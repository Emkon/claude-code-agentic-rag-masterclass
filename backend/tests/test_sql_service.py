import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.sql_service import _validate_sql, _format_results, query_documents_sql

pytestmark = pytest.mark.asyncio
USER_ID = "123e4567-e89b-12d3-a456-426614174000"


def test_validate_sql_accepts_valid_select():
    sql = f"SELECT filename FROM documents WHERE user_id = '{USER_ID}'"
    assert _validate_sql(sql, USER_ID) == sql

def test_validate_sql_rejects_non_select():
    with pytest.raises(ValueError, match="not a SELECT"):
        _validate_sql(f"UPDATE documents SET status='error' WHERE user_id='{USER_ID}'", USER_ID)

def test_validate_sql_blocks_drop_keyword():
    with pytest.raises(ValueError):
        _validate_sql(f"SELECT 1 WHERE user_id='{USER_ID}' -- DROP TABLE documents", USER_ID)

def test_validate_sql_blocks_insert_keyword():
    with pytest.raises(ValueError, match="Blocked keyword"):
        _validate_sql(f"SELECT INSERT FROM documents WHERE user_id='{USER_ID}'", USER_ID)

def test_validate_sql_requires_user_id_in_sql():
    with pytest.raises(ValueError, match="user_id filter"):
        _validate_sql("SELECT filename FROM documents WHERE status='complete'", USER_ID)

def test_validate_sql_rejects_semicolons():
    with pytest.raises(ValueError, match="Semicolons"):
        _validate_sql(f"SELECT 1; SELECT 2 WHERE user_id='{USER_ID}'", USER_ID)

def test_format_results_empty_returns_no_results():
    assert _format_results([]) == "No results found."

def test_format_results_table_contains_column_names_and_values():
    rows = [{"filename": "report.pdf", "chunk_count": 5}]
    result = _format_results(rows)
    assert "filename" in result and "report.pdf" in result and "5" in result

async def test_query_documents_sql_happy_path():
    rows = [{"filename": "q4.pdf", "chunk_count": 10}]
    with patch("app.services.sql_service.get_traced_client") as mock_client, \
         patch("app.services.sql_service.get_db") as mock_db:
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = f"SELECT filename, chunk_count FROM documents WHERE user_id = '$USER_ID'"
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_db.return_value.rpc.return_value.execute.return_value = MagicMock(data=rows)
        result = await query_documents_sql("files?", USER_ID)
    assert "q4.pdf" in result and "10" in result

async def test_query_documents_sql_llm_failure_returns_message():
    with patch("app.services.sql_service.get_traced_client") as mock_client:
        mock_client.return_value.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        result = await query_documents_sql("question", USER_ID)
    assert result == "Could not generate a SQL query for this question."

async def test_query_documents_sql_validation_failure_returns_message():
    with patch("app.services.sql_service.get_traced_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = f"DELETE FROM documents WHERE user_id='{USER_ID}'"
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_resp)
        result = await query_documents_sql("delete", USER_ID)
    assert "SQL validation failed" in result

async def test_query_documents_sql_rpc_failure_returns_empty():
    with patch("app.services.sql_service.get_traced_client") as mock_client, \
         patch("app.services.sql_service.get_db") as mock_db:
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = f"SELECT filename FROM documents WHERE user_id = '$USER_ID'"
        mock_client.return_value.chat.completions.create = AsyncMock(return_value=mock_resp)
        mock_db.return_value.rpc.return_value.execute.side_effect = Exception("Supabase error")
        result = await query_documents_sql("list", USER_ID)
    assert result == ""
