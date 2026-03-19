import asyncio
from sentence_transformers import SentenceTransformer

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    loop = asyncio.get_event_loop()
    model = _get_model()
    embeddings = await loop.run_in_executor(
        None, lambda: model.encode(texts, show_progress_bar=False).tolist()
    )
    return embeddings


async def get_query_embedding(text: str) -> list[float]:
    result = await get_embeddings([text])
    return result[0]
