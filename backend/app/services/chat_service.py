from datetime import date
from typing import AsyncGenerator
from app.database import get_db
from app.services.tracing import get_traced_client
from app.services.retrieval_service import retrieve_context, build_context_block


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


async def stream_chat(
    thread_id: str,
    user_id: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    db = get_db()
    client = get_traced_client()

    # 1. Retrieve relevant chunks
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

    # 4. Save user message to DB
    db.table("messages").insert(
        {
            "thread_id": thread_id,
            "user_id": user_id,
            "role": "user",
            "content": user_message,
        }
    ).execute()

    # 5. Yield source count before streaming (if any chunks found)
    if chunks:
        yield f"data: __sources:{len(chunks)}\n\n"

    # 6. Stream from Groq
    stream = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        stream=True,
    )

    full_response = ""
    async for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            full_response += token
            yield f"data: {token}\n\n"

    # 7. Save assistant message
    db.table("messages").insert(
        {
            "thread_id": thread_id,
            "user_id": user_id,
            "role": "assistant",
            "content": full_response,
        }
    ).execute()

    yield "data: [DONE]\n\n"
