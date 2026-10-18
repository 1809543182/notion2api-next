#!/usr/bin/env python3
"""One-link Notion account connector.

Starts a controlled Chrome window (remote debugging) on the Notion login page and
serves a local status page:

    http://127.0.0.1:8899/

You sign in inside that Chrome window; the page flips to "connected" as soon as
Notion sets token_v2. The connector then derives space_id / user_id, writes
accounts.json (+ .env) and queries getAvailableModels with the fresh account so
you can see exactly which models the workspace can use.

Usage:
    python scripts/connect.py                # open http://127.0.0.1:8899
    python scripts/connect.py --port 8899 --timeout 1800
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import json as json_module
import os
import shutil
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("notion_login", ROOT / "login.py")
login = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
# dataclasses resolves the defining module through sys.modules, so register first.
sys.modules["notion_login"] = login
_spec.loader.exec_module(login)  # type: ignore[union-attr]

STATE = {
    "phase": "starting",
    "detail": "正在启动受控浏览器…",
    "chrome_ok": False,
    "token_ok": False,
    "account": None,
    "models": None,
    "error": None,
    "started_at": time.time(),
}
_LOCK = threading.Lock()


def _set(**kwargs):
    with _LOCK:
        STATE.update(kwargs)


PENDING_FILE = ROOT / "data" / "pending_account.json"


class _CurlResponse:
    """Minimal requests.Response look-alike backed by the system curl.exe."""

    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text[:300]}")


class _CurlSession:
    """HTTP session that shells out to curl.exe.

    Some networks reset libcurl/curl_cffi TLS handshakes to app.notion.com while
    the Windows Schannel curl.exe client still works. This shim keeps the
    account bootstrap usable on such networks (and is used only for small JSON
    calls, never for streaming chat).
    """

    def __init__(self, token_v2: str, cookies: dict[str, str]):
        import subprocess  # noqa: PLC0415

        self._subprocess = subprocess
        from login import BASE_URL, AI_URL, USER_AGENT  # type: ignore  # noqa: PLC0415

        values = dict(cookies or {})
        values["token_v2"] = token_v2
        self.headers = {
            "Origin": BASE_URL,
            "Referer": AI_URL,
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": "; ".join(f"{name}={value}" for name, value in values.items() if value),
        }

    def post(self, url: str, json=None, timeout: float = 30, **kwargs):  # noqa: A002
        args = [
            (shutil.which("curl.exe") or shutil.which("curl") or "curl"), "-sS", "-m", str(int(timeout)),
            "-X", "POST", url,
            "-w", "\n__HTTP__%{http_code}",
            "--data-binary", json_module.dumps(json or {}),
        ]
        proxy = (
            os.getenv("NOTION_PROXY")
            or os.getenv("HTTPS_PROXY")
            or os.getenv("https_proxy")
            or os.getenv("ALL_PROXY")
            or ""
        ).strip()
        if proxy:
            args.extend(["--proxy", proxy])
        # Send headers through stdin so cookies do not appear in process arguments.
        config = "\n".join("header = " + json_module.dumps(f"{key}: {value}") for key, value in self.headers.items())
        proc = self._subprocess.run(args + ["--config", "-"], input=config.encode("utf-8"), capture_output=True)
        if proc.returncode:
            raise RuntimeError(f"curl transport failed (exit {proc.returncode})")
        raw = proc.stdout.decode("utf-8", "replace")
        body, _, code = raw.rpartition("\n__HTTP__")
        try:
            status = int(code.strip())
        except ValueError:
            status = 0
        return _CurlResponse(status, body)


# ---------------------------------------------------------------------------
# curl_cffi session (Notion rejects the plain requests TLS fingerprint on some
# endpoints); fall back to requests when curl_cffi is unavailable.
# ---------------------------------------------------------------------------

def _browser_session(token_v2: str, cookies: dict[str, str]):
    try:
        from curl_cffi import requests as cffi_requests

        session = cffi_requests.Session(impersonate="chrome")
    except Exception:
        import requests

        session = requests.Session()
    values = dict(cookies or {})
    values["token_v2"] = token_v2
    session.headers.update(
        {
            "Origin": login.BASE_URL,
            "Referer": login.AI_URL,
            "User-Agent": login.USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": "; ".join(f"{name}={value}" for name, value in values.items() if value),
        }
    )
    for name, value in values.items():
        if value:
            try:
                session.cookies.set(name, value, domain=login.NOTION_DOMAIN, path="/")
            except Exception:
                pass
    return session


def _query_models(account: dict) -> dict:
    from app.model_registry import NOTION_MODEL_REVERSE_MAP
    from app.model_sync import diff_against_snapshot, extract_available_models, fetch_available_models

    try:
        status, payload = fetch_available_models(
            account,
            notion_url=login.BASE_URL,
            client_version=os.getenv("NOTION_CLIENT_VERSION", "23.13.20261017.0323"),
            impersonate="chrome",
            timeout=20,
        )
    except Exception:
        # Network resets libcurl/curl_cffi on some ISPs; fall back to curl.exe.
        session = _CurlSession(str(account.get("token_v2") or ""), account.get("cookies") or {})
        response = session.post(
            f"{login.BASE_URL}/api/v3/getAvailableModels",
            json={"spaceId": account["space_id"]},
            timeout=25,
        )
        status, payload = response.status_code, response.json()
    if status != 200:
        return {"status": status, "error": f"HTTP {status}", "discovered": [], "missing": []}
    discovered = extract_available_models(payload)
    diff = diff_against_snapshot(discovered, NOTION_MODEL_REVERSE_MAP)
    return {
        "status": status,
        "discovered": discovered,
        "known": diff["known"],
        "missing": diff["missing"],
    }


# ---------------------------------------------------------------------------
# Capture worker
# ---------------------------------------------------------------------------

def _capture(port: int, timeout: int) -> None:
    process = None
    profile_dir = None
    try:
        _set(phase="launching", detail="正在打开受控 Chrome 窗口…")
        process, profile_dir = login._start_chrome_debug_session(port)
        _set(chrome_ok=True, phase="waiting_login",
             detail="Chrome 已打开。请在这个窗口里登录 Notion，直到看到工作区主界面。")

        deadline = time.time() + timeout
        cookies: dict[str, str] = {}
        while time.time() < deadline:
            try:
                cookies = login._extract_cookies_from_cdp(port)
            except Exception:
                cookies = {}
            token = str(cookies.get("token_v2") or "").strip()
            if token:
                break
            time.sleep(2)
        else:
            _set(phase="timeout", detail="等待登录超时，请重新运行 connect.py")
            return

        token = str(cookies.get("token_v2") or "").strip()
        # Persist immediately: Chrome may be terminated by a later failure and
        # its cookies are not flushed on a hard kill.
        try:
            PENDING_FILE.parent.mkdir(exist_ok=True)
            PENDING_FILE.write_text(
                json.dumps({"token_v2": token, "cookies": cookies, "captured_at": time.time()}, ensure_ascii=False),
                encoding="utf-8",
            )
            os.chmod(PENDING_FILE, 0o600)
        except Exception:
            pass
        _set(token_ok=True, phase="resolving",
             detail="已捕获 token_v2，正在解析工作区信息…")

        # Make login.py's account parsing use our browser-fingerprint session.
        login._session_for_token = lambda t, c=None: _CurlSession(t, c)  # type: ignore[assignment]
        candidates = login._extract_candidates(token, cookies)
        chosen = login._choose_account(candidates).with_profile("default")
        merged = login._write_accounts(chosen)
        login._sync_env_file(merged)
        PENDING_FILE.unlink(missing_ok=True)
        account = chosen.to_dict()
        _set(account={k: account.get(k) for k in ("profile_name", "user_name", "user_email", "space_id", "user_id")},
             phase="syncing_models", detail="账号已写入，正在拉取 Notion 实时模型列表…")

        try:
            models = _query_models(account)
        except Exception as exc:  # noqa: BLE001
            models = {"error": str(exc), "discovered": [], "missing": []}
        _set(models=models, phase="connected",
             detail="连接完成，可以关闭这个页面了。")
        out = ROOT / "data" / "model-sync.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps({"account": STATE["account"], "models": models}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        _set(phase="error", error=f"{type(exc).__name__}: {exc}", detail="连接失败")
    finally:
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        if profile_dir is not None:
            shutil.rmtree(profile_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Status page
# ---------------------------------------------------------------------------

PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Notion2API Next · 连接 Notion</title>
<style>
:root{{color-scheme:dark}}
body{{margin:0;font-family:ui-sans-serif,system-ui,"Segoe UI",sans-serif;background:#0f1115;color:#e7e9ee;display:flex;justify-content:center;padding:48px 20px}}
.card{{width:min(760px,100%);background:#161a21;border:1px solid #262c37;border-radius:18px;padding:28px 30px;box-shadow:0 20px 60px rgba(0,0,0,.35)}}
h1{{font-size:20px;margin:0 0 4px}}
.sub{{color:#8b93a3;font-size:13px;margin-bottom:22px}}
.phase{{font-size:15px;font-weight:600;padding:12px 16px;border-radius:12px;background:#1d2430;border:1px solid #2b3442;margin-bottom:16px}}
.detail{{font-size:13px;color:#aab2c2;margin-bottom:20px;line-height:1.6}}
.steps{{font-size:13px;line-height:1.9;color:#c6ccd8;background:#12161c;border:1px solid #232936;border-radius:12px;padding:14px 18px;margin-bottom:20px}}
.steps b{{color:#7dd3fc}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid #232936}}
th{{color:#8b93a3;font-weight:500}}
.ok{{color:#4ade80}} .bad{{color:#f87171}} .warn{{color:#fbbf24}}
code{{background:#0f1319;border:1px solid #232936;border-radius:6px;padding:1px 6px;font-size:12px}}
small{{color:#6b7280}}
</style></head><body><div class="card">
<h1>Notion2API Next · 连接 Notion</h1>
<div class="sub">状态每 2 秒自动更新（本页不会重载）· 不要关闭受控 Chrome 窗口</div>
<div class="phase" id="phase">{phase_icon} {phase_text}</div>
<div class="detail" id="detail">{detail}</div>
<div class="steps">
 <b>1.</b> 使用本次打开的受控 Chrome 窗口（不是你的日常浏览器）<br>
 <b>2.</b> 选择登录方式（Notion 邮箱 / Google / Apple / Microsoft）并完成验证<br>
 <b>3.</b> <b>一直等到能看到 Notion 工作区页面</b>（左侧边栏出现），不要提前关窗口<br>
 <b>4.</b> 本页会自动变成「已连接」，并显示你账号真实可用的模型
</div>
{body}
</div>
</body></html>"""


