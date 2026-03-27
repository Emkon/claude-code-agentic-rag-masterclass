from datetime import datetime
from pydantic import BaseModel


class ThreadCreate(BaseModel):
    title: str = "New Chat"


class ThreadResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ThreadUpdate(BaseModel):
    title: str


class DocumentResponse(BaseModel):
    id: str
    user_id: str
    filename: str
    storage_path: str
    size_bytes: int | None
    status: str
    error_msg: str | None
    chunk_count: int
    content_hash: str | None = None
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    user_id: str
    role: str
    content: str
    created_at: datetime
