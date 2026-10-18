"""Catalog integrity + regression pins for the 2026-10 model wave."""

import pytest

from app import model_registry as reg


# The 11 models announced/added between Notion 3.7 and 3.8 (+ the Auto alias).
NEW_MODELS_2026_10 = {
    "gpt-6.1-sol": "omniberry-sundae",
    "gpt-6-luna": "omodi",
    "claude-sonnet5.5": "achira-donut",
    "claude-opus5.5": "albuquerque-quinn",
    "claude-haiku5.5": "amla-jam",
    "gemini-3.6flash": "vertex-gemini-3.6-flash",
    "gemini-3.7flash": "grapefruit-zeppole",
    "gpt-5.4-mini": "oregon-grape-medium",
    "gpt-5.4-nano": "otaheite-apple-medium",
    "deepseek-v4flash": "baseten-deepseek-v4-flash",
    "kimi-k3": "fireworks-kimi-k3",
}


def test_catalog_is_consistent():
    ids = [m.id for m in reg.MODEL_CATALOG]
    codenames = [m.codename for m in reg.MODEL_CATALOG]
    assert len(ids) == len(set(ids))
    assert len(codenames) == len(set(codenames))
    assert len(reg.MODEL_CATALOG) >= 34
    assert all(m.display and m.provider and m.family for m in reg.MODEL_CATALOG)


def test_derived_tables_cover_catalog():
    for spec in reg.MODEL_CATALOG:
        assert reg.MODEL_MAP[spec.id] == spec.codename
        assert reg.DISPLAY_NAMES[spec.id] == spec.display
        assert reg.MODEL_ICONS[spec.id]
        assert reg.MODEL_PROVIDERS[spec.id] == spec.provider
    assert set(reg.MODEL_MAP) == {m.id for m in reg.MODEL_CATALOG}


def test_aliases_do_not_shadow_canonical_ids():
    for alias, target in reg.MODEL_ALIASES.items():
        assert alias not in reg.MODEL_MAP, f"alias {alias} collides with a model id"
        assert target in reg.MODEL_MAP


def test_default_model_is_routable():
    assert reg.DEFAULT_MODEL in reg.MODEL_MAP


@pytest.mark.parametrize("model_id,codename", sorted(NEW_MODELS_2026_10.items()))
def test_new_models_pinned(model_id, codename):
    assert model_id in reg.MODEL_MAP
    assert reg.get_notion_model(model_id) == codename
    assert reg.is_supported_model(model_id)
    assert reg.is_supported_model(codename)
    assert reg.get_standard_model(codename) == model_id


def test_auto_model_passes_through():
    assert reg.get_notion_model("auto") == "auto"
    assert reg.get_standard_model("auto") == "auto"
    assert reg.is_supported_model("auto")


def test_alias_and_case_resolution():
    assert reg.get_standard_model("claude-opus-5.5") == "claude-opus5.5"
    assert reg.get_standard_model("OPUS-5.5") == "claude-opus5.5"
    assert reg.get_notion_model("sonnet5.5") == "achira-donut"
    assert reg.get_notion_model("agave-flan") == "agave-flan"


def test_unknown_model_falls_back_to_default():
    assert reg.get_standard_model("does-not-exist") == reg.DEFAULT_MODEL
    assert reg.get_notion_model("does-not-exist") == reg.MODEL_MAP[reg.DEFAULT_MODEL]
    assert not reg.is_supported_model("does-not-exist")
    assert not reg.is_supported_model("")


def test_gemini_and_thread_type_helpers():
    assert reg.is_gemini_model("gemini-3.7flash")
    assert reg.is_gemini_model("vertex-gemini-3.6-flash")
    assert not reg.is_gemini_model("claude-opus5.5")
    assert reg.get_thread_type("gemini-3.6flash") == "markdown-chat"
    assert reg.get_thread_type("claude-opus5.5") == "workflow"


def test_groups_cover_every_model_once():
    groups = reg.get_model_groups()
    grouped = [model["id"] for group in groups for model in group["models"]]
    assert len(grouped) == len(reg.MODEL_CATALOG)
    assert set(grouped) == set(reg.MODEL_MAP)
    assert [g["label"] for g in groups] == list(reg.PROVIDER_ORDER)


def test_public_info_shape():
    info = reg.get_model_info("achira-donut")
    assert info["id"] == "claude-sonnet5.5"
    assert info["notion_codename"] == "achira-donut"
    assert info["provider"] == "Anthropic"
    assert "claude-sonnet-5.5" in info["aliases"]
    assert reg.catalog_stats()["models"] == len(reg.MODEL_CATALOG)
