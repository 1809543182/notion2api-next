#!/usr/bin/env python3
"""Compare Notion's live model roster with the registry shipped with the proxy.

Usage
-----
    python scripts/sync_models.py                 # use accounts.json + .env
    python scripts/sync_models.py --raw           # also dump the upstream JSON
    python scripts/sync_models.py --json          # machine-readable output
    python scripts/sync_models.py --accounts other_accounts.json

Exit codes
----------
    0  every Notion codename is already exposed by this proxy
    1  network / upstream failure
    2  configuration or authentication problem
    3  drift: Notion offers codenames that this proxy does not expose yet
"""

from __future__ import annotations

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(override=True)

from app.model_registry import NOTION_MODEL_REVERSE_MAP, catalog_stats  # noqa: E402
from app.model_sync import (  # noqa: E402
    diff_against_snapshot,
    extract_available_models,
    fetch_available_models,
)


def load_accounts(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise SystemExit(
            f"[config] {path} not found. Create it from accounts.example.json "
            "or run: python login.py"
        )
    try:
        with open(path, "r", encoding="utf-8") as handle:
            accounts = json.load(handle)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[config] {path} is not valid JSON: {exc}")
    if not isinstance(accounts, list) or not accounts:
        raise SystemExit(f"[config] {path} must be a non-empty JSON array")
    return accounts


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync the model catalog with Notion")
    parser.add_argument("--accounts", default=os.path.join(PROJECT_ROOT, "accounts.json"))
    parser.add_argument("--notion-url", default=os.getenv("NOTION_URL", "https://app.notion.com"))
    parser.add_argument(
        "--client-version", default=os.getenv("NOTION_CLIENT_VERSION", "23.13.20261017.0323")
    )
    parser.add_argument("--impersonate", default=os.getenv("NOTION_IMPERSONATE", "chrome"))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--account", type=int, default=0, help="index into accounts.json")
    parser.add_argument("--raw", action="store_true", help="dump the upstream JSON body")
    parser.add_argument("--json", action="store_true", help="print machine-readable result")
    args = parser.parse_args()

    accounts = load_accounts(args.accounts)
    if args.account >= len(accounts):
        raise SystemExit(f"[config] --account {args.account} out of range")
    account = accounts[args.account]

    stats = catalog_stats()
    if not args.json:
        print(f"[catalog] {stats['models']} models / {stats['providers']} providers, "
              f"default={stats['default']}, newest row={stats['newest']}")
        print(f"[upstream] POST {args.notion_url.rstrip('/')}/api/v3/getAvailableModels")

    try:
        status, payload = fetch_available_models(
            account,
            notion_url=args.notion_url,
            client_version=args.client_version,
            impersonate=args.impersonate,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"[error] request failed: {exc}")
        return 1

    if args.raw:
        print(json.dumps(payload, indent=2, ensure_ascii=False) if not isinstance(payload, str) else payload)

    if status == 401:
        print("[error] 401 Unauthorized: token_v2 expired or space/user ids are wrong. "
              "Refresh credentials with: python login.py --check")
        return 2
    if status != 200:
        excerpt = payload if isinstance(payload, str) else json.dumps(payload)[:300]
        print(f"[error] upstream returned HTTP {status}: {excerpt}")
        return 1

    discovered = extract_available_models(payload)
    if not discovered:
        print("[warn] HTTP 200 but no model codenames could be extracted. "
              "Re-run with --raw and adapt extract_available_models().")
        return 1

    diff = diff_against_snapshot(discovered, NOTION_MODEL_REVERSE_MAP)

    if args.json:
        print(json.dumps({"status": status, "total": len(discovered), **diff}, indent=2, ensure_ascii=False))
    else:
        print(f"[upstream] {len(discovered)} codenames, {len(diff['known'])} known, "
              f"{len(diff['missing'])} missing")
        for item in diff["missing"]:
            extra = f" ({item['display']})" if item.get("display") else ""
            print(f"  + NOT IN PROJECT: {item['codename']}{extra}")
        for item in diff["known"]:
            print(f"    ok: {item['codename']:<32} -> {item['model_id']}")

    if diff["missing"]:
        print("\nAdd missing rows to app/model_registry.py (MODEL_CATALOG), then run "
              "python scripts/gen_model_data.py")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
