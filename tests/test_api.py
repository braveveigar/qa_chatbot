import pytest
import src.utils as utils_module
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from src.repositories import session_repository, vector_repository
from src.services import llm_service

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(utils_module.time, "sleep", lambda _: None)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(session_repository, "save", MagicMock())
    monkeypatch.setattr(session_repository, "load", MagicMock(return_value=[]))
    monkeypatch.setattr(session_repository, "clear", MagicMock())
    monkeypatch.setattr(vector_repository, "init", MagicMock())
    monkeypatch.setattr(llm_service, "init", MagicMock())

    from src.server import app
    return TestClient(app, raise_server_exceptions=False)


# ── /health ──────────────────────────────────────────────────────────────────

def test_health_redis_ok_milvus_ok(monkeypatch, client):
    mock_r = MagicMock()
    monkeypatch.setattr(session_repository, "_get_client", lambda: mock_r)
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_redis_down(monkeypatch, client):
    def bad(): raise ConnectionError()
    monkeypatch.setattr(session_repository, "_get_client", bad)
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    res = client.get("/health")
    assert res.json()["redis"] == "error"
    assert res.json()["status"] == "degraded"


def test_health_milvus_down(monkeypatch, client):
    monkeypatch.setattr(session_repository, "_get_client", lambda: MagicMock())
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

def test_chat_irrelevant_question(monkeypatch, client):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 200, "result": "없음"})
    res = client.post("/chat", json={"question": "오늘 날씨"})
    assert res.status_code == 200
    assert "스마트 스토어" in res.text


def test_chat_missing_question_field(client):
    res = client.post("/chat", json={})
    assert res.status_code == 422


def test_chat_successful_answer(monkeypatch, client):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 200, "result": "있음"})
    monkeypatch.setattr(llm_service, "embed", MagicMock(return_value=[0.1] * 1536))
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    mock_hit = MagicMock()
    mock_hit.entity.get.return_value = "반품은 7일 이내 가능합니다."
    monkeypatch.setattr(vector_repository, "search", lambda v, limit: [[mock_hit]])
    monkeypatch.setattr(llm_service, "generate_answer", lambda q, db, h: iter(["반품은 ", "7일 이내 ", "가능합니다."]))
    res = client.post("/chat", json={"question": "반품 방법 알려줘"})
    assert res.status_code == 200
    assert "반품" in res.text
