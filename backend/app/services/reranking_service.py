import asyncio
from sentence_transformers.cross_encoder import CrossEncoder

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(RERANKER_MODEL)
    return _model


async def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """
    Score each chunk against the query with a CrossEncoder.
    Returns chunks sorted by descending score.
    Falls back to original order on any error — never raises.
    """
    if not chunks:
        return chunks
    try:
        model = _get_model()
        pairs = [[query, chunk["content"]] for chunk in chunks]
        loop = asyncio.get_event_loop()
        scores: list[float] = await loop.run_in_executor(
            None, lambda: model.predict(pairs).tolist()
        )
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in ranked]
    except Exception as exc:
        print(f"[reranking_service] rerank failed, using original order: {exc}")
        return chunks
