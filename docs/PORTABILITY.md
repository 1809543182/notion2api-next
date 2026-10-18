# 在其他电脑运行

## 条件

- Python 3.11+，推荐 3.11；自动登录需要 Chrome、Edge 或 Chromium。也可手动配置自己的 `accounts.json`。
- 首次安装需要访问 Python 包源；实际聊天需要能访问 Notion，并拥有相应 AI 权限。
- 下载 GitHub ZIP 后完整解压，或 `git clone https://github.com/1809543182/notion2api-next.git`。
- 仓库不包含运行账号、API Key、虚拟环境、聊天数据库或本机代理配置；不依赖维护者电脑上的任何路径。

## 本地启动

Windows 双击 `start.bat`；macOS/Linux 在终端运行 `bash start.sh`。启动器会创建项目自己的 `.venv` 并安装依赖，再复制 `.env.example` 为 `.env`，最后引导登录和启动服务。按 Ctrl+C 停止。启动器固定使用本机 8000 端口。

若系统缺少 venv 模块，先安装对应 Python 的 venv 支持。遇到浏览器发现失败，可在运行前设置 `CHROME_PATH` 为浏览器可执行文件的完整路径，或使用手动方式。

手动方式（激活虚拟环境后）：

```sh
python -m pip install -r requirements.txt -c constraints.txt
python login.py --manual
python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
```

手动启动前也应复制 `.env.example` 为 `.env` 并检查设置。已有账号但不使用自动登录时，按 `accounts.example.json` 的结构填写 `accounts.json`，将三个必填占位符全部替换为自己的有效值。示例不是可用账号。

访问 `http://127.0.0.1:8000`。健康检查与模型目录：

```sh
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $API_KEY" http://127.0.0.1:8000/v1/models
python scripts/sync_models.py
```

设置了 API_KEY 时，客户端配置同一个 Key；它与 Notion `token_v2` 不同。`HOST`/`PORT` 不会覆盖手动 uvicorn 命令行参数，需在命令行显式指定。

需要代理时，在自己的 `.env` 设置 `NOTION_PROXY`，使用本机实际地址。远程机器/容器中的 `127.0.0.1` 指向它自己，不能直接套用原电脑代理端口。

## Docker

先在宿主机完成登录，准备 `.env` 和真实的 `accounts.json`；无需把浏览器或登录工具装进容器。

```sh
docker compose up -d --build
docker compose logs --tail=50
docker compose down
```

Docker 默认绑定本机；确需远程访问时，在设置鉴权和 HTTPS 后再调整 `BIND_HOST`。账号只读挂载，缺文件会直接报错。数据库使用命名卷，`docker compose down` 后继续保留；`down -v` 会删除数据，请勿用作普通停止命令。旧版手动 bind-mount 的数据库不会自动迁入该命名卷。

本次本机 Docker daemon 未启动；已改在 GitHub 托管的 Linux 环境中完成镜像构建、容器启动、健康检查、静态首页和模型接口鉴权验证，全部通过。Windows、Linux、macOS 的离线测试也全部通过。见 [CI 验证记录](https://github.com/1809543182/notion2api-next/actions/runs/39081769243)。macOS/Linux 自动浏览器登录仍需实际账号与交互环境验证。

## 依赖与验证范围

`constraints.txt` 固定本次 Windows/Python 3.11 验证时的依赖版本。它约束所需依赖版本，不会强制安装其中所有工具。其他平台特有依赖可能不在该快照内；新平台应运行测试，不能将这个文件视为所有平台的哈希锁文件。

本次离线测试使用虚构账号：检查模型目录、流解析、本地 HTTP 入口、入站 API Key、账号解析和 Cookie 组装。真实 Notion 登录、模型可用性与云端聊天取决于账号和上游变化，需要部署者在线验证。`/health` 为本地存活检查，不是 Notion 账号有效性检查。
