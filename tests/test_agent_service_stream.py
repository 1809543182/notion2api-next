"""Parser for Notion's new agent_service transcript protocol."""

import json

import pytest

from app.notion_client import NotionOpusAPI, NotionUpstreamError


def make_client():
    return NotionOpusAPI(
        {
            "token_v2": "token",
            "space_id": "space",
            "user_id": "user",
            "user_email": "user@example.com",
        }
    )


def delta(patches):
    return json.dumps({"type": "agent_service_transcript_delta", "patches": patches})


class FakeResponse:
    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        return iter(self._lines)


def test_provisional_streaming_text_and_thinking():
    lines = [
        json.dumps({"type": "keepalive"}),
        delta([{"op": "session_status", "session": {"status": "running"}}]),
        delta([{"op": "put", "entity": {"kind": "thinking", "id": "t1", "source": "provisional", "content_text": "thinking..."}}]),
        delta([{"op": "put", "entity": {"kind": "assistant_message", "id": "a1", "source": "provisional", "content": [{"type": "text", "text": "Hello "}]}}]),
        delta([{"op": "patch", "id": "a1", "ops": [{"op": "append", "path": "/content/0/text", "value": "world"}]}]),
        delta([{"op": "put", "entity": {"kind": "turn_completed"}}]),
    ]
    events = list(make_client()._parse_agent_stream(FakeResponse(lines), "thread-1"))
    assert {"type": "thinking", "text": "thinking..."} in events
    content = "".join(e["text"] for e in events if e["type"] == "content")
    assert content == "Hello world"
    assert not any(e["type"] == "final_content" for e in events)


def test_committed_message_becomes_final_content():
    lines = [
        delta([{"op": "put", "entity": {"kind": "assistant_message", "id": "a1", "source": "committed", "content": [{"type": "text", "text": "Final answer"}]}}]),
        delta([{"op": "put", "entity": {"kind": "turn_completed"}}]),
    ]
    events = list(make_client()._parse_agent_stream(FakeResponse(lines), "thread-2"))
    finals = [e for e in events if e["type"] == "final_content"]
    assert len(finals) == 1
    assert finals[0]["text"] == "Final answer"
    assert finals[0]["source_type"] == "agent-service-committed"


def test_error_entity_raises():
    lines = [
        delta([{"op": "put", "entity": {"kind": "turn_error", "id": "e1", "message": "quota exceeded"}}]),
    ]
    with pytest.raises(NotionUpstreamError) as excinfo:
        list(make_client()._parse_agent_stream(FakeResponse(lines), "thread-3"))
    assert "quota exceeded" in str(excinfo.value)


def test_stream_without_reply_raises():
    lines = [delta([{"op": "put", "entity": {"kind": "turn_completed"}}])]
    with pytest.raises(NotionUpstreamError):
        list(make_client()._parse_agent_stream(FakeResponse(lines), "thread-4"))


def test_transcript_flattening_keeps_history_and_model():
    client = make_client()
    transcript = [
        {"type": "config", "value": {"type": "workflow", "model": "claude-opus5.5"}},
        {"type": "user", "value": [["What is Notion?"]]},
        {"type": "assistant", "value": [["Notion is a workspace."]]},
        {"type": "user", "value": [["And Notion AI?"]]},
    ]
    prompt, model = client._transcript_to_agent_prompt(transcript)
    assert model == "albuquerque-quinn"
    assert "<conversation_history>" in prompt
    assert "Notion is a workspace." in prompt
    assert prompt.rstrip().endswith("And Notion AI?")


def test_transcript_auto_model_is_not_pinned():
    client = make_client()
    transcript = [
        {"type": "config", "value": {"type": "workflow", "model": "auto"}},
        {"type": "user", "value": [["hi"]]},
    ]
    prompt, model = client._transcript_to_agent_prompt(transcript)
    assert model == "auto"
    assert prompt == "hi"
