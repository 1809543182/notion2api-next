# Notion2API Next

This is a derivative update maintained by [1809543182](https://github.com/1809543182), based on the original project by [maverickxone](https://github.com/maverickxone/notion2api). Main changes: updated Notion account acquisition/recovery flow and updated channel model catalog/transport.

See [authentication](docs/AUTHENTICATION.md) and [portable setup](docs/PORTABILITY.md).

> OpenAI-compatible reverse proxy for Notion AI, rebuilt on top of [maverickxone/notion2api](https://github.com/maverickxone/notion2api) (MIT).
> Model catalog synced to **2026-10-17 / Notion 3.8**: 39 model mappings + Auto = 40 catalog entries; validate availability with your own account, plus Notion's new `agent_service` protocol.

![models](https://img.shields.io/badge/models-40-blue) ![runtime](https://img.shields.io/badge/runtime-agent__service-green) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What changed vs. the original project

| Area | Original (2026-09) | Notion2API Next (2026-10-17) |
|---|---|---|
| Models | 23 | **40** (39 mappings + `auto`) |
| Newest models | GPT-6 Astra / Opus 5 | **GPT-6.1 Sol, GPT-6 Luna, Opus 5.5, Sonnet 5.5, Haiku 5.5, Gemini 3.6/3.7 Flash, Kimi K3, DeepSeek V4 Flash, GPT-5.4 Mini/Nano** |
| Upstream protocol | `runInferenceTranscript` | `agent_service` (`createAgentThread` + `listenToThreadTranscript`), legacy kept |
| TLS fingerprint | cloudscraper | **curl_cffi Chrome impersonation** (Notion now rejects python TLS) |
| Host | `www.notion.so` | `app.notion.com` (Notion migrated in 2026-10) |
| Long runs | idle streams killed by CF | SSE keepalive (15 s) + non-blocking pump thread |
| Model maintenance | edit 3 dicts + 2 UI files | one `MODEL_CATALOG` table + codegen + live sync |

`scripts/sync_models.py` calls Notion's own `getAvailableModels` endpoint and diffs it against the shipped catalog, so you can detect and maintain catalog changes.

---

## Features

- OpenAI compatible: `/v1/chat/completions` (SSE + JSON), `/v1/models`, `/v1/models/{id}`
- 40 models / 8 providers; per-provider grouping in `/v1/models` and the built-in UI
- Model aliases: `claude-opus-5.5`, `opus-5.5`, `sonnet5.5`, even raw Notion codenames (`achira-donut`) are accepted
- Thinking & Search panels (standard/heavy modes)
- Multi-account pool with round-robin + cooldown failover
- Built-in Web UI, 50 pytest tests

---

## Quick start

Install Python 3.11+ and Chrome/Edge first. Extract the ZIP completely.
On Windows run `start.bat`; on macOS/Linux run `bash start.sh`.
The launcher creates a virtual environment, installs dependencies, creates `.env`,
then guides you through signing in with your own Notion account.

Manual setup in an activated Python virtual environment:

```bash
python -m pip install -r requirements.txt -c constraints.txt
cp .env.example .env
python login.py
python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

For Docker, prepare `.env` and a real `accounts.json` on the host first, then run
`docker compose up -d --build`. It binds localhost by default and stores the
database in a named volume. The live Notion/model claims in the original archive
were not independently re-tested during this offline release audit.


Open http://localhost:8000 for the Web UI.

---

## API

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="any")
resp = client.chat.completions.create(
    model="claude-opus5.5",  # or opus-5.5 / albuquerque-quinn
    messages=[{"role": "user", "content": "hi"}],
    stream=True,
)
```

| Endpoint | Method | Notes |
|---|---|---|
| `/v1/chat/completions` | POST | chat completion (core) |
| `/v1/models` | GET | list with provider / display_name / codename / is_default |
| `/v1/models/{id}` | GET | single model, aliases and codenames resolve |
| `/health` | GET | account pool, runtime, model count, upstream version |
| `/` | GET | built-in Web UI |

---

## Keeping models current

```bash
python scripts/sync_models.py          # diff live getAvailableModels vs catalog
python scripts/sync_models.py --raw    # dump upstream JSON when the shape changes
python scripts/sync_models.py --json   # machine readable (CI)
```

Exit codes: `0` all known, `1` network/upstream error, `2` auth failure (401), `3` drift (new codenames found).

Add a model by appending one row to `MODEL_CATALOG` in `app/model_registry.py`, then:

```bash
python scripts/gen_model_data.py   # regenerate UI tables
python -m pytest -q                # 50 tests
```

See [docs/MODEL_CATALOG.md](./docs/MODEL_CATALOG.md) and [docs/ADD_MODEL.md](./docs/ADD_MODEL.md).

---

## Environment

| Variable | Description | Default |
|---|---|---|
| `NOTION_ACCOUNTS` / `accounts.json` | Notion credentials | required |
| `NOTION_URL` | upstream base URL | `https://app.notion.com` |
| `NOTION_PROXY` | outbound proxy (Clash/V2Ray; required in CN) | empty |
| `NOTION_CLIENT_VERSION` | client version header | `23.13.20261017.0323` |
| `NOTION_RUNTIME` | `agent_service` / `legacy` | `agent_service` |
| `NOTION_IMPERSONATE` | curl_cffi TLS profile | `chrome` |
| `AGENT_SERVICE_TIMEOUT_S` | per-reply timeout | `240` |
| `STREAM_KEEPALIVE_S` | SSE keepalive interval | `15` |
| `DEFAULT_MODEL` | default model id | `claude-sonnet5.5` |
| `APP_MODE` | lite / standard / heavy | `heavy` |
| `API_KEY` | client bearer token | empty (disabled) |
| `SILICONFLOW_API_KEY` | heavy-mode summarizer | empty |

---

## Provenance of the model data

1. Notion release notes: [3.7 (2026-09-15)](https://www.notion.com/releases/2026-09-15), [3.8 (2026-10-13)](https://www.notion.com/releases/2026-10-13).
2. Notion endpoint `POST https://app.notion.com/api/v3/getAvailableModels` (401 without auth = endpoint exists); wrapped by `scripts/sync_models.py`.
3. Community verification: [upstream PR #29](https://github.com/maverickxone/notion2api/pull/29) (2026-10-17) states its codenames come from `getAvailableModels`.
4. REA static analysis of the `app.notion.com` client bundle confirmed client version `23.13.20261017.0323` and the new host.

---

## License

MIT. Original project by [maverickxone](https://github.com/maverickxone/notion2api); agent_service/TLS fixes informed by community PR #29.