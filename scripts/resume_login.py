#!/usr/bin/env python3
"""Finish account setup from a token captured earlier by scripts/connect.py.

If connect.py already saved data/pending_account.json but failed while resolving
the workspace (network reset, API change, ...), this retries without asking the
user to log in again:

    python scripts/resume_login.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("connect_mod", ROOT / "scripts" / "connect.py")
connect = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
sys.modules["connect_mod"] = connect
spec.loader.exec_module(connect)  # type: ignore[union-attr]

login = connect.login
PENDING = ROOT / "data" / "pending_account.json"


def main() -> int:
    if not PENDING.exists():
        print("[resume] no data/pending_account.json - run scripts/connect.py first")
        return 2
    pending = json.loads(PENDING.read_text(encoding="utf-8"))
    token = str(pending.get("token_v2") or "").strip()
    cookies = pending.get("cookies") or {}
    if not token:
        print("[resume] pending file has no token_v2")
        return 2
    print(f"[resume] using saved token ({len(token)} chars, {len(cookies)} cookies)")

    login._session_for_token = lambda t, c=None: connect._CurlSession(t, c)  # type: ignore[assignment]
    try:
        candidates = login._extract_candidates(token, cookies)
    except Exception as exc:  # noqa: BLE001
        print(f"[resume] workspace lookup failed: {type(exc).__name__}: {exc}")
        return 1

    chosen = login._choose_account(candidates).with_profile("default")
    merged = login._write_accounts(chosen)
    login._sync_env_file(merged)
    PENDING.unlink(missing_ok=True)
    account = chosen.to_dict()
    print("[resume] account saved:")
    for key in ("profile_name", "user_name", "user_email", "space_id", "user_id"):
        print(f"  {key}: {account.get(key)}")
    print(f"  accounts.json entries: {len(merged)}")

    try:
        models = connect._query_models(account)
        out = ROOT / "data" / "model-sync.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "account": {k: account.get(k) for k in ("user_name", "user_email", "space_id", "user_id")},
                    "models": models,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        status = models.get("status")
        discovered = models.get("discovered") or []
        missing = models.get("missing") or []
        print(f"[resume] getAvailableModels status={status} discovered={len(discovered)} missing={len(missing)}")
        for item in missing:
            print(f"  + MISSING locally: {item['codename']} {item.get('display') or ''}")
        if status != 200:
            print(f"[resume] model endpoint returned {status}: {models.get('error')}")
    except Exception as exc:  # noqa: BLE001
        print(f"[resume] model query failed (account is still saved): {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
