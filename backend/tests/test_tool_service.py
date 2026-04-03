import pytest
from unittest.mock import AsyncMock, patch
from app.services.tool_service import execute_tool_call, TOOL_DEFINITIONS

pytestmark = pytest.mark.asyncio
USER_ID = "123e4567-e89b-12d3-a456-426614174000"


def test_tool_definitions_contain_expected_names():
    names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    assert "query_documents_sql" in names
    assert "search_web" in names
    assert "run_subagent" in names

def test_tool_definitions_have_strict_schema():
    for tool in TOOL_DEFINITIONS:
        params = tool["function"]["parameters"]
        assert params.get("additionalProperties") is False
        assert "required" in params

async def test_execute_routes_to_sql_service():
    with patch("app.services.tool_service.query_documents_sql", new_callable=AsyncMock) as mock_sql:
        mock_sql.return_value = "filename | chunk_count\nreport.pdf | 10"
        result = await execute_tool_call("query_documents_sql", {"question": "count files"}, USER_ID)
    mock_sql.assert_called_once_with("count files", USER_ID)
    assert "report.pdf" in result

async def test_execute_routes_to_web_search():
    with patch("app.services.tool_service.search_web", new_callable=AsyncMock) as mock_web:
        mock_web.return_value = "**AI News**\ndesc\nhttps://news.com"
        result = await execute_tool_call("search_web", {"query": "AI news"}, USER_ID)
    mock_web.assert_called_once_with("AI news")
    assert "AI News" in result

async def test_execute_unknown_tool_returns_error_string():
    result = await execute_tool_call("nonexistent", {}, USER_ID)
    assert "Unknown tool" in result

async def test_execute_never_raises_on_service_failure():
    with patch("app.services.tool_service.query_documents_sql", new_callable=AsyncMock) as mock_sql:
        mock_sql.side_effect = Exception("crashed")
        result = await execute_tool_call("query_documents_sql", {"question": "test"}, USER_ID)
    assert result == ""
