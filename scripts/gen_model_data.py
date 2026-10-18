#!/usr/bin/env python3
"""Regenerate the Web UI model tables from app/model_registry.py.

The UI keeps its model data inside two marker blocks:

    frontend/index.html            /* MODEL_DATA_BEGIN */ ... /* MODEL_DATA_END */
    frontend/js/core/constants.js  /* MODEL_DATA_BEGIN */ ... /* MODEL_DATA_END */

Run this script after editing MODEL_CATALOG so the UI never drifts from the
backend registry:

    python scripts/gen_model_data.py          # rewrite both files
    python scripts/gen_model_data.py --check  # exit 1 if the files are stale
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.model_registry import (  # noqa: E402
    DEFAULT_MODEL,
    DISPLAY_NAMES,
    MODEL_ICONS,
    MODEL_PROVIDERS,
    get_model_groups,
)

BEGIN = "/* MODEL_DATA_BEGIN */"
END = "/* MODEL_DATA_END */"

TARGETS = (
    (os.path.join(PROJECT_ROOT, "frontend", "index.html"), "  "),
    (os.path.join(PROJECT_ROOT, "frontend", "js", "core", "constants.js"), "    "),
)


def _js(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def render_lines() -> list[str]:
    groups = get_model_groups()
    ui_groups = []
    flat = []
    for group in groups:
        models = []
        for model in group["models"]:
            row = {"id": model["id"], "label": model["label"]}
            if model.get("icon"):
                row["icon"] = model["icon"]
            if model.get("badge"):
                row["badge"] = model["badge"]
            if model.get("desc"):
                row["desc"] = model["desc"]
            models.append(row)
            flat.append({"id": model["id"], "label": model["label"]})
        ui_groups.append({"label": group["label"], "icon": group["icon"], "models": models})

    return [
        "MODEL_GROUPS:" + _js(ui_groups) + ",",
        "MODELS:" + _js(flat) + ",",
        "DEFAULT_MODEL:" + _js(DEFAULT_MODEL) + ",",
        "MODEL_DISPLAY_NAMES:" + _js(DISPLAY_NAMES) + ",",
        "MODEL_ICONS:" + _js(MODEL_ICONS) + ",",
        "MODEL_PROVIDERS:" + _js(MODEL_PROVIDERS) + ",",
    ]


def render_block(indent: str) -> str:
    body = "\n".join(indent + line for line in render_lines())
    return "\n".join([indent + BEGIN, body, indent + END])


def _pattern() -> re.Pattern:
    return re.compile(r"[ \t]*" + re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate Web UI model tables")
    parser.add_argument("--check", action="store_true", help="fail if the UI tables are stale")
    args = parser.parse_args()

    stale = []
    for path, indent in TARGETS:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        match = _pattern().search(text)
        if not match:
            raise SystemExit(f"[error] markers not found in {path}")
        expected = render_block(indent)
        rel = os.path.relpath(path, PROJECT_ROOT)
        if match.group(0) != expected:
            stale.append(rel)
            if not args.check:
                text = _pattern().sub(lambda _: expected, text, count=1)
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
                print(f"[updated] {rel}")
        elif not args.check:
            print(f"[ok] {rel}")
    if args.check and stale:
        print("[stale] " + ", ".join(stale))
        print("Run: python scripts/gen_model_data.py")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
