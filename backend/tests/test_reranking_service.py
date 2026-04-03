import pytest
import numpy as np
from unittest.mock import MagicMock, patch
import app.services.reranking_service as reranking_module
from app.services.reranking_service import rerank_chunks

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def reset_singleton():
    reranking_module._model = None
    yield
    reranking_module._model = None


def _mock_reranker(scores: list[float]) -> MagicMock:
    mock = MagicMock()
    mock.predict.return_value = np.array(scores)
    return mock


async def test_rerank_reorders_by_score():
    chunks = [
        {"id": "a", "content": "low relevance"},
        {"id": "b", "content": "highly relevant answer"},
        {"id": "c", "content": "somewhat related"},
    ]
    with patch("app.services.reranking_service.CrossEncoder", return_value=_mock_reranker([0.1, 0.9, 0.5])):
        result = await rerank_chunks("test query", chunks)
    assert [c["id"] for c in result] == ["b", "c", "a"]


async def test_rerank_passes_correct_pairs_to_predict():
    chunks = [{"id": "x", "content": "first chunk"}, {"id": "y", "content": "second chunk"}]
    mock = _mock_reranker([0.3, 0.7])
    with patch("app.services.reranking_service.CrossEncoder", return_value=mock):
        await rerank_chunks("my query", chunks)
    called_pairs = mock.predict.call_args[0][0]
    assert called_pairs == [["my query", "first chunk"], ["my query", "second chunk"]]


async def test_rerank_empty_list_returns_empty_without_calling_model():
    mock = _mock_reranker([])
    with patch("app.services.reranking_service.CrossEncoder", return_value=mock):
        result = await rerank_chunks("query", [])
    assert result == []
    mock.predict.assert_not_called()


async def test_rerank_predict_failure_returns_original_order():
    chunks = [{"id": "a", "content": "chunk a"}, {"id": "b", "content": "chunk b"}]
    mock = MagicMock()
    mock.predict.side_effect = RuntimeError("model crashed")
    with patch("app.services.reranking_service.CrossEncoder", return_value=mock):
        result = await rerank_chunks("query", chunks)
    assert [c["id"] for c in result] == ["a", "b"]


async def test_rerank_model_load_failure_returns_original_order():
    chunks = [{"id": "z", "content": "some content"}]
    with patch("app.services.reranking_service.CrossEncoder", side_effect=OSError("not found")):
        result = await rerank_chunks("query", chunks)
    assert result == chunks


async def test_singleton_reused_across_calls():
    chunks = [{"id": "a", "content": "text"}]
    with patch("app.services.reranking_service.CrossEncoder", return_value=_mock_reranker([0.5])) as mock_cls:
        await rerank_chunks("query one", chunks)
        await rerank_chunks("query two", chunks)
    mock_cls.assert_called_once()


async def test_singleton_uses_correct_model_name():
    chunks = [{"id": "a", "content": "text"}]
    with patch("app.services.reranking_service.CrossEncoder", return_value=_mock_reranker([0.5])) as mock_cls:
        await rerank_chunks("query", chunks)
    mock_cls.assert_called_once_with("cross-encoder/ms-marco-MiniLM-L-6-v2")


async def test_rerank_does_not_mutate_input_chunks():
    chunks = [{"id": "a", "content": "text a"}, {"id": "b", "content": "text b"}]
    original_ids = [c["id"] for c in chunks]
    with patch("app.services.reranking_service.CrossEncoder", return_value=_mock_reranker([0.2, 0.8])):
        await rerank_chunks("query", chunks)
    assert [c["id"] for c in chunks] == original_ids
