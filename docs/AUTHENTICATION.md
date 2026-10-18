# 认证与凭据处理

本文依据本仓库代码，说明两个相互独立的认证边界。项目没有 OAuth 授权服务器、JWT 签发服务或自动刷新 Notion 登录态的流程。

## 组件

| 组件 | 代码 | 职责 |
|---|---|---|
| 登录助手 | `login.py` | 启动临时 Chrome/Edge，通过本机 CDP 读取 Cookie；调用 `getSpaces`、`loadUserContent` 组合账号与工作区 |
| 连接与恢复 | `scripts/connect.py`、`scripts/resume_login.py` | 本机状态页、网络回退、待恢复 token、模型查询 |
| 配置 | `app/config.py` | 加载 `.env` 和账号；校验 `token_v2`、`space_id`、`user_id` 三项必填字段 |
| 入站鉴权 | `app/server.py:api_key_auth` | 对 `/v1*` 的非 OPTIONS 请求检查 `Authorization: Bearer <API_KEY>` |
| 账号池 | `app/account_pool.py` | 轮询选择 Notion 客户端，失败时短暂冷却；不刷新登录态 |
| 上游客户端 | `app/notion_client.py` | 把 Notion Cookie、活跃用户和工作区头发送给 `NOTION_URL` |
| 模型同步 | `app/model_sync.py` | 使用相同账号 Cookie 请求 `getAvailableModels`，供同步脚本比较模型快照 |
| Web UI | `frontend/js/core/state.js`、`frontend/js/api/client.js`、`frontend/js/chat/streaming.js` | 保存客户端 API Key 并作为 Bearer 发送给配置的 API 地址 |

## 请求流程

1. 用户在 `login.py` 打开的临时浏览器中自行登录 Notion。登录密码不由本项目接收；项目提取登录后的 `token_v2` 与 Cookie，解析用户、工作区和可选 `space_view_id`。
2. 登录助手将凭据以明文写入本机 `accounts.json`，默认也同步到 `.env` 的 `NOTION_ACCOUNTS`。两份文件均被 Git 和 Docker 上下文忽略。POSIX 系统设置文件权限为 `600`；Windows 仍需依靠账户与 NTFS 权限保护。
3. 服务启动时，显式环境变量优先于 `.env`；但非空 `accounts.json` 的账号内容优先于 `NOTION_ACCOUNTS`。账号只在启动时加载，修改后需要重启。
4. 客户端请求 `/v1/chat/completions`。如果配置了 `API_KEY`，中间件完整比较 Bearer 值；缺失或错误返回 401。留空表示关闭此层鉴权。OPTIONS、静态 Web UI、`/health` 和自动生成的 API 文档不受该 Key 保护。
5. 聊天路由校验模型、组装上下文并向账号池获取客户端。入站的 `API_KEY` 不充当 Notion Cookie；后端使用自己加载的 Notion 账号。
6. 默认 `agent_service` 路径调用 `createAgentThread`，再通过 `listenToThreadTranscript` 读取流；legacy 路径使用 `runInferenceTranscript`。请求携带 Cookie（包含 `token_v2`、`notion_user_id`）、`x-notion-active-user-header`、`x-notion-space-id` 及客户端版本等头。
7. 后端将结果转为 OpenAI 兼容 JSON 或 SSE。账号失败冷却后可以重试；过期 token 必须重新登录获取，项目不提供 refresh token。

## 哪些信息保存在什么位置

| 位置 | 内容与生命周期 |
|---|---|
| `accounts.json`、`.env` | Notion token、Cookie、用户/工作区标识、可选邮箱姓名；`.env` 还可能包含本服务 `API_KEY` 和 SiliconFlow Key。长期明文保存，需自行删除和轮换 |
| `data/pending_account.json` | 连接助手失败恢复用的 token 与 Cookie；成功写入账号后删除，失败后可能继续保留 |
| 临时浏览器目录 | 登录态和缓存；助手结束时尝试删除，异常终止可能留存 |
| `data/model-sync.json` | 模型发现结果及账号标识，属于本机私有运行数据 |
| 浏览器 localStorage/sessionStorage | Web UI 的 `claude_api_key`；聊天记录另存于 `claude_chats`，API 地址另存于 `claude_base_url`。关标签页不会清除 localStorage |
| Heavy 模式 SQLite | 对话、摘要和归档；默认 `data/conversations.db`，Docker 使用命名卷 |
| 标准输出/容器日志 | 请求 IP、路径、账号邮箱或 ID、线程/会话标识及异常诊断信息。发布整理已移除原始上游响应片段，但日志仍应按私有数据处理 |

前端将 API Key 发往用户设置的 Base URL，只应填入可信服务。上游 Cookie 会发送给 `NOTION_URL` 指向的地址，因此不要把它改成不可信镜像。网络代理也属于凭据传输的信任边界。

Heavy 模式配置 `SILICONFLOW_API_KEY` 后，摘要逻辑会把需要压缩的对话内容发送到 `https://api.siliconflow.cn/v1/chat/completions`；Key 放在该请求的 Authorization 头中。标准模式不调用该摘要服务。

## 部署边界

默认启动器与 Docker 只绑定 `127.0.0.1`。向局域网或公网开放前，设置强随机 `API_KEY`、配置 HTTPS 和合适的 `ALLOWED_ORIGINS`。CORS 不是访问鉴权。

这是单个信任域的服务：所有使用同一 API Key 的客户端共享后端账号池，Heavy 会话接口没有独立用户身份隔离。不要把它作为多租户账号系统使用。

本轮检查使用虚构账号，验证的是本地鉴权与请求组装，不代表真实 Notion 登录、订阅权限和所有模型均已重新在线验证。
