# Issues & Troubleshooting / 问题排查指南

> Runtime errors show a red error card in the Web UI with the error code, cause, and suggested action.  
> 运行时错误会在 Web UI 中以红色错误卡片展示，包含错误码、原因和建议操作。  
> This document covers deployment and configuration issues not shown in the UI.  
> 本文档补充 UI 错误卡片无法覆盖的部署和配置问题。

---

## Q1: 503 — "Too Many Requests" / 请求过多

**EN:**

```
503 Service Unavailable: Notion account rate limited
```

Notion AI enforces rate limits per workspace. Rapid consecutive requests trigger a 429 from Notion, which surfaces as a 503 here.

Solutions:
1. Wait 10–30 seconds and retry — Notion's rate limit recovers quickly
2. Add more accounts to `accounts.json` — the pool automatically switches to a healthy account
3. Reduce request frequency (Lite: 30/min, Standard: 25/min, Heavy: 20/min)

---

**中文：**

```
503 Service Unavailable: Notion 账号被限流
```

Notion AI 对每个工作区有请求频率限制，连续快速请求会触发 Notion 返回 429，在本服务表现为 503。

解决方案：
1. 等待 10–30 秒后重试 — Notion 限流通常很快恢复
2. 在 `accounts.json` 中添加更多账号 — 账号池会自动切换到健康账号
3. 降低请求频率（Lite：30次/分钟，Standard：25次/分钟，Heavy：20次/分钟）

---

## Q2: 401 — Token Expired / Token 过期

**EN:**

```
401 Unauthorized: Notion upstream returned HTTP 401
```

Your `token_v2` has expired or been invalidated (Notion logs out sessions periodically).

Solutions:

Option A — Browser-Assisted (easiest):
```bash
python login.py
```

Option B — Manual F12:
1. Open https://www.notion.so/ai and log in
2. `F12` → **Application** → **Cookies** → find `token_v2` → copy Value
3. Run `scripts/extract_notion_info.js` in Console to get other fields
4. Update `accounts.json`, then restart the service

---

**中文：**

```
401 Unauthorized: Notion upstream returned HTTP 401
```

你的 `token_v2` 已过期或失效（Notion 会定期清理登录态）。

解决方案：

方式 A — 浏览器辅助（最简单）：
```bash
python login.py
```

方式 B — 手动 F12：
1. 打开 https://www.notion.so/ai 并登录
2. `F12` → **Application** → **Cookies** → 找到 `token_v2` → 复制 Value
3. 在 Console 中运行 `scripts/extract_notion_info.js` 获取其他字段
4. 更新 `accounts.json`，重启服务

---

## Q3: 405 — Method Not Allowed

**EN:**

```
405 Method Not Allowed
```

The endpoint does not support the HTTP method used.

Supported endpoints:

| Endpoint | Method |
|---|---|
| `/v1/chat/completions` | POST |
| `/v1/models` | GET |
| `/v1/conversations/{id}` | DELETE |
| `/health` | GET |

Common cause: using `/chat/completions` without the `/v1` prefix, or using GET on the chat endpoint.

Note: **Claude Code is not supported** — it uses Anthropic's native API format, which is incompatible with this service.

---

**中文：**

```
405 Method Not Allowed
```

请求的端点不支持该 HTTP 方法。

支持的端点见上表。

常见原因：URL 缺少 `/v1` 前缀，或对聊天端点使用了 GET 方法。

注意：**不支持 Claude Code** — 它使用 Anthropic 原生 API 格式，与本服务不兼容。

---

## Q4: Notion AI Suspended / Notion AI 功能被暂停

**EN:**

Notion may suspend AI access on workspaces with unusual request patterns (many thread creations from a server IP, high frequency, etc.). Business Trial workspaces are especially prone to this.

Mitigation:
- Add multiple accounts to distribute load
- Avoid extremely high request frequency
- If suspended, switch to a different workspace account

---

**中文：**

Notion 可能因异常请求模式（从服务器 IP 大量创建 thread、高频请求等）暂停工作区的 AI 功能，Business Trial 工作区尤其容易触发。

缓解方法：
- 添加多个账号分散负载
- 避免过高的请求频率
- 如已被暂停，切换到其他工作区账号

---

## Q5: Thinking Panel Not Showing / Thinking 面板不显示

**EN:** Use `APP_MODE=standard` or `heavy`. Lite mode does not support the Thinking or Search panels.

**中文：** 请使用 `APP_MODE=standard` 或 `heavy`，Lite 模式不支持 Thinking 和 Search 面板。

---

## Q6: Docker — Service Won't Start / Docker 服务无法启动

**EN:**

```bash
# Check container status
docker-compose ps

# View logs for errors
docker-compose logs --tail=50

# Verify accounts loaded correctly
docker-compose logs | grep "startup"
# Should show: "accounts": N  (N = number of accounts)
```

Common causes: malformed `accounts.json`, missing required env vars in `.env`, port already in use.

---

**中文：**

```bash
# 检查容器状态
docker-compose ps

# 查看错误日志
docker-compose logs --tail=50

# 验证账号是否正确加载
docker-compose logs | grep "startup"
# 应显示："accounts": N（N = 账号数量）
```

常见原因：`accounts.json` 格式错误、`.env` 缺少必填变量、端口被占用。

---

*Last updated / 最后更新：2026-06*
