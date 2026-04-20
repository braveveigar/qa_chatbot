import json
import pytest
from unittest.mock import MagicMock, patch
from src.repositories import session_repository


@pytest.fixture(autouse=True)
def init_repository(monkeypatch):
    monkeypatch.setattr(session_repository, "redis_client", MagicMock())

@pytest.fixture
def mock_redis(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(session_repository, "redis_client", mock)
    return mock


def test_save_pushes_json(mock_redis):
    session_repository.save("user", "반품 방법이 뭔가요?")
    mock_redis.rpush.assert_called_once()
    key, payload = mock_redis.rpush.call_args[0]
    assert key == "naver_qa_test"
    data = json.loads(payload)
    assert data == {"role": "user", "message": "반품 방법이 뭔가요?"}


def test_load_returns_parsed_messages(mock_redis):
    messages = [
        json.dumps({"role": "user", "message": "질문"}),
        json.dumps({"role": "assistant", "message": "답변"}),
    ]
    mock_redis.lrange.return_value = messages
    result = session_repository.load(10)
    assert len(result) == 2
    assert result[0] == {"role": "user", "message": "질문"}
    assert result[1] == {"role": "assistant", "message": "답변"}


def test_load_returns_empty_on_redis_error(monkeypatch):
    mock = MagicMock()
    mock.lrange.side_effect = ConnectionError("redis 연결 실패")
    monkeypatch.setattr(session_repository, "redis_client", mock)
    result = session_repository.load(10)
    assert result == []


def test_save_does_not_raise_on_redis_error(monkeypatch):
    mock = MagicMock()
    mock.rpush.side_effect = ConnectionError("redis 연결 실패")
    monkeypatch.setattr(session_repository, "redis_client", mock)
    session_repository.save("user", "질문")  # 예외가 밖으로 나오면 안 됨


def test_clear_deletes_chat_key(mock_redis):
    session_repository.clear()
    mock_redis.delete.assert_called_once_with("naver_qa_test")
