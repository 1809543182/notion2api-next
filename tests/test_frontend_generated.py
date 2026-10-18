"""The generated Web UI tables must stay in sync with the registry."""

from pathlib import Path

from app.model_registry import DEFAULT_MODEL, MODEL_CATALOG

ROOT = Path(__file__).resolve().parents[1]


def _ui_sources():
    return {
        "index.html": (ROOT / "frontend" / "index.html").read_text(encoding="utf-8"),
        "constants.js": (ROOT / "frontend" / "js" / "core" / "constants.js").read_text(encoding="utf-8"),
    }


def test_ui_contains_every_model_id_and_display_name():
    for name, text in _ui_sources().items():
        assert "/* MODEL_DATA_BEGIN */" in text, name
        assert "/* MODEL_DATA_END */" in text, name
        for spec in MODEL_CATALOG:
            assert spec.id in text, f"{spec.id} missing from {name}"
            assert spec.display in text, f"{spec.display} missing from {name}"


def test_ui_default_model_matches_registry():
    for name, text in _ui_sources().items():
        assert f'DEFAULT_MODEL:"{DEFAULT_MODEL}"' in text, name


def test_generated_blocks_are_identical_in_both_files():
    html = _ui_sources()["index.html"]
    js = _ui_sources()["constants.js"]
    for key in ("MODEL_GROUPS:", "MODELS:", "MODEL_DISPLAY_NAMES:", "MODEL_PROVIDERS:"):
        html_line = next(line.strip() for line in html.splitlines() if line.strip().startswith(key))
        js_line = next(line.strip() for line in js.splitlines() if line.strip().startswith(key))
        assert html_line == js_line, key
