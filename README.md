# Notion2API Next

> 把 Notion AI 变成标准 OpenAI 兼容 API 的新一代反代项目。
> 二开更新项目，由 [1809543182](https://github.com/1809543182) 维护。目录快照包含 39 个模型映射 + Auto；实际可用性以你自己的账号和上游返回为准。

**原作者：maverickxone；原始项目：[maverickxone/notion2api](https://github.com/maverickxone/notion2api)。**

本次二开主要更新：
1. 更新获取 Notion 账号 `accounts` 的方式和链路：浏览器辅助提取、工作区识别及失败后恢复。
2. 更新渠道模型：模型注册表、别名、前后端模型同步及 `agent_service` 适配。

认证组件、请求流程和凭据存储见 [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)，换电脑部署见 [docs/PORTABILITY.md](docs/PORTABILITY.md)。

本项目基于 [maverickxone/notion2api](https://github.com/maverickxone/notion2api)（MIT）重构：保留其稳定的转录/流解析实现，重做了模型注册表、上游传输层和模型同步工具。

---

## 这次升级做了什么

| 项目 | 旧版（notion2api-main，2026-09） | Notion2API Next（2026-10-17） |
|---|---|---|
| 模型数量 | 23 | **40**（39 个映射 + `auto`） |
| 最新模型 | GPT-6 Astra / Opus 5 | **GPT-6.1 Sol、GPT-6 Luna、Opus 5.5、Sonnet 5.5、Haiku 5.5、Gemini 3.6/3.7 Flash、Kimi K3、DeepSeek V4 Flash、GPT-5.4 Mini/Nano** |
| 上游协议 | `runInferenceTranscript` | 新增 `agent_service`（`createAgentThread` + `listenToThreadTranscript`），同时保留 legacy |
| TLS 指纹 | cloudscraper | **curl_cffi Chrome 指纹**（Notion 已开始拒绝 python TLS 指纹） |
| 站点域名 | `www.notion.so` | `app.notion.com`（Notion 2026-10 迁移，旧域名 AI 接口已下线） |
| 长任务流 | 静默会被 Cloudflare 掐断 | SSE keepalive（默认 15s）+ 事件循环不阻塞 |
| 模型维护 | 手改 3 个 dict + 2 个前端文件 | **单表 `MODEL_CATALOG` + 代码生成**，还可对着 Notion 实时接口自检 |

新增的 `scripts/sync_models.py` 会直接调用 Notion 的 `getAvailableModels` 接口，把线上真实可用的模型代号和本地目录做 diff ；需要手动运行该工具并维护目录，不能保证自动跟随上游变化。

---

## 特性

- **OpenAI 兼容**：`/v1/chat/completions`（流式 SSE + 非流式）、`/v1/models`、`/v1/models/{id}`
- **40 个目录项 / 8 家厂商**：Anthropic、OpenAI、Google、Moonshot、xAI、DeepSeek、智谱、Notion
- **模型别名**：`claude-opus-5.5`、`opus-5.5`、`sonnet5.5`、甚至 Notion 内部代号（如 `achira-donut`）都能直接作为 `model` 传入
- **Thinking / Search 面板**：standard / heavy 模式展示推理过程与联网搜索
- **多账号池**：轮询 + 冷却故障转移
- **内置 Web UI**：自带模型选择器（按厂商分组）、会话管理、主题切换
- **可自更新**：`sync_models.py` 探测 Notion 新模型；`gen_model_data.py` 同步前后端
- **可测试**：pytest 用例覆盖注册表、API、agent_service 流解析、模型同步解析

---

## 三种运行模式

| 特性 | Lite | Standard | Heavy |
|------|------|----------|-------|
| 记忆 | 无 | 客户端管理 | 服务端管理（SQLite） |
| Thinking 面板 | 否 | 是 | 是 |
| Search 面板 | 否 | 是 | 是 |
| 速率限制 | 30/min | 25/min | 20/min |
| 适用场景 | 简单问答 | 中短对话（推荐） | 长期对话 |

通过 `APP_MODE` 切换：`lite` / `standard` / `heavy`。

---

## 快速开始

### 0. 一键启动（推荐）

| 系统 | 操作 |
|---|---|
| Windows | 双击项目里的 `start.bat` |
| macOS / Linux | `bash start.sh` |

先安装 Python 3.11+，以及 Chrome / Edge（自动登录需要）。启动器会创建独立 `.venv` → 安装依赖 → 从示例创建 `.env` → 缺账号时辅助登录 → 在本机启动服务。然后手动打开 `http://127.0.0.1:8000`。
停止：关闭窗口，或双击 `stop.bat`。

> 下载 ZIP 后先完整解压，不要在压缩包中直接运行。新电脑需要使用自己的 Notion 账号登录；项目不包含任何可直接使用的账号。

### 1. 准备 Notion 凭据

方式 A（推荐，已有 Notion 网页登录）：运行 `python login.py`，脚本会拉起浏览器并自动抓取 `token_v2 / space_id / user_id`，写入 `accounts.json`；
方式 B（手动）：在 Notion 页面 F12 → Application → Cookies 复制 `token_v2`，再在 Console 运行 `scripts/extract_notion_info.js` 补齐其余字段，粘贴到 `accounts.json`（格式见 `accounts.example.json`）。

### 2. 配置

```bash
cp .env.example .env
# 至少确认：NOTION_URL=https://app.notion.com 、APP_MODE=standard
```

### 3. 启动

```bash
python -m pip install -r requirements.txt -c constraints.txt
python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

或 Docker：

先在宿主机完成登录，确认 `.env` 和 `accounts.json` 存在，再运行（Docker 默认仅绑定本机；数据使用命名卷）：

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

打开 http://localhost:8000 即是内置 Web UI。

---

## 模型目录快照（40 个目录项：39 个映射 + Auto，2026-10-17）

⭐ 标记为本次新增；`auto` 表示交给 Notion 自行选择（仅 agent_service 运行时有效，legacy 会回退到默认模型）。

| # | API 模型名 | Notion 代号 | 厂商 | 显示名 | 加入日期 | 新增 |
|---|---|---|---|---|---|---|
| 1 | `claude-sonnet5.5` | `achira-donut` | Anthropic | Sonnet 5.5 | 2026-10-17 | ⭐ |
| 2 | `claude-opus5.5` | `albuquerque-quinn` | Anthropic | Opus 5.5 | 2026-10-17 | ⭐ |
| 3 | `claude-haiku5.5` | `amla-jam` | Anthropic | Haiku 5.5 | 2026-10-17 | ⭐ |
| 4 | `claude-opus5` | `agave-flan` | Anthropic | Opus 5 | 2026-09-06 |  |
| 5 | `claude-sonnet5` | `angel-cake-high` | Anthropic | Sonnet 5 | 2026-09-06 |  |
| 6 | `claude-sonnet4.6` | `almond-croissant-low` | Anthropic | Sonnet 4.6 | 2026-09-06 |  |
| 7 | `claude-opus4.8` | `ambrosia-tart-high` | Anthropic | Opus 4.8 | 2026-09-06 |  |
| 8 | `claude-opus4.7` | `apricot-sorbet-high` | Anthropic | Opus 4.7 | 2026-09-06 |  |
| 9 | `claude-opus4.6` | `avocado-froyo-medium` | Anthropic | Opus 4.6 | 2026-09-06 |  |
| 10 | `claude-haiku4.5` | `anthropic-haiku-4.5` | Anthropic | Haiku 4.5 | 2026-09-06 |  |
| 11 | `gpt-6.1-sol` | `omniberry-sundae` | OpenAI | GPT-6.1 Sol | 2026-10-17 | ⭐ |
| 12 | `gpt-6-luna` | `omodi` | OpenAI | GPT-6 Luna | 2026-10-17 | ⭐ |
| 13 | `gpt-6-astra` | `orlando-quinn` | OpenAI | GPT-6 Astra | 2026-09-06 |  |
| 14 | `gpt-5.6-sol` | `orange-mousse` | OpenAI | GPT-5.6 Sol | 2026-09-06 |  |
| 15 | `gpt-5.6-terra` | `orchid-muffin` | OpenAI | GPT-5.6 Terra | 2026-09-06 |  |
| 16 | `gpt-5.6-luna` | `olive-jellyroll` | OpenAI | GPT-5.6 Luna | 2026-09-06 |  |
| 17 | `gpt-5.5` | `opal-quince-medium` | OpenAI | GPT-5.5 | 2026-09-06 | ⭐ |
| 18 | `gpt-5.4` | `oval-kumquat-medium` | OpenAI | GPT-5.4 | 2026-09-06 |  |
| 19 | `gpt-5.4-mini` | `oregon-grape-medium` | OpenAI | GPT-5.4 Mini | 2026-10-17 | ⭐ |
| 20 | `gpt-5.4-nano` | `otaheite-apple-medium` | OpenAI | GPT-5.4 Nano | 2026-10-17 | ⭐ |
| 21 | `gpt-5.2` | `oatmeal-cookie` | OpenAI | GPT-5.2 | 2026-10-17 | ⭐ |
| 22 | `gemini-3.7flash` | `grapefruit-zeppole` | Google | Gemini 3.7 Flash | 2026-10-17 | ⭐ |
| 23 | `gemini-3.6flash` | `vertex-gemini-3.6-flash` | Google | Gemini 3.6 Flash | 2026-10-17 | ⭐ |
| 24 | `gemini-3.5flash` | `vertex-gemini-3.5-flash` | Google | Gemini 3.5 Flash | 2026-09-06 |  |
| 25 | `gemini-3.1pro` | `galette-medium-thinking` | Google | Gemini 3.1 Pro | 2026-09-06 |  |
| 26 | `gemini-3flash` | `gingerbread` | Google | Gemini 3 Flash | 2026-09-06 |  |
| 27 | `kimi-k3` | `fireworks-kimi-k3` | Moonshot | Kimi K3 | 2026-10-17 | ⭐ |
| 28 | `grok-4.6` | `soursop-shortcake` | xAI | Grok 4.6 | 2026-10-17 | ⭐ |
| 29 | `grok-4.3` | `xigua-mochi-medium` | xAI | Grok 4.3 | 2026-09-06 |  |
| 30 | `spacexai-4.5` | `strawberry-whoopiepie` | xAI | Grok 4.5 | 2026-09-06 |  |
| 31 | `grok-build0.1` | `xinomavro-cake` | xAI | Grok Build 0.1 | 2026-09-06 |  |
| 32 | `deepseek-v4flash` | `baseten-deepseek-v4-flash` | DeepSeek | DeepSeek V4 Flash | 2026-10-17 | ⭐ |
| 33 | `deepseek-v4.1flash` | `baseten-deepseek-v4.1-flash` | DeepSeek | DeepSeek V4.1 Flash | 2026-10-17 | ⭐ |
| 34 | `deepseek-v4pro` | `baseten-deepseek-v4-pro` | DeepSeek | DeepSeek V4 Pro | 2026-09-06 |  |
| 35 | `glm-5.3` | `baseten-glm-5.3` | Zhipu | GLM 5.3 | 2026-10-17 | ⭐ |
| 36 | `glm-5.3flash` | `baseten-glm-5.3-flash` | Zhipu | GLM 5.3 Flash | 2026-10-17 | ⭐ |
| 37 | `glm-5.2` | `baseten-glm-5.2` | Zhipu | GLM 5.2 | 2026-09-06 |  |
| 38 | `auto` | `auto` | Notion | Auto (Notion picks) | 2026-10-17 | ⭐ |
| 39 | `fable-5.1` | `assam-chai` | Notion | Fable 5.1 | 2026-10-17 | ⭐ |
| 40 | `fable-5` | `acai-budino-high` | Notion | Fable 5 | 2026-09-06 |  |

> 原归档声称曾完成部分模型的在线校验；本轮没有携带真实账号重新验证。请用自己的账号运行 `scripts/sync_models.py`，并实际发送聊天请求确认可用性。

完整说明（含别名、来源与验证方法）见 [`docs/MODEL_CATALOG.md`](./docs/MODEL_CATALOG.md)。

---

## API 用法

任意字符串都能当 API key（若 `.env` 里设置了 `API_KEY` 则必须匹配）。

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="any-string")

resp = client.chat.completions.create(
    model="claude-opus5.5",          # 也可以写 opus-5.5 / albuquerque-quinn
    messages=[{"role": "user", "content": "你好"}],
    stream=True,
)
for chunk in resp:
    print(chunk.choices[0].delta.content or "", end="")
```

| 端点 | 方法 | 说明 |
|---|---|---|
| `/v1/chat/completions` | POST | 聊天补全（核心） |
| `/v1/models` | GET | 模型列表（含 provider / display_name / codename / is_default） |
| `/v1/models/{id}` | GET | 单个模型，支持别名与 Notion 代号 |
| `/health` | GET | 账号池、运行时、模型数量、上游版本 |
| `/` | GET | 内置 Web UI |

---

## 模型同步（重点）

Notion 每隔几周就会加模型（3.7 加 Kimi K3，3.8 一次加了 7 个）。本项目提供两层保障：

### 1. 对着 Notion 实时接口自检

```bash
python scripts/sync_models.py            # 对比线上 getAvailableModels 与本地目录
python scripts/sync_models.py --raw      # 同时打印上游 JSON，便于排查字段变化
python scripts/sync_models.py --json     # 机器可读，适合 CI
```

输出示例：

```text
[catalog] 35 models / 8 providers, default=claude-sonnet5.5, newest row=2026-10-17
[upstream] POST https://app.notion.com/api/v3/getAvailableModels
[upstream] 37 codenames, 35 known, 2 missing
  + NOT IN PROJECT: almond-tart   (Some New Model)
```

退出码：`0` 全部已知 / `1` 网络或上游异常 / `2` 凭据失效（401）/ `3` 发现本地缺失的新模型。

> 接口形状未公开，解析器做了多层兜底；如果 Notion 改了返回结构，用 `--raw` 打印原文后调整 `app/model_sync.py`。

### 2. 单表 + 代码生成

模型目录只有一个真相源：`app/model_registry.py` 里的 `MODEL_CATALOG`。新增模型 = 加一行 + 跑生成器：

```bash
# 1) 在 MODEL_CATALOG 增加一行（id / Notion 代号 / 显示名 / 厂商 / 别名）
# 2) 重新生成 Web UI 与派生表
python scripts/gen_model_data.py
# 3) 跑测试
python -m pytest -q
```

`python -m pytest -q` 里有一条 `gen_model_data.py --check` 风格的守护测试（手动执行 `python scripts/gen_model_data.py --check` 可接入 CI）。

---

## Web UI

访问 `http://localhost:8000`：

- 按厂商分组的模型选择器（40 个目录项，新增模型带 `New` 角标）
- Thinking 面板（可折叠 + 计时）、Search 面板（查询词 + 来源链接）
- 会话管理：新建 / 重命名 / 删除 / 收藏、主题切换、环境粒子动画
- 移动端适配

---

## 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `NOTION_ACCOUNTS` | 账号 JSON 数组（或用 `accounts.json`） | 必填 |
| `NOTION_URL` | 上游站点 | `https://app.notion.com` |
| `NOTION_DOMAIN` | `login.py` 写 cookie 的域 | `app.notion.com` |
| `NOTION_CLIENT_VERSION` | 客户端版本头 | `23.13.20261017.0323` |
| `NOTION_RUNTIME` | `agent_service` / `legacy` | `agent_service` |
| `NOTION_IMPERSONATE` | curl_cffi TLS 指纹 | `chrome` |
| `NOTION_DEBUG_OVERRIDES` | legacy 调试开关 | `false` |
| `AGENT_SERVICE_TIMEOUT_S` | 单次 agent 回复超时 | `240` |
| `AGENT_SERVICE_DELETE_THREAD` | 回复后删除 Notion 线程 | `false` |
| `STREAM_KEEPALIVE_S` | SSE 心跳间隔 | `15` |
| `FIRST_ITEM_WAIT_S` | 首包等待上限 | `20` |
| `DEFAULT_MODEL` | 默认模型 | `claude-sonnet5.5` |
| `APP_MODE` | `lite` / `standard` / `heavy` | `standard` |
| `API_KEY` | 客户端 Bearer Token | 空（不鉴权） |
| `SILICONFLOW_API_KEY` | heavy 模式压缩服务 | 空 |
| `DB_PATH` | SQLite 路径 | `./data/conversations.db` |
| `HOST` / `PORT` / `HOST_PORT` | 监听地址 / 端口 | `0.0.0.0` / `8000` / `8000` |
| `ALLOWED_ORIGINS` | CORS | `*` |
| `DISABLE_RATE_LIMIT` | 关闭限流 | `false` |
| `LOG_LEVEL` / `TZ` | 日志级别 / 时区 | `INFO` / `Asia/Shanghai` |

---

## 常见问题

**Q：返回 `temporarily-unavailable` / `UserValidationError` / 空流？**
Notion 在 AI 接口上校验 TLS 指纹，python-requests / cloudscraper 会被识别。确认已安装 `curl_cffi` 且 `NOTION_IMPERSONATE=chrome`。

**Q：升级后请求全部 401？**
凭据过期。运行 `python login.py --check`，必要时重新 `python login.py`。同步工具 `sync_models.py` 退出码 `2` 也是同一原因。

**Q：模型列表里没有某个模型，但 Notion 网页里有？**
先跑 `python scripts/sync_models.py`。若报 `NOT IN PROJECT`，把对应代号加进 `MODEL_CATALOG` 即可；如果返回 401 说明凭据问题。

**Q：`auto` 模型在 legacy 运行时会怎样？**
legacy 不支持「自动选择」，会自动回退到 `DEFAULT_MODEL` 对应的代号。

**Q：长任务 / Opus 深度思考时连接被掐断？**
agent_service 会在静默期发 `: keepalive` SSE 注释（默认 15s），并把上游拉取放到线程里，不会阻塞事件循环。若你前面还有一层 nginx，请设置 `proxy_buffering off` 并放宽 `proxy_read_timeout`。

**Q：如何切换默认模型？**
改 `.env` 的 `DEFAULT_MODEL`（任意 `/v1/models` 中的 id），或让客户端显式传 `model`。

---

## 项目结构

```text
app/
  model_registry.py    # ★ 唯一真相源：40 个目录项（id / 代号 / 厂商 / 别名）
  model_sync.py        # ★ getAvailableModels 探测与解析
  notion_client.py     # ★ agent_service + legacy 双运行时、curl_cffi 传输
  api/models.py        # /v1/models + /v1/models/{id}
  api/chat.py          # /v1/chat/completions（含 keepalive 泵）
  stream_parser.py     # legacy NDJSON 解析
  conversation.py      # 对话/转录构建
  server.py            # FastAPI 入口、鉴权、健康检查
frontend/              # 内置 Web UI（模型表由脚本生成）
scripts/
  sync_models.py       # ★ 模型同步 CLI
  gen_model_data.py    # ★ 前后端模型表代码生成
  connect.py / resume_login.py / deploy.sh / manage.sh / extract_notion_info.js
login.py               # 浏览器辅助登录入口
tests/                 # pytest 用例
docs/                  # 模型目录、加模型指南、变更日志
```

---

## 模型数据来源与验证

本项目不是拍脑袋补模型名：

1. **Notion 官方发布说明**：[2026-09-15 Notion 3.7](https://www.notion.com/releases/2026-09-15)（"including Opus 5, GPT-5.6 Sol, and Kimi K3" + 新版模型选择器）、[2026-10-13 Notion 3.8](https://www.notion.com/releases/2026-10-13)（"Seven new models all added, including GPT 6.1-Sol, GPT-6 Luna, Opus 5.5, and Sonnet 5.5"）。
2. **Notion 线上接口**：`POST https://app.notion.com/api/v3/getAvailableModels` 是模型列表的真实来源（无凭据时返回 401，说明端点存在且需要登录）；`scripts/sync_models.py` 就是它的封装。
3. **社区已验证的代号**：[upstream PR #29](https://github.com/maverickxone/notion2api/pull/29)（2026-10-17，作者注明 "codenames from getAvailableModels"）给出了 3.7/3.8 新模型的内部代号，本项目据此建表并补充了别名、图标、厂商分组。
4. **REA 逆向分析**：用 REA 对 `app.notion.com` 的 Web 客户端 bundle 做了静态应用图分析（evidence: `ev_607b…`），确认了客户端版本头 `23.13.20261017.0323`、新的 `app.notion.com` 域名与模型相关配置；并用 REA 对原始 zip 做了归档清单核对。

---

## 兼容性

| 客户端 | 状态 | 备注 |
|---|---|---|
| Cherry Studio | ✅ | 推荐 |
| Open WebUI / LobeChat | ✅ | 标准 OpenAI 协议 |
| Zotero 翻译 | ✅ | 速度略慢，Sonnet / Opus 更准 |
| 沉浸式翻译 | ⚠️ | 首包约 3s，延迟偏高 |
| Claude Code | ❌ | 需要 Anthropic 原生协议 |

> 上述客户端兼容表来自项目原有说明，本轮未逐个实测。由于 Notion AI 本身排队 + agent 启动，首 token 通常需要约 3 秒；Opus 深度思考可能更久（这也正是 keepalive 存在的原因）。

---

## 许可证与致谢

MIT License。

- 原始项目：[maverickxone/notion2api](https://github.com/maverickxone/notion2api)（MIT）
- 新协议 / TLS / 长任务修复参考：[PR #29](https://github.com/maverickxone/notion2api/pull/29)
- 模型来源：Notion 官方 release notes + `getAvailableModels`

如果这个项目对你有帮助，请给上游仓库一个 Star ⭐。