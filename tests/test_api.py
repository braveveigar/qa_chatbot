import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from src.repositories import session_repository, vector_repository
from src.services import llm_service
from src.dependencies import verify_api_key


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(session_repository, "redis_client", MagicMock())
    monkeypatch.setattr(session_repository, "save", MagicMock())
    monkeypatch.setattr(session_repository, "load", MagicMock(return_value=[]))
    monkeypatch.setattr(session_repository, "clear", MagicMock())
    monkeypatch.setattr(session_repository, "init", MagicMock())
    monkeypatch.setattr(vector_repository, "init", MagicMock())
    monkeypatch.setattr(llm_service, "init", MagicMock())

    from src.main import app
    app.dependency_overrides[verify_api_key] = lambda: None
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ── /health ──────────────────────────────────────────────────────────────────

def test_health_redis_ok_milvus_ok(monkeypatch, client):
    mock_r = MagicMock()
    monkeypatch.setattr(session_repository, "redis_client", mock_r)
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_redis_down(monkeypatch, client):
    mock_r = MagicMock()
    mock_r.ping.side_effect = ConnectionError()
    monkeypatch.setattr(session_repository, "redis_client", mock_r)
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    res = client.get("/health")
    assert res.json()["redis"] == "error"
    assert res.json()["status"] == "degraded"


def test_health_milvus_down(monkeypatch, client):
    monkeypatch.setattr(session_repository, "redis_client", MagicMock())
    monkeypatch.setattr(vector_repository, "is_connected", lambda: False)
    res = client.get("/health")
    assert res.json()["milvus"] == "error"
    assert res.json()["status"] == "degraded"


# ── /session/reset ────────────────────────────────────────────────────────────

def test_session_reset(client):
    res = client.post("/session/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── /chat ─────────────────────────────────────────────────────────────────────

def test_chat_missing_question_field(client):
    res = client.post("/chat", json={})
    assert res.status_code == 422


def test_chat_streams_agent_answer(monkeypatch, client):
    monkeypatch.setattr(llm_service, "run_agent", lambda q, h: iter(["반품은 ", "7일 이내 ", "가능합니다."]))
    res = client.post("/chat", json={"question": "반품 방법 알려줘"})
    assert res.status_code == 200
    assert "반품" in res.text


def test_chat_irrelevant_returns_agent_response(monkeypatch, client):
    monkeypatch.setattr(llm_service, "run_agent", lambda q, h: iter(["스마트스토어 관련 질문을 부탁드립니다."]))
    res = client.post("/chat", json={"question": "오늘 날씨"})
    assert res.status_code == 200
    assert "스마트스토어" in res.text


# ── API Key 인증 ───────────────────────────────────────────────────────────────

def test_chat_without_api_key_returns_401(monkeypatch):
    monkeypatch.setattr(session_repository, "init", MagicMock())
    monkeypatch.setattr(vector_repository, "init", MagicMock())
    monkeypatch.setattr(llm_service, "init", MagicMock())

    from src.main import app
    res = TestClient(app, raise_server_exceptions=False).post("/chat", json={"question": "반품"})
    assert res.status_code == 403  # APIKeyHeader: 헤더 누락 시 403
