"""Live model discovery against Notion's getAvailableModels endpoint.

The hard-coded catalog in app/model_registry.py is a snapshot. Notion ships new
models every few weeks (see Notion 3.7 / 3.8 release notes), so this module
lets an operator ask Notion directly which codenames the account can use.

Endpoint: POST <NOTION_URL>/api/v3/getAvailableModels

The response body shape is not documented and has changed before, so parsing is
deliberately defensive:

1. known container keys are tried first (models / availableModels / ...),
2. then any nested list of model-looking records is collected,
3. then a heuristic string scan of the whole payload is used as a last resort.

Whatever is recovered is compared against MODEL_MAP so the operator can see
exactly which Notion codenames the project does not expose yet.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable

try:  # pragma: no cover - exercised only when the optional dep is present
    from curl_cffi import requests as cffi_requests  # type: ignore
except Exception:  # pragma: no cover
    cffi_requests = None

import requests

# A Notion model codename: lowercase words joined by dashes/dots, optionally
# suffixed with a reasoning tier (low/medium/high).
CODENAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*(?:-(?:low|medium|high))?$")

CONTAINER_KEYS = (
    "models",
    "availableModels",
    "available_models",
    "modelConfigs",
    "model_configs",
    "modelPickerModels",
    "modelPicker",
    "aiModels",
    "results",
    "data",
    "items",
)

CODENAME_FIELDS = ("id", "model", "codename", "modelId", "model_id", "code", "value", "key")
DISPLAY_FIELDS = ("displayName", "display_name", "label", "title", "name", "friendlyName")

# Strings that match CODENAME_RE but are clearly not model ids.
_NON_MODEL_HINTS = (
    "application",
    "text/",
    "utf-8",
    "json",
    "api/v3",
    "http",
    "www.",
    "notion",
    "google",
    "chrome",
    "safari",
    "mozilla",
)


def _looks_like_codename(value: str, *, strict: bool = True) -> bool:
    if not value or len(value) > 64 or len(value) < 3:
        return False
    if not CODENAME_RE.match(value):
        return False
    lowered = value.lower()
    if any(hint in lowered for hint in _NON_MODEL_HINTS):
        return False
    # Free-form strings must look like "orange-mousse" / "omodi" is only accepted
    # when it comes from a structured field (id/model/codename/...).
    if strict and not (("-" in value) or ("." in value) or ("_" in value)):
        return False
    return True


def _record_from_dict(item: dict[str, Any]) -> dict[str, Any] | None:
    codename = ""
    for field in CODENAME_FIELDS:
        raw = item.get(field)
        if isinstance(raw, str) and _looks_like_codename(raw.strip(), strict=False):
            codename = raw.strip()
            break
    if not codename:
        return None
    display = ""
    for field in DISPLAY_FIELDS:
        raw = item.get(field)
        if isinstance(raw, str) and raw.strip() and raw.strip() != codename:
            display = raw.strip()
            break
    provider = ""
    for field in ("provider", "vendor", "lab", "source", "company"):
        raw = item.get(field)
        if isinstance(raw, str) and raw.strip():
            provider = raw.strip()
            break
    return {"codename": codename, "display": display, "provider": provider}


def _collect(value: Any, out: dict[str, dict[str, Any]], depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(value, dict):
        record = _record_from_dict(value)
        if record:
            out.setdefault(record["codename"], record)
        for key, child in value.items():
            if key in CONTAINER_KEYS or isinstance(child, (list, dict)):
                _collect(child, out, depth + 1)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _collect(child, out, depth + 1)
    elif isinstance(value, str):
        if _looks_like_codename(value.strip()):
            out.setdefault(value.strip(), {"codename": value.strip(), "display": "", "provider": ""})


def _record_from_live_model(item: dict[str, Any]) -> dict[str, Any] | None:
    """Structured record from Notion's current getAvailableModels schema.

    {"model": "omniberry-sundae", "modelMessage": "GPT-6.1 Sol",
     "modelFamily": "openai", "modelProvider": "openai", "displayGroup": "intelligent"}
    """
    codename = item.get("model") or item.get("codename")
    if not isinstance(codename, str) or not codename.strip():
        return None
    return {
        "codename": codename.strip(),
        "display": str(item.get("modelMessage") or item.get("displayName") or "").strip(),
        "provider": str(item.get("modelProvider") or item.get("modelFamily") or "").strip(),
        "tier": str(item.get("displayGroup") or "").strip(),
    }


def extract_available_models(payload: Any) -> list[dict[str, Any]]:
    """Best-effort extraction of model codenames from a getAvailableModels body."""
    found: dict[str, dict[str, Any]] = {}
    if isinstance(payload, dict):
        # Current schema (2026-10): a flat "models" list plus a restricted picker list.
        for key in ("models", "restrictedAccessModelsInPickerConfig"):
            for item in payload.get(key) or []:
                if isinstance(item, dict):
                    record = _record_from_live_model(item)
                elif isinstance(item, str) and item.strip():
                    record = {"codename": item.strip(), "display": "", "provider": "", "tier": ""}
                else:
                    record = None
                if record:
                    found.setdefault(record["codename"], record)
        if found:
            return sorted(found.values(), key=lambda entry: entry["codename"])
        for key in CONTAINER_KEYS:
            if key in payload:
                _collect(payload[key], found)
        if not found:
            _collect(payload, found)
    elif isinstance(payload, list):
        _collect(payload, found)
    return sorted(found.values(), key=lambda item: item["codename"])


def _proxy_config() -> dict[str, str] | None:
    proxy = (
        os.getenv("NOTION_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("ALL_PROXY")
        or os.getenv("all_proxy")
        or ""
    ).strip()
    return {"http": proxy, "https": proxy} if proxy else None


def build_session(account: dict[str, Any], impersonate: str = "chrome") -> Any:
    """Create an HTTP session carrying the account cookies."""
    proxies = _proxy_config()
    if cffi_requests is not None and impersonate and impersonate.lower() not in ("", "0", "off", "none", "false"):
        try:
            session = cffi_requests.Session(impersonate=impersonate, proxies=proxies)
        except TypeError:
            session = cffi_requests.Session(impersonate=impersonate)
            if proxies:
                session.proxies = proxies
    else:
        session = requests.Session()
    if proxies and hasattr(session, "proxies"):
        try:
            session.proxies.update(proxies)
        except Exception:
            pass

    cookies = account.get("cookies") if isinstance(account.get("cookies"), dict) else {}
    for name, value in cookies.items():
        if value:
            session.cookies.set(name, str(value))
    if account.get("token_v2"):
        session.cookies.set("token_v2", str(account["token_v2"]))
    if account.get("user_id"):
        session.cookies.set("notion_user_id", str(account["user_id"]))
    return session


def fetch_available_models(
    account: dict[str, Any],
    notion_url: str,
    client_version: str,
    impersonate: str = "chrome",
    timeout: float = 30.0,
) -> tuple[int, Any]:
    """POST getAvailableModels and return (status_code, parsed_json_or_text)."""
    url = f"{notion_url.rstrip('/')}/api/v3/getAvailableModels"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        ),
        "notion-client-version": client_version,
        "notion-audit-log-platform": "web",
        "origin": notion_url.rstrip("/"),
        "referer": f"{notion_url.rstrip('/')}/ai",
    }
    if account.get("space_id"):
        headers["x-notion-space-id"] = str(account["space_id"])
    if account.get("user_id"):
        headers["x-notion-active-user-header"] = str(account["user_id"])

    # getAvailableModels validates the body: {"spaceId": ...} ({} returns 400).
    body: dict[str, Any] = {}
    if account.get("space_id"):
        body["spaceId"] = str(account["space_id"])

    session = build_session(account, impersonate)
    try:
        response = session.post(url, headers=headers, json=body, timeout=timeout)
        status = int(getattr(response, "status_code", 0))
        try:
            payload = response.json()
        except Exception:
            payload = (response.text or "").strip()
        return status, payload
    finally:
        try:
            session.close()
        except Exception:
            pass


def diff_against_snapshot(
    discovered: Iterable[dict[str, Any]],
    known_codenames: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    """Split discovered models into already-known and missing-from-project."""
    known: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for record in discovered:
        codename = record["codename"]
        if codename in known_codenames:
            known.append({**record, "model_id": known_codenames[codename]})
        else:
            missing.append(record)
    return {"known": known, "missing": missing}
