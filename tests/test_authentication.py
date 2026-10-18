import importlib
import json

import pytest


@pytest.mark.parametrize('header', [None, 'Basic release-test', 'Bearer wrong', 'Bearer release-test extra', 'Bearer ', 'Bearer 非法'])
def test_reject_invalid_bearer(client, monkeypatch, header):
    import app.server as server
    monkeypatch.setattr(server, 'API_KEY', 'release-test')
    # HTTP header bytes are latin-1 on the wire; malformed UTF-8 must still reject.
    headers = {} if header is None else {'Authorization': header.encode('utf-8')}
    assert client.get('/v1/models', headers=headers).status_code == 401


def test_correct_key_and_public_health(client, monkeypatch):
    import app.server as server
    monkeypatch.setattr(server, 'API_KEY', 'release-test')
    response = client.get('/v1/models', headers={'Authorization': 'Bearer release-test'})
    assert response.status_code == 200
    assert 'token_v2' not in response.text
    assert client.get('/health').status_code == 200


def test_empty_key_is_optional(client, monkeypatch):
    import app.server as server
    monkeypatch.setattr(server, 'API_KEY', '')
    assert client.get('/v1/models').status_code == 200


def test_upstream_error_body_stays_private():
    from app.api.chat import _upstream_error_response
    from app.notion_client import NotionUpstreamError
    error = NotionUpstreamError('failure', status_code=401, response_excerpt='private-upstream-body')
    response = _upstream_error_response(error)
    assert response.status_code == 503
    assert b'private-upstream-body' not in response.body


def test_upstream_cookie_is_separate_from_local_api_key():
    from app.notion_client import NotionOpusAPI
    account = {'token_v2': 'test-token', 'user_id': 'test-user', 'space_id': 'test-space'}
    instance = NotionOpusAPI(account)
    headers = instance._agent_headers()
    assert 'token_v2=test-token' in headers['cookie']
    assert 'notion_user_id=test-user' in headers['cookie']
    assert headers['x-notion-space-id'] == 'test-space'
    assert 'Authorization' not in headers


def test_login_account_save_and_env_keep_existing_settings(tmp_path, monkeypatch):
    login = importlib.import_module('login')
    account_file = tmp_path / 'accounts.json'
    env_file = tmp_path / '.env'
    env_file.write_text('APP_MODE=standard\nAPI_KEY=test-local-key\n', encoding='utf-8')
    monkeypatch.setattr(login, 'ACCOUNTS_FILE', account_file)
    monkeypatch.setattr(login, 'ENV_FILE', env_file)
    account = login.NotionAccount('test', 'test-token', 'test-space', 'test-user', '', 'Test', 'test@example.com', {})
    merged = login._write_accounts(account)
    login._sync_env_file(merged)
    assert json.loads(account_file.read_text()) == merged
    assert 'API_KEY=test-local-key' in env_file.read_text()
    assert 'NOTION_ACCOUNTS=' in env_file.read_text()
