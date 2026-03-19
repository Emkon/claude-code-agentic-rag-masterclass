from app.database import get_db
from app.services.embedding_service import get_query_embedding

TOP_K = 5
SIMILARITY_THRESHOLD = 0.3


async def retrieve_context(user_id: str, query: str) -> list[dict]:
    db = get_db()

    # Skip embedding if user has no chunks
    count_result = (
        db.table("chunks")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not count_result.data:
        return []

    query_embedding = await get_query_embedding(query)

    result = db.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_user_id": user_id,
            "match_count": TOP_K,
            "match_threshold": SIMILARITY_THRESHOLD,
        },
    ).execute()

    return result.data or []


def build_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    parts = ["--- RELEVANT DOCUMENT CONTEXT ---"]
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Chunk {i}]\n{chunk['content']}")
    parts.append("--- END CONTEXT ---")
    return "\n\n".join(parts)
