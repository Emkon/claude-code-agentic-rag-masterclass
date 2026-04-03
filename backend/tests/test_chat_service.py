from unittest.mock import MagicMock
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
