from app.database import get_db
from app.services.embedding_service import chunk_text, get_embeddings
from app.services.metadata_service import extract_document_metadata
from app.services.parsing_service import parse_document


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
        full_text = await parse_document(file_bytes, filename)

        if not full_text:
            _broadcast_status(document_id, "error", "Document contained no extractable text")
            return

        # Stage 2: Extract metadata
        _broadcast_status(document_id, "extracting")
        try:
            metadata = await extract_document_metadata(full_text[:3000])
            metadata_dict = metadata.model_dump(exclude_none=True)
            if metadata_dict:
                db.table("documents").update({"metadata": metadata_dict}).eq("id", document_id).execute()
        except Exception as exc:
            print(f"[ingestion_service] metadata update failed: {exc}")
        # Continue regardless — metadata failure must never kill ingestion

        # Stage 3: Chunk
        _broadcast_status(document_id, "chunking")
        chunks = chunk_text(full_text)

        if not chunks:
            _broadcast_status(document_id, "error", "No chunks produced after splitting")
            return

        # Stage 4: Embed
        _broadcast_status(document_id, "embedding")
        embeddings = await get_embeddings(chunks)

        # Stage 5: Store chunks in batches
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

        # Stage 6: Complete
        db.table("documents").update(
            {"status": "complete", "chunk_count": len(chunks)}
        ).eq("id", document_id).execute()

    except Exception as exc:
        _broadcast_status(document_id, "error", str(exc)[:500])
        raise
