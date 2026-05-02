import pytest
from unittest.mock import MagicMock
from openai import APITimeoutError, APIError
from src.services import llm_service


@pytest.fixture(autouse=True)
def reset_client():
    original = llm_service._client
    yield
    llm_service._client = original


# ── _load_workflow ────────────────────────────────────────────────────────────

def test_load_workflow_returns_content(tmp_path, monkeypatch):
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    (wf_dir / "배송.md").write_text("# 배송 워크플로우\n테스트 내용", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert "배송 워크플로우" in llm_service._load_workflow("배송")


def test_load_workflow_falls_back_to_기타(tmp_path, monkeypatch):
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    (wf_dir / "기타.md").write_text("# 기타 워크플로우", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert "기타" in llm_service._load_workflow("존재하지않는카테고리")


# ── _classify_category ────────────────────────────────────────────────────────

def test_classify_category_returns_category():
    mock_client = MagicMock()
    mock_out = MagicMock()
    mock_out.type = "function_call"
    mock_out.name = "load_workflow"
    mock_out.arguments = '{"category": "배송"}'
    mock_client.responses.create.return_value.output = [mock_out]
    llm_service._client = mock_client

    result = llm_service._classify_category("배송이 언제 오나요?", [])
    assert result == "배송"


def test_classify_category_falls_back_to_기타_on_no_tool_call():
    mock_client = MagicMock()
    mock_client.responses.create.return_value.output = []
    llm_service._client = mock_client

    result = llm_service._classify_category("아무 질문", [])
    assert result == "기타"


# ── _execute_search ───────────────────────────────────────────────────────────

def test_execute_search_returns_answers(monkeypatch):
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1] * 1536)]
    llm_service._client = mock_client

    mock_hit = MagicMock()
    mock_hit.entity.get.return_value = "배송은 2~3일 소요됩니다."
    monkeypatch.setattr("src.repositories.vector_repository.search", lambda v, limit: [[mock_hit]])

    assert "배송" in llm_service._execute_search("배송 기간")


# ── _classify_category 에러 처리 ─────────────────────────────────────────────

def test_classify_category_falls_back_on_timeout():
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = APITimeoutError(request=MagicMock())
    llm_service._client = mock_client

    result = llm_service._classify_category("질문", [])
    assert result == "기타"


def test_classify_category_falls_back_on_api_error():
    mock_client = MagicMock()
    mock_client.responses.create.side_effect = APIError(
        message="서버 오류", request=MagicMock(), body=None
    )
    llm_service._client = mock_client

    result = llm_service._classify_category("질문", [])
    assert result == "기타"


def test_classify_category_falls_back_on_invalid_json():
    mock_client = MagicMock()
    mock_out = MagicMock()
    mock_out.type = "function_call"
    mock_out.name = "load_workflow"
    mock_out.arguments = "invalid json {"
    mock_client.responses.create.return_value.output = [mock_out]
    llm_service._client = mock_client

    result = llm_service._classify_category("질문", [])
    assert result == "기타"


# ── _execute_search 에러 처리 ─────────────────────────────────────────────────

def test_execute_search_falls_back_on_timeout():
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = APITimeoutError(request=MagicMock())
    llm_service._client = mock_client

    result = llm_service._execute_search("배송 기간")
    assert result == "관련 정보를 찾을 수 없습니다."


# ── session_repository.clear 에러 처리 ───────────────────────────────────────

# ── ask_clarification ─────────────────────────────────────────────────────────

def test_ask_clarification_exception():
    with pytest.raises(llm_service.ClarificationRequested) as exc_info:
        raise llm_service.ClarificationRequested("주문번호를 알려주세요.")
    assert exc_info.value.question == "주문번호를 알려주세요."
