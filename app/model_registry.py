"""Single source of truth for the Notion model catalog.

Every model this proxy exposes is one row in MODEL_CATALOG. All derived tables
used by the API and the bundled Web UI (MODEL_MAP, DISPLAY_NAMES, MODEL_ICONS,
MODEL_PROVIDERS, NOTION_MODEL_REVERSE_MAP and the alias index) are generated
from that catalog. Adding a model = add one row and run
"python scripts/gen_model_data.py".

Catalog provenance (verified 2026-10-17)
---------------------------------------
* Notion 3.7 release (2026-09-15): "You get access to all the latest frontier
  models in Notion, including Opus 5, GPT-5.6 Sol, and Kimi K3. The new model
  picker is redesigned ...".
* Notion 3.8 release (2026-10-13): "Seven new models all added, including
  GPT 6.1-Sol, GPT-6 Luna, Opus 5.5, and Sonnet 5.5."
* Internal Notion codenames come from POST /api/v3/getAvailableModels.
  scripts/sync_models.py re-reads that endpoint with a live account and
  reports drift, so this table can be kept current without touching code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Provider metadata (drives ordering + icons in the Web UI)
# ---------------------------------------------------------------------------

PROVIDER_ORDER: tuple[str, ...] = (
    "Anthropic",
    "OpenAI",
    "Google",
    "Moonshot",
    "xAI",
    "DeepSeek",
    "Zhipu",
    "Notion",
)

PROVIDER_ICONS: dict[str, str] = {
    "Anthropic": "\u2733\ufe0f",
    "OpenAI": "\u2699",
    "Google": "\u2726",
    "Moonshot": "\U0001f319",
    "xAI": "\u26a1",
    "DeepSeek": "\U0001f40b",
    "Zhipu": "\u25c6",
    "Notion": "\u25c7",
}


@dataclass(frozen=True)
class ModelSpec:
    """One externally-addressable model.

    id        - the string clients send as "model" (stable public name)
    codename  - Notion's internal model id, sent in the config block
    display   - human readable name shown in /v1/models and the Web UI
    provider  - vendor bucket used for grouping
    family    - model family (used by UI badges / analytics)
    aliases   - extra client-side spellings accepted for this model
    badge     - optional UI badge ("New", "Beta", ...)
    desc      - optional one-line description for the model picker
    released  - date this row was added to the registry (YYYY-MM-DD)
    """

    id: str
    codename: str
    display: str
    provider: str
    family: str
    aliases: tuple[str, ...] = ()
    badge: str = ""
    desc: str = ""
    released: str = "2026-09-06"
    reasoning: bool = True


# Row columns: id, codename, display, provider, family, aliases, badge, desc,
# released. Newest first inside every provider group.
_ROWS: tuple[tuple[Any, ...], ...] = (
    # ---- Anthropic -------------------------------------------------------
    ("claude-sonnet5.5", "achira-donut", "Sonnet 5.5", "Anthropic", "claude", ("claude-sonnet-5.5", "claude-sonnet-5-5", "sonnet-5.5", "sonnet5.5"), "New", "Balanced speed & quality (recommended)", "2026-10-17"),
    ("claude-opus5.5", "albuquerque-quinn", "Opus 5.5", "Anthropic", "claude", ("claude-opus-5.5", "claude-opus-5-5", "opus-5.5", "opus5.5"), "New", "Strongest Claude reasoning", "2026-10-17"),
    ("claude-haiku5.5", "amla-jam", "Haiku 5.5", "Anthropic", "claude", ("claude-haiku-5.5", "haiku-5.5", "haiku5.5"), "New", "Fastest Claude", "2026-10-17"),
    ("claude-opus5", "agave-flan", "Opus 5", "Anthropic", "claude", ("claude-opus-5", "opus-5", "opus5"), "", "", "2026-09-06"),
    ("claude-sonnet5", "angel-cake-high", "Sonnet 5", "Anthropic", "claude", ("claude-sonnet-5", "sonnet-5", "sonnet5"), "", "", "2026-09-06"),
    ("claude-sonnet4.6", "almond-croissant-low", "Sonnet 4.6", "Anthropic", "claude", ("claude-sonnet-4.6", "claude-sonnet-4-6", "sonnet-4.6", "sonnet4.6"), "", "", "2026-09-06"),
    ("claude-opus4.8", "ambrosia-tart-high", "Opus 4.8", "Anthropic", "claude", ("claude-opus-4.8", "opus-4.8", "opus4.8"), "", "", "2026-09-06"),
    ("claude-opus4.7", "apricot-sorbet-high", "Opus 4.7", "Anthropic", "claude", ("claude-opus-4.7", "opus-4.7", "opus4.7"), "", "", "2026-09-06"),
    ("claude-opus4.6", "avocado-froyo-medium", "Opus 4.6", "Anthropic", "claude", ("claude-opus-4.6", "opus-4.6", "opus4.6"), "", "", "2026-09-06"),
    ("claude-haiku4.5", "anthropic-haiku-4.5", "Haiku 4.5", "Anthropic", "claude", ("claude-haiku-4.5", "haiku-4.5", "haiku4.5"), "", "", "2026-09-06"),
    # ---- OpenAI ----------------------------------------------------------
    ("gpt-6.1-sol", "omniberry-sundae", "GPT-6.1 Sol", "OpenAI", "gpt", ("gpt-6.1", "gpt6.1-sol", "gpt-6.1-sol-high"), "New", "Newest GPT flagship", "2026-10-17"),
    ("gpt-6-luna", "omodi", "GPT-6 Luna", "OpenAI", "gpt", ("gpt-6-luna-high", "gpt6-luna"), "New", "GPT-6 family, fast tier", "2026-10-17"),
    ("gpt-6-astra", "orlando-quinn", "GPT-6 Astra", "OpenAI", "gpt", ("gpt6-astra",), "", "", "2026-09-06"),
    ("gpt-5.6-sol", "orange-mousse", "GPT-5.6 Sol", "OpenAI", "gpt", ("gpt-5.6", "gpt5.6-sol"), "", "", "2026-09-06"),
    ("gpt-5.6-terra", "orchid-muffin", "GPT-5.6 Terra", "OpenAI", "gpt", ("gpt5.6-terra",), "", "", "2026-09-06"),
    ("gpt-5.6-luna", "olive-jellyroll", "GPT-5.6 Luna", "OpenAI", "gpt", ("gpt5.6-luna",), "", "", "2026-09-06"),
    ("gpt-5.5", "opal-quince-medium", "GPT-5.5", "OpenAI", "gpt", ("gpt5.5",), "Beta", "", "2026-09-06"),
    ("gpt-5.4", "oval-kumquat-medium", "GPT-5.4", "OpenAI", "gpt", ("gpt5.4",), "", "", "2026-09-06"),
    ("gpt-5.4-mini", "oregon-grape-medium", "GPT-5.4 Mini", "OpenAI", "gpt", ("gpt-5.4mini", "gpt5.4-mini"), "New", "Cheap & fast GPT-5.4 tier", "2026-10-17"),
    ("gpt-5.4-nano", "otaheite-apple-medium", "GPT-5.4 Nano", "OpenAI", "gpt", ("gpt-5.4nano", "gpt5.4-nano"), "New", "Smallest GPT-5.4 tier", "2026-10-17"),
    ("gpt-5.2", "oatmeal-cookie", "GPT-5.2", "OpenAI", "gpt", ("gpt5.2",), "New", "Fast GPT-5.2 tier", "2026-10-17"),
    # ---- Google ----------------------------------------------------------
    ("gemini-3.7flash", "grapefruit-zeppole", "Gemini 3.7 Flash", "Google", "gemini", ("gemini-3.7-flash", "gemini-3-7-flash"), "New", "Newest Gemini Flash", "2026-10-17"),
    ("gemini-3.6flash", "vertex-gemini-3.6-flash", "Gemini 3.6 Flash", "Google", "gemini", ("gemini-3.6-flash", "gemini-3-6-flash"), "New", "Fast Gemini with large context", "2026-10-17"),
    ("gemini-3.5flash", "vertex-gemini-3.5-flash", "Gemini 3.5 Flash", "Google", "gemini", ("gemini-3.5-flash", "gemini-3-5-flash"), "", "", "2026-09-06"),
    ("gemini-3.1pro", "galette-medium-thinking", "Gemini 3.1 Pro", "Google", "gemini", ("gemini-3.1-pro", "gemini-3-1-pro"), "", "", "2026-09-06"),
    ("gemini-3flash", "gingerbread", "Gemini 3 Flash", "Google", "gemini", ("gemini-3-flash",), "", "", "2026-09-06"),
    # ---- Moonshot --------------------------------------------------------
    ("kimi-k3", "fireworks-kimi-k3", "Kimi K3", "Moonshot", "kimi", ("kimi-3", "kimi-k-3"), "New", "Kimi K3 agentic coding model", "2026-10-17"),
    # ---- xAI -------------------------------------------------------------
    ("grok-4.6", "soursop-shortcake", "Grok 4.6", "xAI", "grok", ("grok4.6",), "New", "Newest Grok", "2026-10-17"),
    ("grok-4.3", "xigua-mochi-medium", "Grok 4.3", "xAI", "grok", ("grok4.3",), "", "", "2026-09-06"),
    ("spacexai-4.5", "strawberry-whoopiepie", "Grok 4.5", "xAI", "grok", ("grok-4.5", "grok4.5", "spacex-ai-4.5"), "", "", "2026-09-06"),
    ("grok-build0.1", "xinomavro-cake", "Grok Build 0.1", "xAI", "grok", ("grok-build-0.1",), "", "", "2026-09-06"),
    # ---- DeepSeek --------------------------------------------------------
    ("deepseek-v4flash", "baseten-deepseek-v4-flash", "DeepSeek V4 Flash", "DeepSeek", "deepseek", ("deepseek-v4-flash",), "New", "Cheap high-throughput DeepSeek", "2026-10-17"),
    ("deepseek-v4.1flash", "baseten-deepseek-v4.1-flash", "DeepSeek V4.1 Flash", "DeepSeek", "deepseek", ("deepseek-v4.1-flash", "deepseek-v4-1-flash", "deepseek-v41-flash"), "New", "DeepSeek V4.1 fast tier", "2026-10-17"),
    ("deepseek-v4pro", "baseten-deepseek-v4-pro", "DeepSeek V4 Pro", "DeepSeek", "deepseek", ("deepseek-v4-pro",), "", "", "2026-09-06"),
    # ---- Zhipu -----------------------------------------------------------
    ("glm-5.3", "baseten-glm-5.3", "GLM 5.3", "Zhipu", "glm", ("glm5.3",), "New", "Newest GLM", "2026-10-17"),
    ("glm-5.3flash", "baseten-glm-5.3-flash", "GLM 5.3 Flash", "Zhipu", "glm", ("glm-5.3-flash", "glm5.3-flash"), "New", "Fast GLM 5.3", "2026-10-17"),
    ("glm-5.2", "baseten-glm-5.2", "GLM 5.2", "Zhipu", "glm", ("glm5.2",), "", "", "2026-09-06"),
    # ---- Notion ----------------------------------------------------------
    ("auto", "auto", "Auto (Notion picks)", "Notion", "notion", ("default", "notion-auto"), "New", "Let Notion route to the best model", "2026-10-17"),
    ("fable-5.1", "assam-chai", "Fable 5.1", "Notion", "fable", ("fable5.1", "fable-5-1", "claude-fable5.1"), "New", "Notion Fable 5.1", "2026-10-17"),
    ("fable-5", "acai-budino-high", "Fable 5", "Notion", "fable", ("fable5", "claude-fable5", "claude-fable-5"), "", "", "2026-09-06"),
)

MODEL_CATALOG: tuple[ModelSpec, ...] = tuple(ModelSpec(*row) for row in _ROWS)

# ---------------------------------------------------------------------------
# Derived tables (do not hand-edit)
# ---------------------------------------------------------------------------

MODEL_MAP: dict[str, str] = {m.id: m.codename for m in MODEL_CATALOG}
NOTION_MODEL_REVERSE_MAP: dict[str, str] = {
    m.codename: m.id for m in MODEL_CATALOG if m.codename != m.id
}
DISPLAY_NAMES: dict[str, str] = {m.id: m.display for m in MODEL_CATALOG}
MODEL_ICONS: dict[str, str] = {
    m.id: PROVIDER_ICONS.get(m.provider, "\u2022") for m in MODEL_CATALOG
}
MODEL_PROVIDERS: dict[str, str] = {m.id: m.provider for m in MODEL_CATALOG}
MODEL_FAMILIES: dict[str, str] = {m.id: m.family for m in MODEL_CATALOG}

_MODEL_BY_ID: dict[str, ModelSpec] = {m.id: m for m in MODEL_CATALOG}
_CODENAME_TO_ID: dict[str, str] = {
    m.codename: m.id for m in MODEL_CATALOG if m.codename != m.id
}
MODEL_ALIASES: dict[str, str] = {
    alias: m.id for m in MODEL_CATALOG for alias in m.aliases
}

# ---------------------------------------------------------------------------
# Defaults & policy
# ---------------------------------------------------------------------------


def _validated_default() -> str:
    requested = (os.getenv("DEFAULT_MODEL") or "").strip()
    if requested:
        resolved = get_standard_model(requested, fallback="")
        if resolved:
            return resolved
    return "claude-sonnet5.5"


DEFAULT_MODEL: str = _validated_default()

# Models that need Notion's legacy markdown-chat thread type. Only relevant
# for NOTION_RUNTIME=legacy; the new agent_service runtime ignores thread type.
MARKDOWN_CHAT_MODELS: set[str] = {
    "vertex-gemini-3.5-flash",
    "vertex-gemini-3.6-flash",
}

# ---------------------------------------------------------------------------
# Lookup / validation helpers
# ---------------------------------------------------------------------------


def get_standard_model(model_name: str, fallback: str | None = None) -> str:
    """Resolve any accepted spelling to the canonical catalog id.

    Accepts canonical ids, aliases and raw Notion codenames. Unknown values fall
    back to the fallback argument (default: DEFAULT_MODEL).
    """
    name = (model_name or "").strip()
    if name in _MODEL_BY_ID:
        return name
    if name in MODEL_ALIASES:
        return MODEL_ALIASES[name]
    if name in _CODENAME_TO_ID:
        return _CODENAME_TO_ID[name]
    lowered = name.lower()
    if lowered in _MODEL_BY_ID:
        return lowered
    if lowered in MODEL_ALIASES:
        return MODEL_ALIASES[lowered]
    if lowered in _CODENAME_TO_ID:
        return _CODENAME_TO_ID[lowered]
    return DEFAULT_MODEL if fallback is None else fallback


def get_notion_model(model_name: str) -> str:
    """Map a client-supplied model name to the Notion internal codename.

    Raw codenames are passed through unchanged (transcripts store codenames and
    are re-mapped when a request is built). "auto" is passed through so the
    agent_service runtime can let Notion choose.
    """
    name = (model_name or "").strip()
    if name in MODEL_MAP:
        return MODEL_MAP[name]
    if name in NOTION_MODEL_REVERSE_MAP:
        return name
    if name in MODEL_ALIASES:
        return MODEL_MAP[MODEL_ALIASES[name]]
    if name in _MODEL_BY_ID:
        return MODEL_MAP[name]
    lowered = name.lower()
    if lowered in MODEL_MAP:
        return MODEL_MAP[lowered]
    if lowered in MODEL_ALIASES:
        return MODEL_MAP[MODEL_ALIASES[lowered]]
    return MODEL_MAP[DEFAULT_MODEL]


def is_supported_model(model_name: str) -> bool:
    """True when model_name is a canonical id, an alias or a Notion codename."""
    name = (model_name or "").strip()
    if not name:
        return False
    if name in _MODEL_BY_ID or name in MODEL_ALIASES or name in _CODENAME_TO_ID:
        return True
    lowered = name.lower()
    return lowered in _MODEL_BY_ID or lowered in MODEL_ALIASES or lowered in _CODENAME_TO_ID


def is_gemini_model(model_name: str) -> bool:
    """Whether the model belongs to the Gemini family (config-block quirks)."""
    standard = get_standard_model(model_name)
    if MODEL_FAMILIES.get(standard) == "gemini":
        return True
    return standard.startswith("gemini-")


def get_thread_type(model_name: str) -> str:
    """Legacy runtime thread type. agent_service ignores this."""
    notion_model = get_notion_model(get_standard_model(model_name))
    if notion_model in MARKDOWN_CHAT_MODELS:
        return "markdown-chat"
    return "workflow"


def list_available_models() -> list[str]:
    return list(MODEL_MAP.keys())


def get_display_name(model_name: str) -> str:
    standard = get_standard_model(model_name)
    return DISPLAY_NAMES.get(standard, standard)


def get_model_icon(model_name: str) -> str:
    return MODEL_ICONS.get(get_standard_model(model_name), "")


def get_provider(model_name: str) -> str:
    return MODEL_PROVIDERS.get(get_standard_model(model_name), "")


def get_model_spec(model_name: str) -> ModelSpec:
    return _MODEL_BY_ID[get_standard_model(model_name)]


def get_model_info(model_name: str) -> dict[str, Any]:
    """Public metadata for one model (used by /v1/models)."""
    spec = get_model_spec(model_name)
    return {
        "id": spec.id,
        "display_name": spec.display,
        "provider": spec.provider,
        "family": spec.family,
        "icon": PROVIDER_ICONS.get(spec.provider, ""),
        "notion_codename": spec.codename,
        "reasoning": spec.reasoning,
        "aliases": list(spec.aliases),
        "released": spec.released,
        "is_default": spec.id == DEFAULT_MODEL,
    }


def list_model_details() -> list[dict[str, Any]]:
    return [get_model_info(m.id) for m in MODEL_CATALOG]


def get_model_groups() -> list[dict[str, Any]]:
    """Provider-grouped model list, ordered for the Web UI picker."""
    groups: dict[str, list[dict[str, Any]]] = {p: [] for p in PROVIDER_ORDER}
    for spec in MODEL_CATALOG:
        groups.setdefault(spec.provider, []).append(
            {
                "id": spec.id,
                "label": spec.display,
                "icon": PROVIDER_ICONS.get(spec.provider, ""),
                "badge": spec.badge,
                "desc": spec.desc,
            }
        )
    return [
        {"label": provider, "icon": PROVIDER_ICONS.get(provider, ""), "models": groups[provider]}
        for provider in PROVIDER_ORDER
        if groups.get(provider)
    ]


def catalog_stats() -> dict[str, Any]:
    return {
        "models": len(MODEL_CATALOG),
        "providers": len({m.provider for m in MODEL_CATALOG}),
        "default": DEFAULT_MODEL,
        "newest": max(m.released for m in MODEL_CATALOG),
    }
