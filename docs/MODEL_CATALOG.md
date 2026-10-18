# 模型目录 / Model Catalog

快照时间：**2026-10-17**，对应 Notion **3.8**。共 **40** 个目录项（含 `auto`），默认 `claude-sonnet5.5`。

> 真相源：`app/model_registry.py` 的 `MODEL_CATALOG`。本文表由脚本生成核对，请勿手改代码以外的副本。

## 原归档记载的实机校验（2026-10-17，未在本轮复验）

⟦POST https://app.notion.com/api/v3/getAvailableModels⟧（请求体必须带 ⟦{"spaceId": "..."}⟧，否则 400）返回 **39** 个模型。与目录比对：

**线上有、目录原先没有（已补齐）**

| 代号 | 显示名 | 厂商 | 档位 |
|---|---|---|---|
| ⟦soursop-shortcake⟧ | Grok 4.6 | xAI | intelligent |
| ⟦oatmeal-cookie⟧ | GPT-5.2 | OpenAI | fast |
| ⟦baseten-deepseek-v4.1-flash⟧ | DeepSeek V4.1 Flash | DeepSeek | fast |
| ⟦baseten-glm-5.3⟧ | GLM 5.3 | Zhipu | intelligent |
| ⟦baseten-glm-5.3-flash⟧ | GLM 5.3 Flash | Zhipu | fast |
| ⟦assam-chai⟧ | Fable 5.1 | Anthropic | intelligent |

**目录有、线上已下架（已移除）**

| 代号 | 显示名 |
|---|---|
| ⟦fireworks-kimi-k2.7⟧ | Kimi K2.7 Code |

**活体调用验证**：⟦claude-sonnet5.5⟧（27s）、⟦glm-5.3⟧（32s）、⟦gpt-6.1-sol⟧（15s）、⟦claude-haiku5.5⟧ 流式（17s）全部 HTTP 200 且内容正确。

## 全表

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

## 本次新增的 11 个模型 + Auto

| 模型 | 代号 | 依据 |
|---|---|---|
| GPT-6.1 Sol | `omniberry-sundae` | Notion 3.8："including GPT 6.1-Sol ..." |
| GPT-6 Luna | `omodi` | Notion 3.8 新增 7 模型之一 |
| Sonnet 5.5 | `achira-donut` | Notion 3.8："... Opus 5.5, and Sonnet 5.5" |
| Opus 5.5 | `albuquerque-quinn` | Notion 3.8 |
| Haiku 5.5 | `amla-jam` | Notion 3.8 同期模型 |
| Gemini 3.6 Flash | `vertex-gemini-3.6-flash` | 3.8 前后新增（vertex 前缀，legacy 走 markdown-chat） |
| Gemini 3.7 Flash | `grapefruit-zeppole` | 3.8 前后新增 |
| GPT-5.4 Mini | `oregon-grape-medium` | 3.8 前后新增（OpenAI 小参数档） |
| GPT-5.4 Nano | `otaheite-apple-medium` | 3.8 前后新增 |
| DeepSeek V4 Flash | `baseten-deepseek-v4-flash` | 3.8 前后新增 |
| Kimi K3 | `fireworks-kimi-k3` | Notion 3.7："... and Kimi K3" |
| Auto | `auto` | Notion 新版模型选择器的「自动」 |

> 内部代号来源：`POST /api/v3/getAvailableModels`，与 upstream PR #29（2026-10-17）作者注明的一致。代号属于 Notion 内部标识，Notion 可能随时更换；若某个模型报 `does not support selected model`，用 `sync_models.py` 重新核对。

## 别名（Aliases）

每个模型都带一组别名，客户端可以用更常见的写法：

- Claude：`claude-opus-5.5` / `opus-5.5` / `opus5.5` / `claude-opus-5-5`
- GPT：`gpt-6.1` → `gpt-6.1-sol`；`gpt-6-luna` / `gpt6-luna`
- Gemini：`gemini-3.7-flash`、`gemini-3.6-flash`、`gemini-3.1-pro`
- Kimi：`kimi-3` → `kimi-k3`；`kimi-k2.7-code` → `kimi-2.7`
- xAI：`grok-4.5` → `spacexai-4.5`；`grok-build-0.1`
- DeepSeek：`deepseek-v4-flash` / `deepseek-v4-pro`
- Notion：`default`、`notion-auto` → `auto`；`fable5`、`claude-fable5`

此外，**Notion 原始代号本身也可以直接当 model 传入**（如 `achira-donut`），内部会反查回标准 id。

## 验证方法

```bash
# 1) 列出全部模型
curl -s http://localhost:8000/v1/models | python -m json.tool

# 2) 查单个模型（别名也可以）
curl -s http://localhost:8000/v1/models/opus-5.5

# 3) 对 Notion 线上接口做 diff（需要有效凭据）
python scripts/sync_models.py

# 4) 本地目录完整性
python -m pytest -q
```

## 数据来源

1. [Notion 3.7 release notes (2026-09-15)](https://www.notion.com/releases/2026-09-15)
2. [Notion 3.8 release notes (2026-10-13)](https://www.notion.com/releases/2026-10-13)
3. `POST https://app.notion.com/api/v3/getAvailableModels`（未认证返回 401，端点真实存在）
4. [upstream PR #29](https://github.com/maverickxone/notion2api/pull/29) — 新旧模型代号交叉验证
5. REA 对 `app.notion.com` 前端 bundle 的静态分析（确认客户端版本与域名迁移）