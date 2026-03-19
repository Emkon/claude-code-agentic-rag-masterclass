import io
from pypdf import PdfReader
from app.database import get_db
from app.services.embedding_service import chunk_text, get_embeddings


def _broadcast_status(document_id: str, status: str, error_msg: str | None = None) -> None:
    db = get_db()
    payload: dict = {"status": status}
    if error_msg:
        payload["error_msg"] = error_msg
    db.table("documents").update(payload).eq("id", document_id).execute()


async def ingest_document(
    document_id: str,
    user_id: str,
    file_bytes: bytes,
    filename: str,
) -> None:
    db = get_db()

    try:
        # Stage 1: Parse
        _broadcast_status(document_id, "parsing")
        reader = PdfReader(io.BytesIO(file_bytes))
        full_text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        ).strip()

        if not full_text:
            _broadcast_status(document_id, "error", "PDF contained no extractable text")
            return

        # Stage 2: Chunk
        _broadcast_status(document_id, "chunking")
        chunks = chunk_text(full_text)

        if not chunks:
            _broadcast_status(document_id, "error", "No chunks produced after splitting")
            return

        # Stage 3: Embed
        _broadcast_status(document_id, "embedding")
        embeddings = await get_embeddings(chunks)

        # Stage 4: Store chunks in batches
        chunk_rows = [
            {
                "document_id": document_id,
                "user_id": user_id,
                "content": chunk,
                "embedding": embedding,
                "chunk_index": idx,
            }
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        batch_size = 100
        for i in range(0, len(chunk_rows), batch_size):
            db.table("chunks").insert(chunk_rows[i : i + batch_size]).execute()

        # Stage 5: Complete
        db.table("documents").update(
            {"status": "complete", "chunk_count": len(chunks)}
        ).eq("id", document_id).execute()

    except Exception as exc:
        _broadcast_status(document_id, "error", str(exc)[:500])
        raise
