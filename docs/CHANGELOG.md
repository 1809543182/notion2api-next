# 发布整理（2026-10-18）

- 二开维护者：1809543182；原作者：maverickxone，保留原项目与社区贡献说明。
- 更新获取 Notion accounts 的方式链路及渠道模型目录。
- 修复首次启动时依赖安装顺序、独立虚拟环境、macOS 浏览器发现和 .env 读取。
- 修复 Docker 上下文排除 scripts 导致构建失败；默认仅绑定本机，数据库使用命名卷。
- 系统环境变量优先于 .env；默认 standard 模式；Bearer Key 使用完整常量时间比较。
- 手动输入 token 隐藏回显；POSIX 凭据权限设为 600；成功连接后删除待恢复 token。
- curl 回退通过 stdin 传 Cookie，避免暴露于进程参数；清理临时浏览器目录。
- API 错误及常规日志不再输出原始上游响应片段。
- 新增认证与可移植部署文档、回归检查和依赖版本约束。

---

# Changelog

## v2.0.1 — 2026-10-17（实机校验）

- 用真实 Notion 账号调用 ⟦POST /api/v3/getAvailableModels⟧（body 需 ⟦{"spaceId": ...}⟧）拿到线上 39 个模型，与目录比对。
- 新增：Grok 4.6（⟦soursop-shortcake⟧）、GPT-5.2（⟦oatmeal-cookie⟧）、DeepSeek V4.1 Flash（⟦baseten-deepseek-v4.1-flash⟧）、GLM 5.3（⟦baseten-glm-5.3⟧）、GLM 5.3 Flash（⟦baseten-glm-5.3-flash⟧）、Fable 5.1（⟦assam-chai⟧）。
- 下架：Kimi K2.7（⟦fireworks-kimi-k2.7⟧，Notion 已不再提供）。
- ⟦scripts/sync_models.py⟧ / ⟦app/model_sync.py⟧ 修复：请求体必须带 ⟦spaceId⟧；解析支持 Notion 当前 schema（⟦models[]: model / modelMessage / modelProvider / displayGroup⟧）。
- 新增出站代理支持 ⟦NOTION_PROXY⟧（Clash 等）；⟦app/notion_client.py⟧、⟦app/model_sync.py⟧、⟦login.py⟧、⟦scripts/connect.py⟧ 全部走代理。
- 新增一键登录连接器 ⟦scripts/connect.py⟧（本地状态页 + CDP 抓取）与断点续传 ⟦scripts/resume_login.py⟧。
- 实测：⟦claude-sonnet5.5⟧ / ⟦glm-5.3⟧ / ⟦gpt-6.1-sol⟧ / ⟦claude-haiku5.5⟧（流式）全部 200。

## v2.0.0 — 2026-10-17

基于 upstream `maverickxone/notion2api` `5882102`（2026-09-07），合并社区 PR #29 的协议/传输修复，并重做模型层。

### Added

- **11 个新模型 + Auto**：GPT-6.1 Sol、GPT-6 Luna、Sonnet 5.5、Opus 5.5、Haiku 5.5、Gemini 3.6/3.7 Flash、GPT-5.4 Mini/Nano、DeepSeek V4 Flash、Kimi K3、`auto`（共 35）。
- `POST /api/v3/getAvailableModels` 实时探测：`app/model_sync.py` + `scripts/sync_models.py`（退出码 0/1/2/3，支持 `--raw` / `--json`）。
- `GET /v1/models/{id}`：支持别名与 Notion 代号反查。
- 模型别名系统（76 个别名），`/v1/models` 增加 `provider / family / notion_codename / reasoning / is_default / released` 字段。
- 前端模型表代码生成：`scripts/gen_model_data.py`（`--check` 可进 CI）。
- 36 个 pytest 用例：注册表完整性、模型 API、agent_service 流解析、同步解析。
- `accounts.example.json`、`requirements-dev.txt`、`docs/MODEL_CATALOG.md`、`docs/CHANGELOG.md`。

### Changed

- 默认模型：`claude-sonnet4.6` → `claude-sonnet5.5`（可用 `DEFAULT_MODEL` 覆盖）。
- 上游域名默认：`www.notion.so` → `app.notion.com`（`NOTION_URL` / `NOTION_DOMAIN`）。
- 客户端版本头默认：`23.13.20260228.0625` → `23.13.20261017.0323`。
- 模型注册表从 3 个散落 dict 改为单一 `MODEL_CATALOG` + 派生表。
- `/health` 增加 `version / runtime / notion_client_version / models / default_model / notion_url`。
- Docker 镜像/容器名改为 `notion2api-next` / `notion2api_next`，镜像内复制 `scripts/`。

### Added (upstream PR #29, merged here)

- `agent_service` 运行时：`createAgentThread` + `listenToThreadTranscript`，把 transcript 摊平成 agent prompt，解析 `agent_service_transcript_delta`（provisional / committed / thinking / turn_completed / error）。
- curl_cffi Chrome TLS 指纹（`NOTION_IMPERSONATE`），cloudscraper 作为回退；修复 Notion 开始拒绝 python TLS 导致的 `temporarily-unavailable` / `UserValidationError` / 空流。
- SSE keepalive 泵（`STREAM_KEEPALIVE_S`，默认 15s）+ 上游拉取放线程，避免长 agent 任务被 Cloudflare 100s 空闲切断、避免阻塞事件循环。
- `curl_cffi` 的 `iter_lines()` 兼容修复（不支持 `decode_unicode`）。

### Fixed

- 原始 registry 缺少新模型的补全：新模型图标/别名/厂商分组在本项目补齐。
- `auto` 在 legacy 运行时会正确回退默认模型（而不是发送 `auto`）。
- `claude-opus4.6` 硬编码默认值（`schemas.py` / `main.py` / `manage.sh`）统一走注册表。

### Tests

```
python -m pytest -q      # 36 passed
python scripts/gen_model_data.py --check
```