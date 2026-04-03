import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat_service import _merge_tool_call_deltas


def _tc(index, id="", name="", arguments=""):
    tc = MagicMock()
    tc.index = index
    tc.id = id
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def test_merge_single_delta_creates_entry():
    acc = {}
    _merge_tool_call_deltas(acc, [_tc(0, id="c1", name="search_web", arguments='{"q":')])
    assert acc[0] == {"id": "c1", "name": "search_web", "arguments": '{"q":'}

def test_merge_accumulates_arguments_across_chunks():
    acc = {}
    _merge_tool_call_deltas(acc, [_tc(0, id="c1", name="search_web", arguments='{"quer')])
    _merge_tool_call_deltas(acc, [_tc(0, arguments='y": "AI"}')])
    assert acc[0]["arguments"] == '{"query": "AI"}'

def test_merge_handles_two_parallel_tool_calls():
    acc = {}
    _merge_tool_call_deltas(acc, [
        _tc(0, id="c1", name="search_web", arguments="{}"),
        _tc(1, id="c2", name="query_documents_sql", arguments="{}"),
    ])
    assert acc[0]["name"] == "search_web"
    assert acc[1]["name"] == "query_documents_sql"

def test_merge_empty_delta_leaves_acc_unchanged():
    acc = {0: {"id": "c1", "name": "search_web", "arguments": "{}"}}
    _merge_tool_call_deltas(acc, [])
    assert acc[0]["name"] == "search_web"


# ---------------------------------------------------------------------------
# Sub-agent integration in stream_chat
# ---------------------------------------------------------------------------

async def _collect_stream(gen):
    return [item async for item in gen]


def _make_stream_chunk(content=None, finish_reason=None, tool_calls=None):
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls or []
    choice = MagicMock()
    choice.delta = delta
    choice.finish_reason = finish_reason
    chunk = MagicMock()
    chunk.choices = [choice]
    return chunk


async def _async_iter(items):
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_run_subagent_tool_sse_tool_event_emitted_first():
    """data: __tool:run_subagent is yielded before sub-agent SSE events."""
    def _make_tc_delta(idx, id, name, arguments):
        tc = MagicMock()
        tc.index = idx
        tc.id = id
        tc.function.name = name
        tc.function.arguments = arguments
        return tc

    async def mock_subagent_streaming(task, user_id):
        yield {"type": "sse", "data": "data: __subagent_start\n\n"}
        yield {"type": "sse", "data": "data: __subagent_end\n\n"}
        yield {"type": "result", "data": "done"}

    with patch("app.services.chat_service.get_traced_client") as mock_client_fn, \
         patch("app.services.chat_service.get_db") as mock_db_fn, \
         patch("app.services.chat_service.retrieve_context", new_callable=AsyncMock, return_value=[]), \
         patch("app.services.chat_service.subagent_service.run_subagent_streaming", new=mock_subagent_streaming):

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        mock_db.table.return_value.insert.return_value.execute.return_value = None
        mock_db_fn.return_value = mock_db

        # Pass 1 ends with tool_calls for run_subagent
        tc_delta = _make_tc_delta(0, "tc1", "run_subagent", '{"task":"summarize"}')
        pass1_chunks = [
            _make_stream_chunk(tool_calls=[tc_delta]),
            _make_stream_chunk(finish_reason="tool_calls"),
        ]
        # Pass 2 returns final answer
        pass2_chunks = [_make_stream_chunk(content="Summary done.", finish_reason="stop")]

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[
            _async_iter(pass1_chunks),
            _async_iter(pass2_chunks),
        ])
        mock_client_fn.return_value = mock_client

        from app.services.chat_service import stream_chat
        events = await _collect_stream(stream_chat("thread-1", "user-1", "summarize"))

    # Strip "data: " prefix and trailing whitespace for comparison
    data_payloads = [e[6:].strip() for e in events if e.startswith("data: ")]
    tool_idx = data_payloads.index("__tool:run_subagent")
    subagent_start_idx = data_payloads.index("__subagent_start")
    assert tool_idx < subagent_start_idx


@pytest.mark.asyncio
async def test_run_subagent_result_used_in_pass2():
    """The result from the sub-agent is passed as the tool message for Pass 2."""
    def _make_tc_delta(idx, id, name, arguments):
        tc = MagicMock()
        tc.index = idx
        tc.id = id
        tc.function.name = name
        tc.function.arguments = arguments
        return tc

    async def mock_subagent_streaming(task, user_id):
        yield {"type": "sse", "data": "data: __subagent_start\n\n"}
        yield {"type": "sse", "data": "data: __subagent_end\n\n"}
        yield {"type": "result", "data": "Sub-agent result here."}

    with patch("app.services.chat_service.get_traced_client") as mock_client_fn, \
         patch("app.services.chat_service.get_db") as mock_db_fn, \
         patch("app.services.chat_service.retrieve_context", new_callable=AsyncMock, return_value=[]), \
         patch("app.services.chat_service.subagent_service.run_subagent_streaming", new=mock_subagent_streaming):

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        mock_db.table.return_value.insert.return_value.execute.return_value = None
        mock_db_fn.return_value = mock_db

        tc_delta = _make_tc_delta(0, "tc1", "run_subagent", '{"task":"analyze"}')
        pass1_chunks = [
            _make_stream_chunk(tool_calls=[tc_delta]),
            _make_stream_chunk(finish_reason="tool_calls"),
        ]
        pass2_chunks = [_make_stream_chunk(content="Final answer.", finish_reason="stop")]

        captured_messages = []
        call_count = 0

        async def capture_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _async_iter(pass1_chunks)
            captured_messages.extend(kwargs.get("messages", []))
            return _async_iter(pass2_chunks)

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=capture_create)
        mock_client_fn.return_value = mock_client

        from app.services.chat_service import stream_chat
        await _collect_stream(stream_chat("thread-1", "user-1", "analyze docs"))

    tool_messages = [m for m in captured_messages if m.get("role") == "tool"]
    assert any("Sub-agent result here." in m.get("content", "") for m in tool_messages)


@pytest.mark.asyncio
async def test_non_subagent_tools_use_execute_tool_call():
    """Tools other than run_subagent are dispatched via execute_tool_call."""
    def _make_tc_delta(idx, id, name, arguments):
        tc = MagicMock()
        tc.index = idx
        tc.id = id
        tc.function.name = name
        tc.function.arguments = arguments
        return tc

    with patch("app.services.chat_service.get_traced_client") as mock_client_fn, \
         patch("app.services.chat_service.get_db") as mock_db_fn, \
         patch("app.services.chat_service.retrieve_context", new_callable=AsyncMock, return_value=[]), \
         patch("app.services.chat_service.execute_tool_call", new_callable=AsyncMock, return_value="web result") as mock_execute:

        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        mock_db.table.return_value.insert.return_value.execute.return_value = None
        mock_db_fn.return_value = mock_db

        tc_delta = _make_tc_delta(0, "tc1", "search_web", '{"query":"AI news"}')
        pass1_chunks = [
            _make_stream_chunk(tool_calls=[tc_delta]),
            _make_stream_chunk(finish_reason="tool_calls"),
        ]
        pass2_chunks = [_make_stream_chunk(content="Here is the answer.", finish_reason="stop")]

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[
            _async_iter(pass1_chunks),
            _async_iter(pass2_chunks),
        ])
        mock_client_fn.return_value = mock_client

        from app.services.chat_service import stream_chat
        await _collect_stream(stream_chat("thread-1", "user-1", "latest AI news"))

    mock_execute.assert_called_once_with("search_web", {"query": "AI news"}, "user-1")
