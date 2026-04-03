import asyncio
import logging
from app.database import get_db
from app.services.embedding_service import get_query_embedding
from app.services.metadata_service import extract_query_filters
from app.services.reranking_service import rerank_chunks

logger = logging.getLogger(__name__)

TOP_K = 5
SIMILARITY_THRESHOLD = 0.1   # Lowered from 0.3 — reranker handles quality filtering
CANDIDATE_POOL = 20           # Candidates fetched per search arm for RRF


def _reciprocal_rank_fusion(
    vector_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
) -> list[dict]:
    """
    Merge two ranked lists via Reciprocal Rank Fusion.
    RRF score = sum over each list of 1 / (k + rank), rank is 1-indexed.
    k=60 is the standard value from Cormack et al. 2009.
    Returns unique chunks ordered by descending RRF score.
    """
    scores: dict[str, float] = {}
    chunks_by_id: dict[str, dict] = {}

    for rank, chunk in enumerate(vector_results, start=1):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunks_by_id[cid] = chunk

    for rank, chunk in enumerate(keyword_results, start=1):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
        chunks_by_id[cid] = chunk

    sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    result = []
    for cid in sorted_ids:
        chunk = dict(chunks_by_id[cid])
        chunk["rrf_score"] = scores[cid]
        result.append(chunk)
    return result


async def _keyword_search(
    db,
    query: str,
    user_id: str,
    filter_document_ids: list[str] | None,
) -> list[dict]:
    """Keyword search via Postgres FTS. Returns [] on any failure (graceful degradation)."""
    try:
        params: dict = {
            "query_text": query,
            "match_user_id": user_id,
            "match_count": CANDIDATE_POOL,
        }
        if filter_document_ids is not None:
            params["filter_document_ids"] = filter_document_ids
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: db.rpc("keyword_search_chunks", params).execute()
        )
        return result.data or []
    except Exception as exc:
        logger.warning(f"[retrieval] keyword search failed, falling back to vector-only: {exc}")
        return []


async def retrieve_context(user_id: str, query: str) -> list[dict]:
    logger.info(f"[retrieval] query={query!r}")
    db = get_db()

    # Early exit if user has no chunks
    count_result = (
        db.table("chunks")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not count_result.data:
        return []

    # Step 1: Extract query filters (fails open)
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

    # Step 2: Embed query
    query_embedding = await get_query_embedding(query)

    # Step 3a: Vector search (CANDIDATE_POOL candidates)
    vector_params: dict = {
        "query_embedding": query_embedding,
        "match_user_id": user_id,
        "match_count": CANDIDATE_POOL,
        "match_threshold": SIMILARITY_THRESHOLD,
    }
    if filter_document_ids is not None:
        vector_params["filter_document_ids"] = filter_document_ids

    loop = asyncio.get_event_loop()
    vector_result = await loop.run_in_executor(
        None, lambda: db.rpc("match_chunks", vector_params).execute()
    )
    vector_results = vector_result.data or []

    # Step 3b: Keyword search (graceful fallback on failure)
    keyword_results = await _keyword_search(db, query, user_id, filter_document_ids)

    # Step 4: RRF fusion
    fused = _reciprocal_rank_fusion(vector_results, keyword_results)
    if not fused:
        return []

    # Step 5: Rerank fused candidates, return Top-K
    reranked = await rerank_chunks(query, fused[:CANDIDATE_POOL])
    top = reranked[:TOP_K]
    logger.info(f"[retrieval] vector={len(vector_results)} keyword={len(keyword_results)} fused={len(fused)} returning={len(top)}")
    for i, c in enumerate(top, 1):
        logger.info(f"[retrieval] [{i}] rrf={c.get('rrf_score', 0):.4f} | {c['content'][:120].replace(chr(10), ' ')!r}")
    return top


def build_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    parts = ["--- RELEVANT DOCUMENT CONTEXT ---"]
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[Chunk {i}]\n{chunk['content']}")
    parts.append("--- END CONTEXT ---")
    return "\n\n".join(parts)
