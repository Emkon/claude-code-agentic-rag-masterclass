"""Tests for subagent_service.py"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_response(content="Done.", finish_reason="stop", tool_calls=None):
    """Build a mock non-streaming chat completion response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_call(id="tc1", name="retrieve_document_chunks", arguments='{"query":"test"}'):
    tc = MagicMock()
    tc.id = id
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


@pytest.mark.asyncio
async def test_streaming_emits_subagent_start():
    """First event is the __subagent_start SSE."""
    with patch("app.services.subagent_service.get_traced_client") as mock_client_fn, \
         patch("app.services.subagent_service.retrieve_context", new_callable=AsyncMock, return_value=[]):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_make_response("Answer."))
        mock_client_fn.return_value = mock_client

        from app.services.subagent_service import run_subagent_streaming
        events = [e async for e in run_subagent_streaming("Summarize docs", "user-1")]

    assert events[0] == {"type": "sse", "data": "data: __subagent_start\n\n"}


@pytest.mark.asyncio
async def test_streaming_emits_subagent_end():
    """Second-to-last event is __subagent_end SSE."""
    with patch("app.services.subagent_service.get_traced_client") as mock_client_fn, \
         patch("app.services.subagent_service.retrieve_context", new_callable=AsyncMock, return_value=[]):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_make_response("Answer."))
        mock_client_fn.return_value = mock_client

        from app.services.subagent_service import run_subagent_streaming
        events = [e async for e in run_subagent_streaming("Summarize docs", "user-1")]

    assert events[-2] == {"type": "sse", "data": "data: __subagent_end\n\n"}


@pytest.mark.asyncio
async def test_streaming_final_event_is_result():
    """Last event has type='result' with the LLM's final answer."""
    with patch("app.services.subagent_service.get_traced_client") as mock_client_fn, \
         patch("app.services.subagent_service.retrieve_context", new_callable=AsyncMock, return_value=[]):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_make_response("Final answer."))
        mock_client_fn.return_value = mock_client

        from app.services.subagent_service import run_subagent_streaming
        events = [e async for e in run_subagent_streaming("task", "user-1")]

    assert events[-1]["type"] == "result"
    assert events[-1]["data"] == "Final answer."


@pytest.mark.asyncio
async def test_streaming_emits_tool_event_per_tool_call():
    """Each sub-agent tool call emits a __subagent_tool:{name} SSE event."""
    tc = _make_tool_call(name="retrieve_document_chunks", arguments='{"query":"revenue"}')
    stop_response = _make_response("Here is the summary.")

    with patch("app.services.subagent_service.get_traced_client") as mock_client_fn, \
         patch("app.services.subagent_service.retrieve_context", new_callable=AsyncMock, return_value=[]):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[
            _make_response(content=None, finish_reason="tool_calls", tool_calls=[tc]),
            stop_response,
        ])
        mock_client_fn.return_value = mock_client

        from app.services.subagent_service import run_subagent_streaming
        events = [e async for e in run_subagent_streaming("task", "user-1")]

    sse_data = [e["data"] for e in events if e["type"] == "sse"]
    assert "data: __subagent_tool:retrieve_document_chunks\n\n" in sse_data


@pytest.mark.asyncio
async def test_stop_finish_reason_exits_loop_immediately():
    """If first response has finish_reason='stop', no further LLM calls are made."""
    with patch("app.services.subagent_service.get_traced_client") as mock_client_fn, \
         patch("app.services.subagent_service.retrieve_context", new_callable=AsyncMock, return_value=[]):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_make_response("Done."))
        mock_client_fn.return_value = mock_client

        from app.services.subagent_service import run_subagent_streaming
        _ = [e async for e in run_subagent_streaming("task", "user-1")]

    assert mock_client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_max_iterations_respected():
    """Loop runs at most MAX_ITERATIONS times even with repeated tool_calls responses."""
    tc = _make_tool_call()
    tool_response = _make_response(content=None, finish_reason="tool_calls", tool_calls=[tc])
    final_response = _make_response("Final.")

    with patch("app.services.subagent_service.get_traced_client") as mock_client_fn, \
         patch("app.services.subagent_service.retrieve_context", new_callable=AsyncMock, return_value=[]):
        mock_client = MagicMock()
        # Always return tool_calls — the loop should break and call once more for final answer
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[tool_response, tool_response, tool_response, final_response]
        )
        mock_client_fn.return_value = mock_client

        from app.services.subagent_service import MAX_ITERATIONS, run_subagent_streaming
        events = [e async for e in run_subagent_streaming("task", "user-1")]

    # MAX_ITERATIONS calls in loop + 1 final answer call
    assert mock_client.chat.completions.create.call_count == MAX_ITERATIONS + 1
    assert events[-1]["type"] == "result"


@pytest.mark.asyncio
async def test_execute_subagent_tool_retrieve():
    """retrieve_document_chunks calls retrieve_context and builds context block."""
    mock_chunks = [{"id": "c1", "content": "Revenue was $10M"}]
    with patch("app.services.subagent_service.retrieve_context", new_callable=AsyncMock, return_value=mock_chunks):
        from app.services.subagent_service import _execute_subagent_tool
        result = await _execute_subagent_tool("retrieve_document_chunks", {"query": "revenue"}, "user-1")

    assert "Revenue was $10M" in result


@pytest.mark.asyncio
async def test_execute_subagent_tool_unknown_returns_error():
    """Unknown tool name returns an error string instead of raising."""
    from app.services.subagent_service import _execute_subagent_tool
    result = await _execute_subagent_tool("nonexistent_tool", {}, "user-1")
    assert "Unknown tool" in result
