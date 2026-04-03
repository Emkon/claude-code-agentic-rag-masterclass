import json
import logging
from typing import AsyncGenerator
from app.services.tracing import get_traced_client
from app.services.retrieval_service import retrieve_context, build_context_block
from app.services.sql_service import query_documents_sql
from app.services.web_search_service import search_web

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3

SUBAGENT_SYSTEM_PROMPT = (
    "You are a specialized document analysis agent. Complete the given task by using "
    "available tools to gather information. Be thorough and specific. "
    "Use retrieve_document_chunks to read document content, query_documents_sql for "
    "metadata questions, and search_web for information not in the documents."
)

SUBAGENT_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_document_chunks",
            "description": (
                "Retrieve relevant document chunks for a query using hybrid semantic + keyword search. "
                "Use this to read the actual content of uploaded documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query to retrieve relevant chunks"}
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_documents_sql",
            "description": (
                "Query document metadata using SQL to answer questions about counts, "
                "dates, topics, entities, file names, types, etc."
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
                "Search the web for current information not available in uploaded documents."
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


async def _execute_subagent_tool(name: str, args: dict, user_id: str) -> str:
    """Dispatch a sub-agent tool call. Never raises."""
    try:
        if name == "retrieve_document_chunks":
            chunks = await retrieve_context(user_id, args.get("query", ""))
            return build_context_block(chunks) or "No relevant document chunks found."
        elif name == "query_documents_sql":
            return await query_documents_sql(args.get("question", ""), user_id)
        elif name == "search_web":
            return await search_web(args.get("query", ""))
        else:
            logger.warning(f"[subagent] unknown tool: {name!r}")
            return f"Unknown tool: {name}"
    except Exception as exc:
        logger.warning(f"[subagent] tool execution error for {name!r}: {exc}")
        return ""


async def run_subagent_streaming(
    task: str, user_id: str
) -> AsyncGenerator[dict, None]:
    """
    Run an isolated sub-agent to complete a task.

    Yields dicts:
      {"type": "sse",    "data": "data: __subagent_start\\n\\n"}
      {"type": "sse",    "data": "data: __subagent_tool:{name}\\n\\n"}
      {"type": "sse",    "data": "data: __subagent_end\\n\\n"}
      {"type": "result", "data": "<final text>"}   ← always last
    """
    logger.info(f"[subagent] starting task={repr(task[:120])}")
    yield {"type": "sse", "data": "data: __subagent_start\n\n"}

    client = get_traced_client()
    messages = [
        {"role": "system", "content": SUBAGENT_SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    final_text = ""

    for iteration in range(MAX_ITERATIONS):
        logger.info(f"[subagent] iteration {iteration + 1}/{MAX_ITERATIONS}")
        try:
            response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                tools=SUBAGENT_TOOL_DEFINITIONS,
                tool_choice="auto",
                stream=False,
            )
        except Exception as exc:
            logger.warning(f"[subagent] LLM call failed: {exc}")
            final_text = "Sub-agent encountered an error and could not complete the task."
            break

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        message = choice.message

        if finish_reason == "stop" or finish_reason is None:
            final_text = message.content or ""
            break

        if finish_reason == "tool_calls" and message.tool_calls:
            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(f"[subagent] tool={tool_name!r}")
                yield {"type": "sse", "data": f"data: __subagent_tool:{tool_name}\n\n"}
                tool_result = await _execute_subagent_tool(tool_name, tool_args, user_id)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result or "No results found.",
                })
        else:
            # Unexpected finish reason — treat content as final answer
            final_text = message.content or ""
            break
    else:
        # Exhausted iterations — ask for a final answer without tools
        logger.info("[subagent] max iterations reached, requesting final answer")
        try:
            final_response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                stream=False,
            )
            final_text = final_response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning(f"[subagent] final answer call failed: {exc}")
            final_text = "Sub-agent could not produce a final answer."

    yield {"type": "sse", "data": "data: __subagent_end\n\n"}
    yield {"type": "result", "data": final_text}
