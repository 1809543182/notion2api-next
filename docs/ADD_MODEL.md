# 新增模型清单（v2）

> v2 起模型定义收敛为**单一真相源**：只要改 `app/model_registry.py` 的 `MODEL_CATALOG` 一行，其余全部由代码生成。
> 旧版需要手改 6 个文件的做法已废弃。

## 需要准备的信息

| 字段 | 说明 | 示例 |
|---|---|---|
| `id` | 客户端使用的公开模型名（稳定、不可随意改） | `claude-opus5.5` |
| `codename` | Notion 内部模型代号（来自 `getAvailableModels`） | `albuquerque-quinn` |
| `display` | UI / `/v1/models` 显示名 | `Opus 5.5` |
| `provider` | 厂商分组（须在 `PROVIDER_ORDER` 中，或先加分组） | `Anthropic` |
| `family` | 模型族，用于 Gemini 特判 / 统计 | `claude` |
| `aliases` | 额外可接受的写法（可选） | `("opus-5.5",)` |
| `badge` | UI 角标（可选） | `"New"` |
| `released` | 加入目录的日期 | `"2026-10-17"` |

## 操作步骤

### 1. 加一行

在 `app/model_registry.py` 的 `_ROWS` 末尾（或对应厂商分组内）加：

```python
("claude-opus5.5", "albuquerque-quinn", "Opus 5.5", "Anthropic", "claude",
 ("claude-opus-5.5", "opus-5.5", "opus5.5"), "New", "Strongest Claude reasoning", "2026-10-17"),
```

列顺序固定：`id, codename, display, provider, family, aliases, badge, desc, released`。

### 2. 重新生成前端与派生表

```bash
python scripts/gen_model_data.py
```

会更新：

- `frontend/index.html`（Web UI 内联常量）
- `frontend/js/core/constants.js`（模块化常量）
- `/v1/models` 输出、`DISPLAY_NAMES / MODEL_ICONS / MODEL_PROVIDERS / MODEL_ALIASES` 等派生表在 import 时自动生成

### 3. 自检

```bash
python -m pytest -q
python scripts/gen_model_data.py --check   # CI 用法
```

### 4.（可选）对着 Notion 线上接口验证

```bash
python scripts/sync_models.py
```

退出码 `3` 表示 Notion 还有本地没有的代号，按提示补 `_ROWS` 即可。

## 下线模型

从 `_ROWS` 删除对应行，然后同样执行 `gen_model_data.py` + 测试。
注意同步更新 `DEFAULT_MODEL`（若删除的是默认模型）。

## 常见坑

- 代号必须与 `getAvailableModels` 完全一致；写错会得到 `does not support selected model`。
- 新增厂商时，加 `PROVIDER_ORDER` 条目和 `PROVIDER_ICONS` 图标，否则 UI 分组缺失。
- Gemini `vertex-` 前缀的模型在 legacy 运行时需要走 `markdown-chat`，记得加入 `MARKDOWN_CHAT_MODELS`。
- agent_service 运行时忽略 thread type，`auto` 也是该运行时专属。