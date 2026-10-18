"""Parsing of the undocumented getAvailableModels payload."""

from app.model_registry import NOTION_MODEL_REVERSE_MAP
from app.model_sync import diff_against_snapshot, extract_available_models


def test_extract_from_live_schema():
    # Real shape returned by POST /api/v3/getAvailableModels (2026-10-17).
    payload = {
        "models": [
            {
                "model": "orange-mousse",
                "modelMessage": "GPT-5.6 Sol",
                "modelFamily": "openai",
                "modelProvider": "openai",
                "displayGroup": "intelligent",
            },
            {
                "model": "achira-donut",
                "modelMessage": "Sonnet 5.5",
                "modelFamily": "anthropic",
                "modelProvider": "anthropic",
                "displayGroup": "intelligent",
            },
        ],
        "restrictedAccessModelsInPickerConfig": [
            {"codename": "assam-chai", "modelMessage": "Fable 5.1", "modelFamily": "anthropic"}
        ],
    }
    found = extract_available_models(payload)
    codenames = [item["codename"] for item in found]
    assert codenames == ["achira-donut", "assam-chai", "orange-mousse"]
    by_code = {item["codename"]: item for item in found}
    assert by_code["achira-donut"]["display"] == "Sonnet 5.5"
    assert by_code["orange-mousse"]["provider"] == "openai"
    assert by_code["orange-mousse"]["tier"] == "intelligent"


def test_extract_from_nested_container_and_plain_strings():
    payload = {
        "data": {
            "availableModels": [
                "grapefruit-zeppole",
                {"codename": "omodi", "display_name": "GPT-6 Luna"},
            ]
        }
    }
    found = extract_available_models(payload)
    assert {item["codename"] for item in found} == {"grapefruit-zeppole", "omodi"}


def test_ignores_non_model_strings():
    payload = {"data": {"graph": ["application/json", "api/v3/getAvailableModels", "utf-8"]}}
    assert extract_available_models(payload) == []


def test_diff_against_snapshot_reports_missing():
    discovered = [
        {"codename": "orange-mousse", "display": "", "provider": ""},
        {"codename": "brand-new-model", "display": "Brand New", "provider": "OpenAI"},
    ]
    diff = diff_against_snapshot(discovered, NOTION_MODEL_REVERSE_MAP)
    assert [item["codename"] for item in diff["known"]] == ["orange-mousse"]
    assert diff["known"][0]["model_id"] == "gpt-5.6-sol"
    assert [item["codename"] for item in diff["missing"]] == ["brand-new-model"]
