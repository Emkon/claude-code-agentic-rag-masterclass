import pytest
from unittest.mock import AsyncMock, patch
from app.services.web_search_service import search_web, _format_tavily_results, _format_ddg_results

pytestmark = pytest.mark.asyncio


def test_format_tavily_results_includes_title_content_url():
    r = [{"title": "AI", "content": "desc", "url": "https://ai.com"}]
    out = _format_tavily_results(r)
    assert "AI" in out and "desc" in out and "https://ai.com" in out

def test_format_ddg_results_includes_title_body_href():
    r = [{"title": "Python", "body": "lang", "href": "https://python.org"}]
    out = _format_ddg_results(r)
    assert "Python" in out and "lang" in out and "https://python.org" in out

def test_format_tavily_results_caps_at_five():
    r = [{"title": f"r{i}", "content": "x", "url": "u"} for i in range(10)]
    assert _format_tavily_results(r).count("**r") == 5

async def test_search_web_uses_tavily_when_key_set():
    with patch("app.services.web_search_service.settings") as mock_settings, \
         patch("app.services.web_search_service._search_tavily", new_callable=AsyncMock) as mock_tavily:
        mock_settings.tavily_api_key = "tvly-key"
        mock_tavily.return_value = "Tavily result"
        result = await search_web("AI news")
    mock_tavily.assert_called_once_with("AI news")
    assert result == "Tavily result"

async def test_search_web_uses_ddg_when_no_key():
    with patch("app.services.web_search_service.settings") as mock_settings, \
         patch("app.services.web_search_service._search_duckduckgo", new_callable=AsyncMock) as mock_ddg:
        mock_settings.tavily_api_key = None
        mock_ddg.return_value = "DDG result"
        result = await search_web("climate")
    mock_ddg.assert_called_once_with("climate")
    assert result == "DDG result"

async def test_search_web_falls_back_to_ddg_when_tavily_fails():
    with patch("app.services.web_search_service.settings") as mock_settings, \
         patch("app.services.web_search_service._search_tavily", new_callable=AsyncMock) as mock_tavily, \
         patch("app.services.web_search_service._search_duckduckgo", new_callable=AsyncMock) as mock_ddg:
        mock_settings.tavily_api_key = "key"
        mock_tavily.side_effect = Exception("rate limited")
        mock_ddg.return_value = "DDG fallback"
        result = await search_web("query")
    mock_ddg.assert_called_once()
    assert result == "DDG fallback"

async def test_search_web_returns_empty_when_both_fail():
    with patch("app.services.web_search_service.settings") as mock_settings, \
         patch("app.services.web_search_service._search_tavily", new_callable=AsyncMock) as mock_tavily, \
         patch("app.services.web_search_service._search_duckduckgo", new_callable=AsyncMock) as mock_ddg:
        mock_settings.tavily_api_key = "key"
        mock_tavily.side_effect = Exception("down")
        mock_ddg.side_effect = Exception("also down")
        result = await search_web("query")
    assert result == ""

async def test_search_web_never_raises():
    with patch("app.services.web_search_service.settings") as mock_settings, \
         patch("app.services.web_search_service._search_tavily", new_callable=AsyncMock) as mock_tavily, \
         patch("app.services.web_search_service._search_duckduckgo", new_callable=AsyncMock) as mock_ddg:
        mock_settings.tavily_api_key = "key"
        mock_tavily.side_effect = RuntimeError("crash")
        mock_ddg.side_effect = RuntimeError("crash")
        result = await search_web("anything")
    assert result == ""
