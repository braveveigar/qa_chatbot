import pytest
from unittest.mock import MagicMock
from src.services import chat_service, llm_service
from src.repositories import session_repository

_SID = "test_session"


@pytest.fixture(autouse=True)
def mock_session(monkeypatch):
    monkeypatch.setattr(session_repository, "save", MagicMock())
    monkeypatch.setattr(session_repository, "load", MagicMock(return_value=[]))


def _consume(generator) -> str:
    return "".join(generator)


def test_streams_agent_answer(monkeypatch):
    monkeypatch.setattr(llm_service, "run_agent", lambda q, h: iter(["배송은 ", "2~3일 ", "소요됩니다."]))
    result = _consume(chat_service.process_chat(_SID, "배송 기간이 얼마나 걸려요?"))
    assert result == "배송은 2~3일 소요됩니다."


def test_saves_user_message_before_agent(monkeypatch):
    monkeypatch.setattr(llm_service, "run_agent", lambda q, h: iter([]))
    _consume(chat_service.process_chat(_SID, "질문"))
    session_repository.save.assert_any_call(_SID, "user", "질문")


def test_saves_assistant_answer_after_stream(monkeypatch):
    monkeypatch.setattr(llm_service, "run_agent", lambda q, h: iter(["안녕", "하세요"]))
    _consume(chat_service.process_chat(_SID, "질문"))
    session_repository.save.assert_any_call(_SID, "assistant", "안녕하세요")


def test_passes_chat_history_to_agent(monkeypatch):
    history = [{"role": "user", "message": "이전 질문"}]
    session_repository.load.return_value = history
    received_history = []

    def mock_agent(q, h):
        received_history.extend(h)
        return iter([])

    monkeypatch.setattr(llm_service, "run_agent", mock_agent)
    _consume(chat_service.process_chat(_SID, "새 질문"))
    assert received_history == history
