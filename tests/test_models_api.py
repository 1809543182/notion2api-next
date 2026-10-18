"""OpenAI-compatible /v1/models surface."""

from app.model_registry import DEFAULT_MODEL, MODEL_CATALOG


def test_list_models(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "list"
    assert body["count"] == len(MODEL_CATALOG) == len(body["data"])
    ids = [item["id"] for item in body["data"]]
    assert body["default_model"] == DEFAULT_MODEL
    assert ids[0] == "claude-sonnet5.5"
    assert "gpt-6.1-sol" in ids

    sample = next(item for item in body["data"] if item["id"] == "claude-opus5.5")
    assert sample["display_name"] == "Opus 5.5"
    assert sample["provider"] == "Anthropic"
    assert sample["notion_codename"] == "albuquerque-quinn"
    assert sample["is_default"] is False


def test_retrieve_model_by_public_id_and_alias(client):
    by_id = client.get("/v1/models/gpt-6.1-sol")
    assert by_id.status_code == 200
    assert by_id.json()["notion_codename"] == "omniberry-sundae"

    by_alias = client.get("/v1/models/opus-5.5")
    assert by_alias.status_code == 200
    assert by_alias.json()["id"] == "claude-opus5.5"

    by_codename = client.get("/v1/models/achira-donut")
    assert by_codename.status_code == 200
    assert by_codename.json()["id"] == "claude-sonnet5.5"


def test_retrieve_unknown_model_returns_404(client):
    response = client.get("/v1/models/not-a-real-model")
    assert response.status_code == 404


def test_health_reports_runtime_and_catalog(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["runtime"] == "agent_service"
    assert body["models"] == len(MODEL_CATALOG)
    assert body["default_model"] == DEFAULT_MODEL


def test_unsupported_model_is_rejected_before_upstream(client):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "definitely-not-a-model", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 400
    assert "Unsupported model" in str(response.json())
