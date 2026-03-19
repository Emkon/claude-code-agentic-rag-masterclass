from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.database import get_db
from app.models import ThreadCreate, ThreadResponse, ThreadUpdate

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("", response_model=ThreadResponse)
async def create_thread(
    body: ThreadCreate,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    result = (
        db.table("threads")
        .insert({"user_id": user["id"], "title": body.title})
        .execute()
    )
    return result.data[0]


@router.get("", response_model=list[ThreadResponse])
async def list_threads(user: dict = Depends(get_current_user)):
    db = get_db()
    result = (
        db.table("threads")
        .select("*")
        .eq("user_id", user["id"])
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


@router.delete("/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db.table("threads").delete().eq("id", thread_id).eq("user_id", user["id"]).execute()


@router.patch("/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    body: ThreadUpdate,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    result = (
        db.table("threads")
        .update({"title": body.title})
        .eq("id", thread_id)
        .eq("user_id", user["id"])
        .execute()
    )
    return result.data[0]
