import json
import os

# The FastAPI app loads accounts at import time. Provide a dummy account before
# any app module is imported by a test module.
os.environ["NOTION_ACCOUNTS"] = json.dumps(
    [
        {
            "profile_name": "test",
            "token_v2": "test-token",
            "space_id": "test-space",
            "user_id": "test-user",
            "user_email": "test@example.com",
        }
    ]
)
os.environ["APP_MODE"] = "standard"
os.environ["DISABLE_RATE_LIMIT"] = "true"
os.environ.pop("API_KEY", None)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.server import app

    with TestClient(app) as test_client:
        yield test_client
