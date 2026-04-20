import pytest
from unittest.mock import MagicMock, patch
from src.repositories import vector_repository


@pytest.fixture(autouse=True)
def reset_client():
    original = vector_repository._client
    yield
    vector_repository._client = original


def test_is_connected_false_before_init():
    vector_repository._client = None
    assert vector_repository.is_connected() is False


def test_is_connected_true_after_init():
    vector_repository._client = MagicMock()
    assert vector_repository.is_connected() is True


def test_search_returns_none_when_not_connected():
    vector_repository._client = None
    result = vector_repository.search([0.1] * 1536)
    assert result is None


def test_search_calls_milvus(monkeypatch):
    mock_client = MagicMock()
    mock_client.search.return_value = [[{"entity": {"answer": "테스트 답변"}}]]
    vector_repository._client = mock_client

    result = vector_repository.search([0.1] * 1536, limit=2)
    mock_client.search.assert_called_once()
    assert result is not None


def test_init_sets_client_on_success(monkeypatch):
    mock_instance = MagicMock()
    with patch("src.repositories.vector_repository.MilvusClient", return_value=mock_instance):
        vector_repository._client = None
        vector_repository.init()
        assert vector_repository._client is mock_instance


def test_init_keeps_none_on_failure(monkeypatch):
    with patch("src.repositories.vector_repository.MilvusClient", side_effect=Exception("DB 없음")):
        vector_repository._client = None
        vector_repository.init()
        assert vector_repository._client is None
