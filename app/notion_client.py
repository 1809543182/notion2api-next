import os
import threading
import time
import uuid
from typing import Any, Generator, Optional

import json

import cloudscraper
import requests
import urllib3

try:  # Chrome TLS/HTTP2 fingerprint. Notion AI endpoints reject python-requests/cloudscraper JA3
    from curl_cffi import requests as cffi_requests  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    cffi_requests = None

from app.logger import logger
from app.model_registry import get_notion_model
from app.stream_parser import parse_stream

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 可通过环境变量覆盖 Notion 客户端版本号（Notion 更新后可能需要同步）
NOTION_CLIENT_VERSION = os.getenv("NOTION_CLIENT_VERSION", "23.13.20261017.0323")

# Notion 站点根地址（区域镜像 / 反代时可覆盖）；未设置时保持官方默认
# 2026-10: Notion's web client and API moved to app.notion.com (the old
# www.notion.so host is retired for the AI endpoints). Override for mirrors.
NOTION_URL = os.getenv("NOTION_URL", "https://app.notion.com").rstrip("/")

# 2026-10: Notion AI endpoints (runInferenceTranscript, createAgentThread, sendEventToAgentThread)
# answer {"type":"error","subType":"temporarily-unavailable"} / 400 UserValidationError generic_error
# unless the TLS fingerprint looks like a real browser. curl_cffi impersonation fixes it.
NOTION_IMPERSONATE = os.getenv("NOTION_IMPERSONATE", "chrome").strip()

# Chat runtime: "agent_service" (new Notion Agent Service protocol: createAgentThread +
# listenToThreadTranscript) or "legacy" (runInferenceTranscript). Accounts enrolled in the
# agent_service experiment still accept legacy calls as of 2026-10-17, but the web UI uses agent_service.
NOTION_RUNTIME = os.getenv("NOTION_RUNTIME", "agent_service").strip().lower()
AGENT_SERVICE_TIMEOUT_S = float(os.getenv("AGENT_SERVICE_TIMEOUT_S", "240"))
AGENT_SERVICE_DELETE_THREAD = os.getenv("AGENT_SERVICE_DELETE_THREAD", "false").strip().lower() in ("1", "true", "yes")

BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"


