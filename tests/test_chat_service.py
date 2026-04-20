import pytest
import src.utils as utils_module
from unittest.mock import MagicMock, patch
from src.services import chat_service
from src.repositories import session_repository, vector_repository
from src.services import llm_service

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(utils_module.time, "sleep", lambda _: None)


@pytest.fixture(autouse=True)
def mock_session(monkeypatch):
    monkeypatch.setattr(session_repository, "save", MagicMock())
    monkeypatch.setattr(session_repository, "load", MagicMock(return_value=[]))


def _consume(generator) -> str:
    return "".join(generator)


def test_irrelevant_question_returns_fixed_message(monkeypatch):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 200, "result": "없음"})
    result = _consume(chat_service.process_chat("오늘 날씨 어때?"))
    assert "스마트 스토어" in result


def test_relevance_classify_failure_returns_retry_message(monkeypatch):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 424, "result": "분류 실패"})
    result = _consume(chat_service.process_chat("???"))
    assert "다시" in result


def test_api_error_returns_error_message(monkeypatch):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 503, "result": "API 오류"})
    result = _consume(chat_service.process_chat("질문"))
    assert "API 오류" in result


def test_embed_failure_returns_error_message(monkeypatch):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 200, "result": "있음"})
    monkeypatch.setattr(llm_service, "embed", MagicMock(side_effect=Exception("임베딩 실패")))
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    result = _consume(chat_service.process_chat("반품 방법"))
    assert "관리자" in result


def test_milvus_not_connected_returns_error_message(monkeypatch):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 200, "result": "있음"})
    monkeypatch.setattr(llm_service, "embed", MagicMock(return_value=[0.1] * 1536))
    monkeypatch.setattr(vector_repository, "is_connected", lambda: False)
    result = _consume(chat_service.process_chat("반품 방법"))
    assert "DB 연결" in result


def test_no_search_result_returns_not_found_message(monkeypatch):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 200, "result": "있음"})
    monkeypatch.setattr(llm_service, "embed", MagicMock(return_value=[0.1] * 1536))
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    monkeypatch.setattr(vector_repository, "search", lambda v, limit: [[]])
    result = _consume(chat_service.process_chat("반품 방법"))
    assert "찾을 수 없습니다" in result


def test_successful_chat_streams_answer(monkeypatch):
    monkeypatch.setattr(llm_service, "check_relevance", lambda q, h: {"status": 200, "result": "있음"})
    monkeypatch.setattr(llm_service, "embed", MagicMock(return_value=[0.1] * 1536))
    monkeypatch.setattr(vector_repository, "is_connected", lambda: True)
    mock_hit = MagicMock()
    mock_hit.entity.get.return_value = "배송은 2~3일 소요됩니다."
    monkeypatch.setattr(vector_repository, "search", lambda v, limit: [[mock_hit]])
    monkeypatch.setattr(llm_service, "generate_answer", lambda q, db, h: iter(["배송은 ", "2~3일 ", "소요됩니다."]))
    result = _consume(chat_service.process_chat("배송 기간이 얼마나 걸려요?"))
    assert "배송" in result