def _render() -> str:
    with _LOCK:
        state = dict(STATE)
    phase = state["phase"]
    icons = {
        "starting": ("⏳", "启动中"),
        "launching": ("⏳", "启动浏览器"),
        "waiting_login": ("🔐", "等待你登录"),
        "resolving": ("🧩", "解析工作区"),
        "syncing_models": ("🔄", "同步模型列表"),
        "connected": ("✅", "已连接"),
        "timeout": ("⌛", "等待超时"),
        "error": ("❌", "出错"),
    }
    icon, text = icons.get(phase, ("•", phase))
    rows = []
    rows.append(f"<tr><td>受控 Chrome</td><td>{'<span class=ok>运行中</span>' if state['chrome_ok'] else '<span class=warn>未启动</span>'}</td></tr>")
    rows.append(f"<tr><td>token_v2</td><td>{'<span class=ok>已捕获</span>' if state['token_ok'] else '<span class=warn>等待中</span>'}</td></tr>")
    account = state.get("account")
    if account:
        rows.append(f"<tr><td>账号</td><td>{html.escape(str(account.get('user_name') or ''))} {html.escape(str(account.get('user_email') or ''))}</td></tr>")
        rows.append(f"<tr><td>工作区 space_id</td><td><code>{html.escape(str(account.get('space_id') or ''))}</code></td></tr>")
    body = "<table>" + "".join(rows) + "</table>"
    models = state.get("models")
    if models:
        if models.get("error"):
            body += f"<p class=bad>模型接口错误：{html.escape(str(models['error']))}</p>"
        else:
            discovered = models.get("discovered") or []
            missing = models.get("missing") or []
            body += f"<h3 style='font-size:14px;margin:22px 0 6px'>Notion 实时模型：{len(discovered)} 个 · 本地缺失：{len(missing)}</h3>"
            if missing:
                body += "<table><tr><th>本地缺失的代号</th><th>显示名</th></tr>"
                for item in missing:
                    body += f"<tr><td><code>{html.escape(item['codename'])}</code></td><td>{html.escape(item.get('display') or '')}</td></tr>"
                body += "</table>"
            else:
                body += "<p class=ok>本地模型目录已覆盖本次接口返回的全部代号。</p>"
    if state.get("error"):
        body += f"<p class=bad>{html.escape(str(state['error']))}</p>"
    uptime = int(time.time() - state["started_at"])
    body += f"<p><small>已等待 {uptime}s · 目标地址 {html.escape(login.AI_URL)}</small></p>"
    return PAGE.format(
        phase_icon=icon,
        phase_text=text,
        detail=html.escape(str(state.get("detail") or "")),
        body=body,
    )


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return
        payload = _render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence per-request logging
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Connect a Notion account through a local status page")
    parser.add_argument("--port", type=int, default=8899, help="status page port")
    parser.add_argument("--timeout", type=int, default=1800, help="seconds to wait for the login")
    parser.add_argument("--wait", action="store_true", help="keep serving after the account is connected")
    args = parser.parse_args()

    worker = threading.Thread(target=_capture, args=(login._find_free_port(), args.timeout), daemon=True)
    worker.start()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[connect] status page: http://127.0.0.1:{args.port}/")
    print(f"[connect] login url:   {login.AI_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
