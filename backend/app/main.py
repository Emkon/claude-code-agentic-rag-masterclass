from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import threads, messages, documents

app = FastAPI(title="RAG Masterclass API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(threads.router)
app.include_router(messages.router)
app.include_router(documents.router)
