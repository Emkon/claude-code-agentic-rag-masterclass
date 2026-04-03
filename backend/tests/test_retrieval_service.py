import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.retrieval_service import _reciprocal_rank_fusion, retrieve_context


# Pure function tests — no mocking needed
def test_rrf_chunk_in_both_lists_ranks_highest():
    vector = [{"id": "a", "content": "v1"}, {"id": "b", "content": "v2"}]
    keyword = [{"id": "b", "content": "v2"}, {"id": "c", "content": "k1"}]
    result = _reciprocal_rank_fusion(vector, keyword)
    assert result[0]["id"] == "b"
    assert {r["id"] for r in result} == {"a", "b", "c"}


def test_rrf_empty_keyword_preserves_vector_order():
    vector = [{"id": "x", "content": "one"}, {"id": "y", "content": "two"}]
    result = _reciprocal_rank_fusion(vector, [])
    assert [r["id"] for r in result] == ["x", "y"]


def test_rrf_empty_vector_preserves_keyword_order():
    keyword = [{"id": "p", "content": "one"}, {"id": "q", "content": "two"}]
    result = _reciprocal_rank_fusion([], keyword)
    assert [r["id"] for r in result] == ["p", "q"]


def test_rrf_both_empty_returns_empty():
    assert _reciprocal_rank_fusion([], []) == []


def test_rrf_deduplicates_same_chunk_id():
    chunk = {"id": "dup", "content": "text"}
    result = _reciprocal_rank_fusion([chunk], [chunk])
    assert len(result) == 1
    assert result[0]["id"] == "dup"


def test_rrf_annotates_rrf_score_on_output():
    vector = [{"id": "a", "content": "text"}]
    result = _reciprocal_rank_fusion(vector, [])
    assert "rrf_score" in result[0]
    assert isinstance(result[0]["rrf_score"], float)


# Integration tests — mock I/O boundaries
@pytest.mark.asyncio
async def test_retrieve_context_returns_empty_when_no_chunks():
    with patch("app.services.retrieval_service.get_db") as mock_db_fn, \
         patch("app.services.retrieval_service.get_query_embedding") as mock_embed, \
         patch("app.services.retrieval_service.extract_query_filters") as mock_filters:
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        mock_db_fn.return_value = db
        result = await retrieve_context("user-1", "test query")
    assert result == []
    mock_embed.assert_not_called()
    mock_filters.assert_not_called()


@pytest.mark.asyncio
async def test_retrieve_context_keyword_failure_falls_back_to_vector():
    vector_chunk = {"id": "v1", "content": "vector result", "document_id": "d1", "similarity": 0.8}

    with patch("app.services.retrieval_service.get_db") as mock_db_fn, \
         patch("app.services.retrieval_service.get_query_embedding", new_callable=AsyncMock) as mock_embed, \
         patch("app.services.retrieval_service.extract_query_filters", new_callable=AsyncMock) as mock_filters, \
         patch("app.services.retrieval_service.rerank_chunks", new_callable=AsyncMock) as mock_rerank:

        mock_embed.return_value = [0.1] * 384
        mock_filters.return_value = MagicMock(entity=None, year=None, quarter=None, document_type=None)
        mock_rerank.side_effect = lambda q, chunks: chunks

        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": "c1"}])

        def rpc_side(rpc_name, params):
            m = MagicMock()
            if rpc_name == "match_chunks":
                m.execute.return_value = MagicMock(data=[vector_chunk])
            else:
                m.execute.side_effect = Exception("keyword RPC down")
            return m

        db.rpc.side_effect = rpc_side
        mock_db_fn.return_value = db

        result = await retrieve_context("user-1", "revenue growth")

    assert any(r["id"] == "v1" for r in result)
