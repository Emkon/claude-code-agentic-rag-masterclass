from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.auth import get_current_user
from app.database import get_db
from app.models import MessageCreate, MessageResponse
from app.services.chat_service import stream_chat

router = APIRouter(prefix="/threads", tags=["messages"])


@router.post("/{thread_id}/messages")
async def send_message(
    thread_id: str,
    body: MessageCreate,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    existing = (
        db.table("messages")
        .select("id")
        .eq("thread_id", thread_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        title = " ".join(body.content.strip().split()[:5])
        db.table("threads").update({"title": title}).eq("id", thread_id).eq("user_id", user["id"]).execute()

    return StreamingResponse(
        stream_chat(thread_id, user["id"], body.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{thread_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    result = (
        db.table("messages")
        .select("*")
        .eq("thread_id", thread_id)
        .eq("user_id", user["id"])
        .order("created_at", desc=False)
        .execute()
    )
    return result.data
