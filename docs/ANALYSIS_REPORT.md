# 逆向分析报告 / Analysis Report

日期：2026-10-17　目标：原始项目归档（upstream `maverickxone/notion2api`，提交 `5882102`，2026-09-07）

> 本文保留为历史分析记录，包含当时的结论；本轮仅核对本地代码和离线测试，未重新验证这些线上模型及服务变迁的描述。

## 1. 任务与结论

任务：分析旧反代项目的模型列表为何过时，找出 Notion 当前实际支持的最新模型，产出一个带新模型的新反代项目。

结论：

- 旧项目是**硬编码快照**：23 个模型，最后更新 2026-09-06；Notion 在 9 月中旬到 10 月中旬连续发布了 3.7 / 3.8，模型池已扩到 35 个（含 `auto`）。
- 旧项目的**上游协议也过时**：2026-10 起 Notion Web 端使用 `agent_service`（`createAgentThread` + `listenToThreadTranscript`），并开始按 TLS 指纹拒绝 python 客户端；旧代码会得到 502 空流 / `temporarily-unavailable`。
- 旧项目域名 `www.notion.so` 已不是 Web 客户端入口，现为 `app.notion.com`。
- 因此新版同时升级了**模型层**与**传输/协议层**，并提供一个可重复执行的模型同步工具，避免再次过时。

## 2. 分析方法

| 步骤 | 方法 | 结果 |
|---|---|---|
| 源码审计 | 解包 zip，读 `app/model_registry.py`、`docs/ADD_MODEL.md`、`docs/PROJECT_PROGRESS.md` | 确认模型名单是 3 个手写 dict + 2 份前端副本，无运行时发现机制 |
| 上游追溯 | GitHub API 对比 upstream `main`、63 个 fork、PR | upstream 停在 2026-09-07；PR #29（2026-10-17）带新协议与“codenames from getAvailableModels” |
| 官方发布说明 | notion.com/releases 3.7 / 3.8 | 3.7 提到 Opus 5 / GPT-5.6 Sol / Kimi K3；3.8 明确“Seven new models ... GPT 6.1-Sol, GPT-6 Luna, Opus 5.5, Sonnet 5.5” |
| 接口探测 | `POST https://app.notion.com/api/v3/getAvailableModels` | 401 Unauthorized（端点存在且需登录）；这是模型列表的权威来源 |
| 客户端分析（REA） | REA `analyze_javascript_application` 对 `app.notion.com` 的 13 个首屏 bundle 做静态应用图分析 | 确认客户端版本 `23.13.20261017.0323`、`app.notion.com` 入口、模型配置（`orange-mousse` 作为 setup 默认模型）等静态事实 |
| 交叉验证 | PR #29 的 registry diff、社区 fork 的 registry | 11 个新代号与 3.7/3.8 发布说明一一对应 |

REA 证据：`ev_607b54488629171f56796d5517a92914dae58a26f58d554c8bac9550630e2e6a`（Notion Web bundle 的 `analyze_javascript_application` 父证据；summary view `ev_0c11995140df5655869b7e626108476740331e19d4c15412e4a5541e01cd3c83`）。覆盖状态 `complete-within-view`，缺陷/限制已在证据中列明（例如体积过大导致部分文件语义分析未启动）。

## 3. 关键发现

### 3.1 模型（新增 11 + Auto）

| API 名 | Notion 代号 | 依据 |
|---|---|---|
| gpt-6.1-sol | omniberry-sundae | Notion 3.8 |
| gpt-6-luna | omodi | Notion 3.8 |
| claude-opus5.5 | albuquerque-quinn | Notion 3.8 |
| claude-sonnet5.5 | achira-donut | Notion 3.8 |
| claude-haiku5.5 | amla-jam | Notion 3.8 同期 |
| gemini-3.6flash | vertex-gemini-3.6-flash | 3.8 前后 |
| gemini-3.7flash | grapefruit-zeppole | 3.8 前后 |
| gpt-5.4-mini | oregon-grape-medium | 3.8 前后 |
| gpt-5.4-nano | otaheite-apple-medium | 3.8 前后 |
| deepseek-v4flash | baseten-deepseek-v4-flash | 3.8 前后 |
| kimi-k3 | fireworks-kimi-k3 | Notion 3.7 |
| auto | auto | 新版模型选择器 |

### 3.2 协议与传输

- `agent_service`：createAgentThread 提交摊平后的 prompt + model，然后 listenToThreadTranscript 读 NDJSON 增量（`agent_service_transcript_delta`，patch op: `put/patch/session_status`，entity kind: `assistant_message/thinking/turn_completed`）。
- TLS：Notion 对 AI 端点校验 TLS/JA3，python-requests / cloudscraper 会被拒；curl_cffi `impersonate=chrome` 可解。
- 长任务：agent 思考期可静默数分钟，需 SSE 心跳 + 非阻塞泵，否则 Cloudflare ~100s 空闲断连。

### 3.3 域名/版本

- `app.notion.com` 为 2026-10 的 Web/API 入口（`www.notion.so`、`www.notion.com` 的 AI 路径在本机网络下被重置，且官方 release 链接均指向 `app.notion.com`）。
- 客户端版本头：`23.13.20261017.0323`（HTML `data-notion-version`）。

## 4. 新项目的改动

1. `MODEL_CATALOG` 单一真相源（35 行），派生 76 个别名 + 8 组厂商 + 图标/显示名。
2. `/v1/models` 增加元数据与 `/v1/models/{id}`（别名/代号反查）。
3. `app/model_sync.py` + `scripts/sync_models.py`：直连 getAvailableModels 做 diff，退出码可用于 CI。
4. `scripts/gen_model_data.py`：前后端模型表由注册表生成，`--check` 防漂移。
5. 传输层采用 PR #29 的 agent_service + curl_cffi + keepalive；legacy 保留为可选项。
6. 默认模型、域名、客户端版本、Docker/镜像名、文档全部同步。
7. 36 个测试覆盖注册表 / API / agent_service 解析 / 同步解析。

## 5. 局限与不确定性（必须说明）

- **代号未用真实账号二次验证**：本次分析环境没有可用的 Notion 凭据，`getAvailableModels` 返回 401。11 个新代号取自 PR #29 作者标注“来自 getAvailableModels”的 registry，并与 3.7/3.8 发布说明交叉核对；**最终以 `python scripts/sync_models.py`（用你的账号）为准**。
- getAvailableModels 的响应结构未公开，同步解析器做了多层兜底；若 Notion 改结构，用 `--raw` 打印后调整。
- Notion 可能随时重命名内部代号 / 下线模型；`does not support selected model` 时应重新 sync。
- `gemini-3.6flash` 的 legacy thread type 按 vertex 前缀推断为 `markdown-chat`，未逐模型活体验证（agent_service 下无影响）。
- REA 静态分析不等价运行时：端点/模型配置是静态候选与官方发布说明的交叉结论，非运行时抓包。

## 6. 复现步骤

```bash
# 1) 本地目录完整性
python -m pytest -q

# 2) 生成物一致性
python scripts/gen_model_data.py --check

# 3) 用真实凭据核对 Notion 线上模型池
python scripts/sync_models.py
```