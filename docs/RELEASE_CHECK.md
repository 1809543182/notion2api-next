# 发布前检查（2026-10-18）

## 隐私检查

- 检查对象：用户提供的 `notion2api-next-v2.0.1-github.zip` 及整理后的发布源码。
- 原始 ZIP SHA-256：`997593e7ed5f00428631c6c02e6ff77e361bae98cd851ca44c8083f7e046645b`。
- 原包未包含 `.env`、真实 `accounts.json`、数据库、浏览器目录、日志或 Git 历史。
- 使用 Gitleaks 8.30.1 扫描原始解包目录和发布目录，均未发现符合检测规则的密钥残留。对账号字段、邮箱、UUID、Windows 本机路径和常见密钥格式补充检索；邮箱仅为示例，原文档的一处本机路径已清理。
- 后续新增 Docker CI 中的固定虚构测试 Key `ci-test-key` 被识别为 curl Authorization 候选，已人工核对为本次新建的临时测试容器凭据；不关联真实账号、部署或服务。它不是原包遗留的密钥。
- 运行时敏感文件仍被 `.gitignore` 与 Docker 上下文忽略。扫描不构成绝对无隐私保证；后续提交自己的运行文件前仍需检查。

## 已完成的本地验证

- 在独立 Windows / Python 3.11.15 虚拟环境中安装项目与测试依赖，`pip check` 通过。
- 原有 39 项测试通过；增加 11 项认证及凭据回归检查后，合计 **50 项通过**。
- 覆盖错误/缺失/格式异常 Bearer、正确 Key、空 Key、公开健康接口、上游 Cookie 与客户端 Key 分离、错误响应不回传上游原文、账号保存时保留其他 .env 设置。
- 实际启动 uvicorn，HTTP 验证 `/`、前端 JS、`/health` 与模型接口；无 Key/错误 Key 返回 401，正确 Key 返回 200，模型目录为 40 项。使用虚构账号，没有向 Notion 发送请求。
- 前后端模型生成一致性检查、Python 编译与登录 CLI 的 `--help` 入口通过。
- Compose 配置解析通过，检查了构建上下文、只读账号挂载与本机端口绑定。
- 公开上传后重新从 GitHub 克隆，50 项测试、前后端生成一致性及 HTTP 启动检查通过；导出 ZIP 重新解压后 HTTP 启动检查通过。
- [GitHub CI](https://github.com/1809543182/notion2api-next/actions/runs/39081769243)：Windows、Linux、macOS 各 50 项测试及代码检查通过；Linux Docker 镜像构建、Compose 启动、健康接口、首页和 API Key 校验全部通过。受测代码提交为 `6de8913e34796fcd355109df01cfbb55e8223dda`。

## 尚未证明的部分

- 本机 Docker daemon 未运行；Docker 已在 GitHub Linux 环境实测，其他宿主平台的 Docker 尚未逐一验证。
- 没有使用真实账号完成交互登录、上游聊天及所有模型验证。模型快照不是订阅权限或实际调用成功的保证。
- macOS/Linux 浏览器登录需要对应系统实测；三平台 CI 仅运行离线测试和代码检查，不会代替浏览器登录测试。
- 新电脑需要自己的有效账号、Python/浏览器和网络；项目不是离线、零配置的软件包。
- 测试依赖中的 Starlette/httpx 组合有弃用提示，目前测试通过。

跨平台 CI 的最新结果以 GitHub Actions 为准。
