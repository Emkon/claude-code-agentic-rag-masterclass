import asyncio
import hashlib
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from app.auth import get_current_user
from app.database import get_db
from app.models import DocumentResponse
from app.services.ingestion_service import ingest_document


def sanitize_storage_key(filename: str) -> str:
    """Remove characters invalid for Supabase Storage keys."""
    name = re.sub(r'[^\w.\-]', '_', filename)
    return re.sub(r'_+', '_', name)

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/html",
    "text/markdown",
    "text/plain",            # browsers may send .md files as text/plain
    "application/octet-stream",  # generic fallback — extension checked below
}

ALLOWED_EXTENSIONS: set[str] = {
    ".pdf", ".docx", ".html", ".htm", ".md", ".markdown"
}


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    file_ext = Path(file.filename or "").suffix.lower()

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Accepted: .pdf, .docx, .html, .md",
        )

    # For generic MIME types, require a known extension
    if file.content_type in ("application/octet-stream", "text/plain"):
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported extension '{file_ext}'. Accepted: .pdf, .docx, .html, .htm, .md, .markdown",
            )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    content_hash = hashlib.sha256(file_bytes).hexdigest()
    db = get_db()
    user_id = user["id"]
    storage_path = f"{user_id}/{sanitize_storage_key(file.filename)}"

    # Check for existing document with same (user_id, filename)
    existing = (
        db.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .eq("filename", file.filename)
        .execute()
    )

    if existing.data:
        doc = existing.data[0]

        # Case 1: Same hash — already up to date, skip ingestion
        if doc["content_hash"] == content_hash:
            return JSONResponse(
                content=doc,
                headers={"X-Dedup-Result": "already-up-to-date"},
                status_code=200,
            )

        # Case 2: Different hash — delete old chunks, re-ingest
        db.table("chunks").delete().eq("document_id", doc["id"]).execute()

        db.storage.from_("documents").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type or "application/octet-stream", "upsert": "true"},
        )

        updated = (
            db.table("documents")
            .update({
                "content_hash": content_hash,
                "size_bytes": len(file_bytes),
                "status": "uploading",
                "chunk_count": 0,
                "error_msg": None,
            })
            .eq("id", doc["id"])
            .execute()
        )

        document = updated.data[0]
        asyncio.create_task(ingest_document(document["id"], user_id, file_bytes, file.filename))

        return JSONResponse(
            content=document,
            headers={"X-Dedup-Result": "updated"},
            status_code=200,
        )

    # Case 3: New file — normal first-time ingestion
    db.storage.from_("documents").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": file.content_type or "application/octet-stream", "upsert": "true"},
    )

    result = db.table("documents").insert({
        "user_id": user_id,
        "filename": file.filename,
        "storage_path": storage_path,
        "size_bytes": len(file_bytes),
        "status": "uploading",
        "content_hash": content_hash,
    }).execute()

    document = result.data[0]
    asyncio.create_task(ingest_document(document["id"], user_id, file_bytes, file.filename))

    return JSONResponse(content=document, status_code=201)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(user: dict = Depends(get_current_user)):
    db = get_db()
    result = (
        db.table("documents")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    user_id = user["id"]

    doc_result = (
        db.table("documents")
        .select("storage_path")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not doc_result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_path = doc_result.data[0]["storage_path"]

    try:
        db.storage.from_("documents").remove([storage_path])
    except Exception:
        pass

    db.table("documents").delete().eq("id", document_id).eq("user_id", user_id).execute()
