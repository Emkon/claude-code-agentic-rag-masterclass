import logging
from app.services.sql_service import query_documents_sql
from app.services.web_search_service import search_web

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_subagent",
            "description": (
                "Delegate complex, multi-step document analysis to a specialized sub-agent "
                "that can perform multiple sequential retrieval and search operations. "
                "Use for: comprehensive document summaries, cross-document analysis, "
                "tasks requiring iterative retrieval, or deep research questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Detailed task description for the sub-agent to complete",
                    }
                },
                "required": ["task"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_documents_sql",
            "description": (
                "Query your uploaded documents using SQL to answer questions about "
                "document metadata: counts, dates, topics, entities, file names, types, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Natural language question to answer"}
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web for current information not available in uploaded documents. "
                "Use for recent events, news, or general knowledge questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
]


async def execute_tool_call(tool_name: str, tool_args: dict, user_id: str) -> str:
    """Dispatch a tool call. Returns result string. Never raises."""
    logger.info(f"[tool_service] tool={tool_name!r} args={tool_args!r}")
    try:
        if tool_name == "query_documents_sql":
            return await query_documents_sql(tool_args.get("question", ""), user_id)
        elif tool_name == "search_web":
            return await search_web(tool_args.get("query", ""))
        else:
            logger.warning(f"[tool_service] unknown tool: {tool_name!r}")
            return f"Unknown tool: {tool_name}"
    except Exception as exc:
        logger.warning(f"[tool_service] execute_tool_call error for {tool_name!r}: {exc}")
        return ""