def _proxy_config():
    """Optional outbound proxy (Clash/V2Ray/...), e.g. http://127.0.0.1:7890."""
    proxy = (
        os.getenv("NOTION_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("https_proxy")
        or os.getenv("ALL_PROXY")
        or os.getenv("all_proxy")
        or ""
    ).strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def _new_http_session():
    """HTTP session with a browser TLS fingerprint when curl_cffi is available."""
    proxies = _proxy_config()
    if cffi_requests is not None and NOTION_IMPERSONATE.lower() not in ("", "0", "off", "none", "false"):
        try:
            return cffi_requests.Session(impersonate=NOTION_IMPERSONATE, proxies=proxies)
        except TypeError:  # older curl_cffi without the proxies kwarg
            session = cffi_requests.Session(impersonate=NOTION_IMPERSONATE)
            if proxies:
                session.proxies = proxies
            return session
    session = cloudscraper.create_scraper()
    if proxies:
        session.proxies.update(proxies)
    return session


_TRANSPORT_ERRORS: tuple = (requests.exceptions.RequestException,)
_TIMEOUT_ERRORS: tuple = (requests.exceptions.Timeout,)
if cffi_requests is not None:
    from curl_cffi.requests import exceptions as _cffi_exc  # type: ignore

    _TRANSPORT_ERRORS = _TRANSPORT_ERRORS + (_cffi_exc.RequestException,)
    _TIMEOUT_ERRORS = _TIMEOUT_ERRORS + (_cffi_exc.Timeout,)


class NotionUpstreamError(RuntimeError):
    """Notion 上游请求失败或返回异常内容。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        retriable: bool = True,
        response_excerpt: str = "",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retriable = retriable
        self.response_excerpt = response_excerpt


class NotionOpusAPI:
    def __init__(self, account_config: dict):
        """
        从单组账号配置初始化 Notion 客户端。
        account_config 需要包含 token_v2, space_id, user_id, space_view_id, user_name, user_email
        """
        self.token_v2 = account_config.get("token_v2", "")
        self.space_id = account_config.get("space_id", "")
        self.user_id = account_config.get("user_id", "")
        self.space_view_id = account_config.get("space_view_id", "")
        self.user_name = account_config.get("user_name", "user")
        self.user_email = account_config.get("user_email", "")
        self.cookies = account_config.get("cookies", {})
        if not isinstance(self.cookies, dict):
            self.cookies = {}
        self.cookies["token_v2"] = self.token_v2

        self.url = f"{NOTION_URL}/api/v3/runInferenceTranscript"
        self.delete_url = f"{NOTION_URL}/api/v3/saveTransactions"
        self.account_key = self.user_email or self.user_id or "unknown-account"

        # 复用 HTTP 会话（curl_cffi Chrome 指纹优先，否则 cloudscraper）
        self._scraper = _new_http_session()
        self._scraper_lock = threading.Lock()

    def _build_cookie_header(self) -> str:
        cookie_jar = self.cookies.copy()
        cookie_jar["notion_user_id"] = self.user_id
        return "; ".join(f"{name}={value}" for name, value in cookie_jar.items() if value)

    def _to_notion_transcript(self, transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for block in transcript:
            if block.get("type") != "config":
                converted.append(block)
                continue

            value = block.get("value")
            if not isinstance(value, dict):
                converted.append(block)
                continue

            notion_block = dict(block)
            notion_value = dict(value)
            mapped = get_notion_model(str(value.get("model", "") or ""))
            if mapped == "auto":  # "auto" only exists on the agent_service runtime
                mapped = get_notion_model("")
            notion_value["model"] = mapped
            notion_block["value"] = notion_value
            converted.append(notion_block)
        return converted

    def _resolve_thread_type(self, notion_transcript: list[dict[str, Any]]) -> str:
        for block in notion_transcript:
            if block.get("type") != "config":
                continue
            value = block.get("value")
            if isinstance(value, dict):
                thread_type = str(value.get("type", "") or "").strip()
                if thread_type:
                    return thread_type
        return "workflow"

    def _resolve_request_profile(self, thread_type: str) -> dict[str, Any]:
        is_markdown_chat = thread_type == "markdown-chat"
        return {
            "thread_type": thread_type,
            "create_thread": not is_markdown_chat,
            "is_partial_transcript": is_markdown_chat,
            "precreate_thread": is_markdown_chat,
            "include_debug_overrides": os.getenv("NOTION_DEBUG_OVERRIDES", "false").lower() in ("1", "true", "yes"),
        }

    def _build_thread_headers(self) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "cookie": self._build_cookie_header(),
            "x-notion-active-user-header": self.user_id,
            "x-notion-space-id": self.space_id,
        }

    def _create_thread(self, thread_id: str, thread_type: str) -> bool:
        payload = {
            "requestId": str(uuid.uuid4()),
            "transactions": [
                {
                    "id": str(uuid.uuid4()),
                    "spaceId": self.space_id,
                    "operations": [
                        {
                            "pointer": {"table": "thread", "id": thread_id, "spaceId": self.space_id},
                            "path": [],
                            "command": "set",
                            "args": {
                                "id": thread_id,
                                "version": 1,
                                "parent_id": self.space_id,
                                "parent_table": "space",
                                "space_id": self.space_id,
                                "created_time": int(time.time() * 1000),
                                "created_by_id": self.user_id,
                                "created_by_table": "notion_user",
                                "messages": [],
                                "data": {},
                                "alive": True,
                                "type": thread_type,
                            },
                        }
                    ],
                }
            ],
        }
        try:
            resp = requests.post(
                self.delete_url,
                json=payload,
                headers=self._build_thread_headers(),
                timeout=20,
            )
            if resp.status_code == 200:
                return True
            logger.warning(
                "Pre-create thread failed",
                extra={
                    "request_info": {
                        "event": "thread_precreate_failed",
                        "thread_id": thread_id,
                        "thread_type": thread_type,
                        "status": resp.status_code,
                    }
                },
            )
        except Exception:
            logger.warning(
                "Pre-create thread raised exception",
                exc_info=True,
                extra={
                    "request_info": {
                        "event": "thread_precreate_error",
                        "thread_id": thread_id,
                        "thread_type": thread_type,
                    }
                },
            )
        return False

    def delete_thread(self, thread_id: str) -> None:
        """
        通过 saveTransactions 接口将指定 thread 的 alive 状态设为 False，
        从而清理 Notion 主页面上的对话记录。
        此方法设计为在后台线程中调用，不影响主流输出。
        """
        headers = self._build_thread_headers()
        payload = {
            "requestId": str(uuid.uuid4()),
            "transactions": [
                {
                    "id": str(uuid.uuid4()),
                    "spaceId": self.space_id,
                    "operations": [
                        {
                            "pointer": {
                                "table": "thread",
                                "id": thread_id,
                                "spaceId": self.space_id,
                            },
                            "command": "update",
                            "path": [],
                            "args": {"alive": False},
                        }
                    ],
                }
            ],
        }
        try:
            resp = requests.post(self.delete_url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                logger.info(
                    "Thread auto-deleted from Notion home",
                    extra={"request_info": {"event": "thread_deleted", "thread_id": thread_id}},
                )
            else:
                logger.warning(
                    f"Thread deletion failed: HTTP {resp.status_code}",
                    extra={"request_info": {"event": "thread_delete_failed", "thread_id": thread_id, "status": resp.status_code}},
                )
        except Exception as exc:
            logger.warning(
                f"Thread deletion raised an exception: {exc}",
                extra={"request_info": {"event": "thread_delete_error", "thread_id": thread_id}},
            )

    def stream_response(self, transcript: list, thread_id: Optional[str] = None) -> Generator[dict[str, Any], None, None]:
        """
        发起 Notion API 请求并返回结构化流生成器。
        接收完整的 transcript 列表作为参数。

        Args:
            transcript: 对话历史记录列表
            thread_id: 可选的已有 thread_id。如果提供，将重用该线程以保持上下文
        """
        if not isinstance(transcript, list) or not transcript:
            raise ValueError("Invalid transcript payload: transcript must be a non-empty list.")

        if NOTION_RUNTIME == "agent_service":
            yield from self._stream_agent_service(transcript)
            return

        notion_transcript = self._to_notion_transcript(transcript)
        thread_type = self._resolve_thread_type(notion_transcript)
        request_profile = self._resolve_request_profile(thread_type)

        # 如果没有提供 thread_id，创建新的；否则重用已有的
        should_create_thread = thread_id is None
        thread_id = thread_id or str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        response = None

        # 保存 thread_id 以便外部访问
        self.current_thread_id = thread_id

        if request_profile["precreate_thread"] and should_create_thread:
            if not self._create_thread(thread_id, thread_type):
                should_create_thread = True
                request_profile["create_thread"] = True
                request_profile["is_partial_transcript"] = False
        elif not should_create_thread:
            # 如果重用已有线程，不要创建新线程
            request_profile["create_thread"] = False
            # 关键修复：设置 is_partial_transcript=True，让 Notion 接受客户端的历史消息
            request_profile["is_partial_transcript"] = True

        # 把 cookie 直接放进 header，绕过 cloudscraper 的 cookie jar
        # （cookie jar 可能被 Cloudflare challenge 写入含非 ASCII 字符的 cookie，导致编码错误）
        cookie_header = self._build_cookie_header()

        # ВАЖНО (2026-09-06): апстрим отдаёт пустой стрим без браузерного фингерпринта
        # (проверено A/B: те же payload/token/IP — с sec-fetch + свежим UA идёт NDJSON, без них пусто).
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/x-ndjson",
            "User-Agent": BROWSER_UA,
            "x-notion-space-id": self.space_id,
            "x-notion-active-user-header": self.user_id,
            "notion-audit-log-platform": "web",
            "notion-client-version": NOTION_CLIENT_VERSION,
            "origin": NOTION_URL,
            "referer": f"{NOTION_URL}/chat",
            "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="8", "Google Chrome";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "cookie": cookie_header,
        }

        payload = {
            "traceId": trace_id,
            "spaceId": self.space_id,
            "threadId": thread_id,
            "threadType": thread_type,
            "createThread": request_profile["create_thread"],
            "generateTitle": True,
            "saveAllThreadOperations": True,
            "setUnreadState": True,
            "isPartialTranscript": request_profile["is_partial_transcript"],
            "asPatchResponse": True,
            "isUserInAnySalesAssistedSpace": False,
            "isSpaceSalesAssisted": False,
            "threadParentPointer": {
                "table": "space",
                "id": self.space_id,
                "spaceId": self.space_id,
            },
            "transcript": notion_transcript,
        }
        if request_profile["include_debug_overrides"]:
            payload["debugOverrides"] = {
                "emitAgentSearchExtractedResults": True,
                "cachedInferences": {},
                "annotationInferences": {},
                "emitInferences": False,
            }

        logger.info(
            "Dispatching request to Notion upstream",
            extra={
                "request_info": {
                    "event": "notion_upstream_request",
                    "trace_id": trace_id,
                    "thread_id": thread_id,
                    "thread_type": thread_type,
                    "create_thread": bool(request_profile["create_thread"]),
                    "is_partial_transcript": bool(request_profile["is_partial_transcript"]),
                    "account": self.account_key,
                    "space_id": self.space_id,
                }
            },
        )

        try:
            with self._scraper_lock:
                scraper = self._scraper
                scraper.cookies.clear()
            response = scraper.post(
                self.url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=(15, 120),
            )
            if response.status_code == 403:
                # Cloudflare challenge 可能过期，重建 scraper 后重试一次
                response.close()
                logger.warning(
                    "Got 403, rebuilding cloudscraper to refresh Cloudflare challenge",
                    extra={"request_info": {"event": "cloudflare_challenge_refresh", "account": self.account_key}},
                )
                new_scraper = _new_http_session()
                with self._scraper_lock:
                    self._scraper = new_scraper
                response = new_scraper.post(
                    self.url,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=(15, 120),
                )
            if response.status_code != 200:
                excerpt = (response.text or "").strip().replace("\n", " ")[:300]
                # 429 和 5xx 都允许重试（换账号或等待后重试）
                retriable = response.status_code >= 500 or response.status_code == 429
                raise NotionUpstreamError(
                    f"Notion upstream returned HTTP {response.status_code}.",
                    status_code=response.status_code,
                    retriable=retriable,
                    response_excerpt=excerpt,
                )

            emitted = False
            for chunk in parse_stream(response):
                emitted = True
                yield chunk

            if not emitted:
                raise NotionUpstreamError(
                    "Notion upstream returned an empty stream.",
                    status_code=502,
                    retriable=True,
                )

            # 流结束后，不再自动删除 thread
            # 原因：Notion API 的 workflow 模式依赖于服务器端保存的对话历史
            # 删除 thread 会导致后续请求无法获取历史消息（AI 失忆）
            # 保持 thread 存活可以维持对话上下文
            logger.info(
                "Thread completed and preserved for conversation context",
                extra={
                    "request_info": {
                        "event": "thread_completed_preserved",
                        "thread_id": thread_id,
                        "was_created_new": should_create_thread,
                    }
                },
            )
        except _TIMEOUT_ERRORS as exc:
            logger.error(f"Request timeout: {exc}", exc_info=True)
            raise NotionUpstreamError("Request to Notion upstream timed out.", retriable=True) from exc
        except _TRANSPORT_ERRORS as exc:
            logger.error(f"Request failed: {exc}", exc_info=True)
            # 不暴露原始异常细节给用户
            raise NotionUpstreamError("Request to Notion upstream failed. Please try again later.", retriable=True) from exc
        finally:
            if response is not None:
                response.close()


    # ------------------------------------------------------------------
    # Agent Service runtime (Notion web UI since 2026-10, "agent_service" experiment)
    # ------------------------------------------------------------------
    def _agent_headers(self, accept: str = "application/json") -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": accept,
            "User-Agent": BROWSER_UA,
            "x-notion-space-id": self.space_id,
            "x-notion-active-user-header": self.user_id,
            "notion-audit-log-platform": "web",
            "notion-client-version": NOTION_CLIENT_VERSION,
            "origin": NOTION_URL,
            "referer": f"{NOTION_URL}/ai",
            "sec-ch-ua": '"Chromium";v="141", "Not?A_Brand";v="8", "Google Chrome";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "cookie": self._build_cookie_header(),
        }

    @staticmethod
    def _rich_text_to_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, list) and item and isinstance(item[0], str):
                    parts.append(item[0])
                elif isinstance(item, dict):
                    parts.append(str(item.get("content") or item.get("text") or ""))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return ""

    def _transcript_to_agent_prompt(self, transcript: list[dict[str, Any]]) -> tuple[str, Optional[str]]:
        """Flatten the repo's legacy transcript into one agent-service user message + model codename."""
        model: Optional[str] = None
        turns: list[tuple[str, str]] = []
        for block in transcript:
            btype = block.get("type")
            value = block.get("value")
            if btype == "config" and isinstance(value, dict):
                raw = str(value.get("model", "") or "")
                model = get_notion_model(raw) if raw else None
            elif btype == "user":
                text = self._rich_text_to_str(value)
                if text.strip():
                    turns.append(("user", text))
            elif btype in ("assistant", "agent-inference", "markdown-chat"):
                text = self._rich_text_to_str(value)
                if text.strip():
                    turns.append(("assistant", text))
        if not turns:
            raise ValueError("Transcript has no user message.")
        # merge consecutive same-role turns
        merged: list[list[str]] = []
        for role, text in turns:
            if merged and merged[-1][0] == role:
                merged[-1][1] += "\n\n" + text
            else:
                merged.append([role, text])
        if len(merged) == 1 and merged[0][0] == "user":
            return merged[0][1], model
        last_user_idx = max(i for i, (r, _) in enumerate(merged) if r == "user")
        history = merged[:last_user_idx]
        current = merged[last_user_idx][1]
        lines = ["<conversation_history>"]
        for role, text in history:
            lines.append(f"[{'User' if role == 'user' else 'Assistant'}]\n{text}\n")
        lines.append("</conversation_history>\n")
        lines.append("Continue the conversation above. Reply only to this latest user message:\n")
        lines.append(current)
        return "\n".join(lines), model

    def _agent_post(self, session, name: str, data: dict[str, Any], *, stream: bool = False, timeout: Any = 60):
        url = f"{NOTION_URL}/api/v3/{name}"
        accept = "application/x-ndjson" if stream else "application/json"
        return session.post(url, headers=self._agent_headers(accept), json=data, stream=stream, timeout=timeout)

    def _agent_create_thread(self, session, thread_id: str, prompt: str, model: Optional[str]):
        payload: dict[str, Any] = {
            "type": "personal_agent",
            "spaceId": self.space_id,
            "threadId": thread_id,
            "createdSource": "full_page_chat",
            "content": [{"type": "text", "text": [[prompt]]}],
            "clientMessageId": str(uuid.uuid4()),
        }
        if model and model.lower() not in ("auto", "default"):
            payload["model"] = model
        resp = self._agent_post(session, "createAgentThread", payload, timeout=(15, 60))
        if resp.status_code == 400 and "model" in payload and "does not support selected model" in (resp.text or ""):
            logger.warning(
                "Agent Service rejected model, retrying with Auto",
                extra={"request_info": {"event": "agent_service_model_rejected", "model": model}},
            )
            payload.pop("model", None)
            payload["threadId"] = thread_id = str(uuid.uuid4())
            payload["clientMessageId"] = str(uuid.uuid4())
            resp = self._agent_post(session, "createAgentThread", payload, timeout=(15, 60))
        if resp.status_code != 200:
            excerpt = (resp.text or "").strip().replace("\n", " ")[:300]
            retriable = resp.status_code >= 500 or resp.status_code == 429
            raise NotionUpstreamError(
                f"Notion createAgentThread returned HTTP {resp.status_code}.",
                status_code=resp.status_code,
                retriable=retriable,
                response_excerpt=excerpt,
            )
        return thread_id

    def _stream_agent_service(self, transcript: list[dict[str, Any]]) -> Generator[dict[str, Any], None, None]:
        prompt, model = self._transcript_to_agent_prompt(transcript)
        thread_id = str(uuid.uuid4())
        session = _new_http_session()
        response = None
        try:
            logger.info(
                "Dispatching Agent Service thread",
                extra={"request_info": {"event": "agent_service_request", "model": model, "account": self.account_key,
                                        "prompt_chars": len(prompt)}},
            )
            thread_id = self._agent_create_thread(session, thread_id, prompt, model)
            self.current_thread_id = thread_id
            response = self._agent_post(
                session,
                "listenToThreadTranscript",
                {"spaceId": self.space_id, "threadId": thread_id,
                 "includeProvisionalUserMessages": True, "includeQueueChanges": False},
                stream=True,
                timeout=(15, AGENT_SERVICE_TIMEOUT_S),
            )
            if response.status_code != 200:
                excerpt = (response.text or "").strip().replace("\n", " ")[:300]
                raise NotionUpstreamError(
                    f"Notion listenToThreadTranscript returned HTTP {response.status_code}.",
                    status_code=response.status_code,
                    retriable=response.status_code >= 500 or response.status_code == 429,
                    response_excerpt=excerpt,
                )
            yield from self._parse_agent_stream(response, thread_id)
        except _TIMEOUT_ERRORS as exc:
            raise NotionUpstreamError("Agent Service request timed out.", retriable=True) from exc
        except _TRANSPORT_ERRORS as exc:
            logger.error(f"Agent Service request failed: {exc}", exc_info=True)
            raise NotionUpstreamError("Request to Notion upstream failed. Please try again later.", retriable=True) from exc
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            try:
                session.close()
            except Exception:
                pass
            if AGENT_SERVICE_DELETE_THREAD and getattr(self, "current_thread_id", None) == thread_id:
                threading.Thread(target=self.delete_thread, args=(thread_id,), daemon=True).start()

    def _parse_agent_stream(self, response, thread_id: str) -> Generator[dict[str, Any], None, None]:
        """Translate agent_service transcript deltas into repo stream items (content/thinking/final_content)."""
        deadline = time.time() + AGENT_SERVICE_TIMEOUT_S
        provisional_text: dict[str, str] = {}     # assistant_message id -> text emitted so far
        thinking_text: dict[str, str] = {}
        committed_assistant: list[str] = []
        emitted_any = False
        seen_running = False
        for raw in response.iter_lines():
            if time.time() > deadline:
                raise NotionUpstreamError("Agent Service turn timed out.", retriable=True)
            if not raw:
                continue
            line = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            etype = event.get("type")
            if etype == "keepalive":
                continue
            if etype != "agent_service_transcript_delta":
                continue
            for patch in event.get("patches") or []:
                op = patch.get("op")
                if op in ("session", "session_status"):
                    status = (patch.get("session") or {}).get("status")
                    if status == "running":
                        seen_running = True
                    continue
                if op == "patch":
                    pid = str(patch.get("id") or "")
                    if pid not in provisional_text:
                        continue
                    for sub in patch.get("ops") or []:
                        if sub.get("op") == "append" and str(sub.get("path", "")).endswith("/text"):
                            delta = str(sub.get("value") or "")
                            if delta:
                                provisional_text[pid] += delta
                                emitted_any = True
                                yield {"type": "content", "text": delta}
                    continue
                if op != "put":
                    continue
                entity = patch.get("entity") or {}
                kind = entity.get("kind")
                source = entity.get("source")
                eid = str(entity.get("id") or "")
                if kind == "assistant_message":
                    text = "".join(
                        str(c.get("text") or "") for c in (entity.get("content") or []) if isinstance(c, dict) and c.get("type") == "text"
                    )
                    if source == "provisional":
                        if eid not in provisional_text:
                            if any(provisional_text.values()) and text:
                                # another assistant segment in the same turn (e.g. after a tool call)
                                yield {"type": "content", "text": "\n\n"}
                            provisional_text[eid] = ""
                        prev = provisional_text[eid]
                        delta = text[len(prev):] if text.startswith(prev) else text
                        if delta:
                            provisional_text[eid] = text
                            emitted_any = True
                            yield {"type": "content", "text": delta}
                    else:
                        if text:
                            committed_assistant.append(text)
                elif kind == "thinking":
                    text = str(entity.get("content_text") or "")
                    if source == "provisional" and text:
                        prev = thinking_text.get(eid, "")
                        delta = text[len(prev):] if text.startswith(prev) else text
                        thinking_text[eid] = text
                        if delta:
                            yield {"type": "thinking", "text": delta}
                elif kind == "turn_completed":
                    final = "\n\n".join(t for t in committed_assistant if t.strip())
                    if final:
                        yield {"type": "final_content", "text": final, "source_type": "agent-service-committed"}
                    elif not emitted_any:
                        raise NotionUpstreamError(
                            "Agent Service turn completed without an assistant message.", status_code=502, retriable=True
                        )
                    return
                elif kind and ("error" in kind or "failed" in kind):
                    msg = str(entity.get("message") or entity.get("error") or entity.get("text") or kind)
                    logger.warning(
                        "Agent Service turn error entity",
                        extra={"request_info": {"event": "agent_service_turn_error", "thread_id": thread_id,
                                                "kind": kind}},
                    )
                    raise NotionUpstreamError(f"Notion Agent Service error: {msg}"[:300], status_code=502, retriable=False)
        # stream closed before turn_completed
        final = "\n\n".join(t for t in committed_assistant if t.strip())
        if final:
            yield {"type": "final_content", "text": final, "source_type": "agent-service-committed"}
            return
        if not emitted_any:
            raise NotionUpstreamError("Agent Service stream ended without a reply.", status_code=502, retriable=True)
