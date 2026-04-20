import pytest
from unittest.mock import patch, MagicMock
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
    result = llm_service._load_workflow("배송")
    assert "배송 워크플로우" in result


def test_load_workflow_falls_back_to_기타(tmp_path, monkeypatch):
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    (wf_dir / "기타.md").write_text("# 기타 워크플로우", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = llm_service._load_workflow("존재하지않는카테고리")
    assert "기타" in result


# ── _execute_tool ─────────────────────────────────────────────────────────────

def test_execute_tool_load_workflow(tmp_path, monkeypatch):
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    (wf_dir / "반품_교환.md").write_text("# 반품 워크플로우", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = llm_service._execute_tool("load_workflow", '{"category": "반품_교환"}', "반품하고 싶어요")
    assert "반품 워크플로우" in result


def test_execute_tool_search_qa(monkeypatch):
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value.data = [MagicMock(embedding=[0.1] * 1536)]
    llm_service._client = mock_client

    mock_hit = MagicMock()
    mock_hit.entity.get.return_value = "배송은 2~3일 소요됩니다."
    monkeypatch.setattr("src.repositories.vector_repository.search", lambda v, limit: [[mock_hit]])

    result = llm_service._execute_tool("search_qa", '{"query": "배송 기간"}', "배송 기간이 얼마나 걸려요?")
    assert "배송" in result


def test_execute_tool_unknown_returns_message():
    result = llm_service._execute_tool("unknown_tool", '{}', "질문")
    assert "알 수 없는" in result
