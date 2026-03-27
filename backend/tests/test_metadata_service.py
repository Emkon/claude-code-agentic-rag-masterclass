import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.metadata_service import (
    extract_document_metadata,
    extract_query_filters,
    DocumentMetadata,
    QueryFilters,
)

pytestmark = pytest.mark.asyncio


def _mock_llm_response(json_str: str):
    """Helper: build a fake Groq response object returning the given JSON string."""
    response = MagicMock()
    response.choices[0].message.content = json_str
    return response


# --- extract_document_metadata ---

async def test_metadata_parses_all_fields():
    """LLM returns well-formed JSON → all Pydantic fields populated correctly."""
    fake_json = '{"entity":"Apple","year":2024,"quarter":"Q3","document_type":"earnings_report","language":"en","topic":"quarterly results","summary":"Apple Q3 2024 earnings."}'
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response(fake_json)
        )
        result = await extract_document_metadata("Apple Q3 2024 earnings...")

    assert result.entity == "Apple"
    assert result.year == 2024
    assert result.quarter == "Q3"
    assert result.document_type == "earnings_report"
    assert result.language == "en"


async def test_metadata_year_coerced_from_string():
    """LLM returns year as a string → Pydantic coerces it to int."""
    fake_json = '{"entity":"Tesla","year":"2023"}'
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response(fake_json)
        )
        result = await extract_document_metadata("some text")

    assert result.year == 2023
    assert isinstance(result.year, int)


async def test_metadata_partial_fields():
    """LLM returns only some fields → missing fields are None, not an error."""
    fake_json = '{"entity":"Microsoft"}'
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response(fake_json)
        )
        result = await extract_document_metadata("some text")

    assert result.entity == "Microsoft"
    assert result.year is None
    assert result.quarter is None


async def test_metadata_llm_error_returns_empty():
    """LLM call raises an exception → returns empty DocumentMetadata, never raises."""
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            side_effect=Exception("API timeout")
        )
        result = await extract_document_metadata("some text")

    assert isinstance(result, DocumentMetadata)
    assert result.entity is None
    assert result.year is None


async def test_metadata_invalid_json_returns_empty():
    """LLM returns malformed JSON → Pydantic parse fails → returns empty DocumentMetadata."""
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response("not valid json {{")
        )
        result = await extract_document_metadata("some text")

    assert isinstance(result, DocumentMetadata)
    assert result.entity is None


# --- extract_query_filters ---

async def test_filters_parses_correctly():
    """LLM extracts entity, year, and quarter from a specific question."""
    fake_json = '{"entity":"Tesla","year":2023,"quarter":"Q2"}'
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response(fake_json)
        )
        result = await extract_query_filters("What were Tesla's Q2 2023 results?")

    assert result.entity == "Tesla"
    assert result.year == 2023
    assert result.quarter == "Q2"


async def test_filters_empty_for_general_question():
    """General question → LLM returns empty JSON → all filters are None."""
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            return_value=_mock_llm_response("{}")
        )
        result = await extract_query_filters("Summarize the main points")

    assert result.entity is None
    assert result.year is None
    assert result.quarter is None
    assert result.document_type is None


async def test_filters_llm_error_returns_empty():
    """LLM call fails → returns empty QueryFilters, never raises."""
    with patch("app.services.metadata_service.get_traced_client") as mock_fn:
        mock_fn.return_value.chat.completions.create = AsyncMock(
            side_effect=Exception("rate limit")
        )
        result = await extract_query_filters("What were Apple's results?")

    assert isinstance(result, QueryFilters)
    assert result.entity is None
