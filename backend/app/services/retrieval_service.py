from app.database import get_db
from app.services.embedding_service import get_query_embedding
from app.services.metadata_service import extract_query_filters

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

    # Step 1: Extract query filters (fails open — returns all-None on any error)
    filters = await extract_query_filters(query)
    filter_document_ids: list[str] | None = None

    has_filters = any(
        v is not None
        for v in [filters.entity, filters.year, filters.quarter, filters.document_type]
    )

    if has_filters:
        jsonb_filter = filters.model_dump(exclude_none=True)
        doc_result = (
            db.table("documents")
            .select("id")
            .eq("user_id", user_id)
            .contains("metadata", jsonb_filter)
            .execute()
        )
        matched_ids = [r["id"] for r in (doc_result.data or [])]

        if matched_ids:
            filter_document_ids = matched_ids
        # else: zero matches — fall back to unfiltered search (filter_document_ids stays None)

    # Step 2: Embed query
    query_embedding = await get_query_embedding(query)

    # Step 3: Vector search — pass filter_document_ids only when set
    rpc_params: dict = {
        "query_embedding": query_embedding,
        "match_user_id": user_id,
        "match_count": TOP_K,
        "match_threshold": SIMILARITY_THRESHOLD,
    }
    if filter_document_ids is not None:
        rpc_params["filter_document_ids"] = filter_document_ids

    result = db.rpc("match_chunks", rpc_params).execute()
    return result.data or []


def build_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    parts = ["--- RELEVANT DOCUMENT CONTEXT ---"]
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Chunk {i}]\n{chunk['content']}")
    parts.append("--- END CONTEXT ---")
    return "\n\n".join(parts)
