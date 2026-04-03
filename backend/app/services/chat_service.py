import json
import logging
from datetime import date
from typing import AsyncGenerator
from app.database import get_db
from app.services.tracing import get_traced_client
from app.services.retrieval_service import retrieve_context, build_context_block
from app.services.tool_service import TOOL_DEFINITIONS, execute_tool_call
from app.services import subagent_service

logger = logging.getLogger(__name__)


def build_system_prompt(context_block: str = "") -> str:
    today = date.today().strftime("%B %d, %Y")
    base = f"You are a helpful AI assistant. Today's date is {today}."
    if context_block:
        base += (
            "\n\nUse the following document context to answer the user's question. "
            "If the answer is not in the context, say so and use your general knowledge.\n\n"
            + context_block
        )
    return base


def _merge_tool_call_deltas(accumulated: dict, delta_tool_calls: list) -> dict:
    """
    Merge streaming tool_call delta objects into a flat dict keyed by index.
    Each entry: {"id": str, "name": str, "arguments": str}
    """
    for tc in delta_tool_calls:
        idx = tc.index
        if idx not in accumulated:
            accumulated[idx] = {"id": "", "name": "", "arguments": ""}
        if tc.id:
            accumulated[idx]["id"] = tc.id
        if tc.function.name:
            accumulated[idx]["name"] += tc.function.name
        if tc.function.arguments:
            accumulated[idx]["arguments"] += tc.function.arguments
    return accumulated


async def stream_chat(
    thread_id: str,
    user_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    db = get_db()
    client = get_traced_client()

    # 1. RAG retrieval
    chunks = await retrieve_context(user_id, user_message)
    context_block = build_context_block(chunks)

    # 2. Fetch full message history
    history_result = (
        db.table("messages")
        .select("role,content")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    history = history_result.data

    # 3. Assemble stateless message list
    messages = [{"role": "system", "content": build_system_prompt(context_block)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # 4. Save user message
    db.table("messages").insert(
        {"thread_id": thread_id, "user_id": user_id, "role": "user", "content": user_message}
    ).execute()

    # 5. Yield source count
    if chunks:
        yield f"data: __sources:{len(chunks)}\n\n"

    # 6. Pass 1 — non-streaming with tools
    # stream=False avoids llama-3.1-8b-instant leaking tool call syntax into delta.content
    response = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="auto",
        stream=False,
    )

    full_response = ""
    choice = response.choices[0]
    message = choice.message
    finish_reason = choice.finish_reason

    # If model generated text before/instead of tool call, stream it
    if message.content:
        full_response += message.content
        yield f"data: {message.content}\n\n"

    # 7. If tools requested — execute and stream Pass 2
    if finish_reason == "tool_calls" and message.tool_calls:
        tool_calls_for_msg = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in message.tool_calls
        ]

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": tool_calls_for_msg,
        })

        for tc in tool_calls_for_msg:
            tool_name = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                tool_args = {}

            yield f"data: __tool:{tool_name}\n\n"

            if tool_name == "run_subagent":
                tool_result = ""
                async for event in subagent_service.run_subagent_streaming(
                    tool_args.get("task", ""), user_id
                ):
                    if event["type"] == "sse":
                        yield event["data"]
                    else:
                        tool_result = event["data"]
            else:
                tool_result = await execute_tool_call(tool_name, tool_args, user_id)

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result or "No results found.",
            })

        # Pass 2 — stream final answer (no tools= to prevent infinite loop)
        stream2 = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            stream=True,
        )
        async for chunk in stream2:
            token = chunk.choices[0].delta.content or ""
            if token:
                full_response += token
                yield f"data: {token}\n\n"

    # 8. Save assistant message
    db.table("messages").insert(
        {"thread_id": thread_id, "user_id": user_id, "role": "assistant", "content": full_response}
    ).execute()

    yield "data: [DONE]\n\n"
