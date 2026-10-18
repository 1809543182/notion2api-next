import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.model_registry import (
    DEFAULT_MODEL,
    get_model_info,
    is_supported_model,
    list_available_models,
    list_model_details,
)

router = APIRouter()


@router.get("/models", tags=["models"])
async def list_models() -> Dict[str, Any]:
    """List every model this proxy can route to, OpenAI-compatible.

    Extra fields (provider / display_name / notion_codename / reasoning /
    is_default / aliases) are additive: OpenAI clients ignore unknown keys,
    while UIs can group models by provider.
    """
    created_at = int(time.time())
    data = []
    for info in list_model_details():
        data.append(
            {
                "id": info["id"],
                "object": "model",
                "created": created_at,
                "owned_by": "notion",
                "permission": [],
                "root": info["id"],
                "parent": None,
                "display_name": info["display_name"],
                "provider": info["provider"],
                "family": info["family"],
                "icon": info["icon"],
                "notion_codename": info["notion_codename"],
                "reasoning": info["reasoning"],
                "aliases": info["aliases"],
                "released": info["released"],
                "is_default": info["is_default"],
            }
        )
    return {
        "object": "list",
        "data": data,
        "default_model": DEFAULT_MODEL,
        "count": len(data),
    }


@router.get("/models/{model_id:path}", tags=["models"])
async def retrieve_model(model_id: str) -> Dict[str, Any]:
    """Retrieve one model (OpenAI-compatible). Aliases and codenames resolve."""
    if not is_supported_model(model_id):
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Model '{model_id}' not found.",
                    "type": "invalid_request_error",
                    "code": "model_not_found",
                    "available": list_available_models(),
                }
            },
        )
    info = get_model_info(model_id)
    return {
        "id": info["id"],
        "object": "model",
        "created": int(time.time()),
        "owned_by": "notion",
        "display_name": info["display_name"],
        "provider": info["provider"],
        "family": info["family"],
        "icon": info["icon"],
        "notion_codename": info["notion_codename"],
        "reasoning": info["reasoning"],
        "aliases": info["aliases"],
        "released": info["released"],
        "is_default": info["is_default"],
    }
