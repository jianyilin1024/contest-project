"""大模型网关测试：SSE 解析 + 端点行为（不产生真实网络请求）。"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.llm.openai_compatible import iter_sse_data, parse_sse_delta

client = TestClient(app)


# ---------------- 纯函数：SSE 解析 ----------------


def test_parse_reasoning_delta() -> None:
    chunk = '{"choices":[{"delta":{"reasoning_content":"先想一下"}}]}'
    delta = parse_sse_delta(chunk)
    assert delta is not None
    assert delta.kind == "reasoning"
    assert delta.text == "先想一下"


def test_parse_content_delta() -> None:
    chunk = '{"choices":[{"delta":{"content":"答案是 42"}}]}'
    delta = parse_sse_delta(chunk)
    assert delta is not None
    assert delta.kind == "content"
    assert delta.text == "答案是 42"


def test_parse_skips_done_and_noise() -> None:
    assert parse_sse_delta("[DONE]") is None
    assert parse_sse_delta("") is None
    assert parse_sse_delta("not-json") is None
    assert parse_sse_delta('{"choices":[{"delta":{}}]}') is None


def test_iter_sse_data_filters_non_data_lines() -> None:
    lines = ["event: ping", "data: a", "", ": comment", "data: b"]
    assert list(iter_sse_data(lines)) == ["a", "b"]


# ---------------- 端点行为 ----------------


@pytest.fixture
def no_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    yield
    monkeypatch.undo()


def test_chat_without_key_returns_503(no_api_key) -> None:
    response = client.post("/api/v1/llm/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 503
    assert "LLM_API_KEY" in response.json()["detail"]


def test_health_without_key_reports_error(no_api_key) -> None:
    response = client.get("/api/v1/llm/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["detail"]


def test_chat_rejects_empty_messages() -> None:
    response = client.post("/api/v1/llm/chat", json={"messages": []})
    assert response.status_code == 422


def test_stream_without_key_emits_error_event(no_api_key) -> None:
    response = client.post(
        "/api/v1/llm/chat/stream",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert response.status_code == 200
    assert '"type": "error"' in response.text


def test_openapi_exposes_llm_routes() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/llm/health" in paths
    assert "/api/v1/llm/chat" in paths
    assert "/api/v1/llm/chat/stream" in paths
