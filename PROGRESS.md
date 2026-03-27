# Progress

## Convention
- `[ ]` = Not started
- `[-]` = In progress
- `[x]` = Completed

## Modules

### Module 1: App Shell + Observability ✅
- [x] Database — threads + messages tables, RLS, updated_at trigger
- [x] Backend — FastAPI, venv, Groq streaming, LangSmith tracing, auth middleware
- [x] Frontend — React + Vite + Tailwind + shadcn, chat UI, auth pages
- [x] End-to-End — both servers running, chat working, streaming confirmed

### Module 2: BYO Retrieval + Memory ✅
- [x] Database — documents + chunks tables, RLS, HNSW index, match_chunks RPC, Realtime enabled, Storage bucket
- [x] Backend — embedding_service (local sentence-transformers), ingestion_service, retrieval_service, documents router, chat_service updated
- [x] Frontend — DocumentsPage with drag-and-drop, useDocuments hook, Realtime status updates, sources indicator
- [x] UI — white sidebar with Chat/Documents nav + user profile, stop generation button (AbortController)
- [x] End-to-End Validation — upload PDF → status live update → chat retrieves from document → stop mid-stream works

**Repository:** https://github.com/Emkon/claude-code-agentic-rag-masterclass

**Running on:**
- Backend: `http://localhost:8001`
- Frontend: `http://localhost:5174`

**Start commands:**
```bash
# Terminal 1
cd backend && venv/Scripts/uvicorn app.main:app --reload --port 8001

# Terminal 2
cd frontend && npm run dev
```

### Module 3: Record Manager ✅
- [x] Database — add `content_hash` column to documents table
- [x] Backend — hash file bytes on upload, detect duplicate/changed files
- [x] Backend — skip re-ingestion if hash matches, re-ingest if changed
- [x] End-to-End — upload same file twice → no duplicate chunks; modify file → re-ingests
- [x] UI — "Already up to date" / "Updating..." / "Updated" status badges

### Module 4: Metadata Extraction
- [ ] LLM-extracted structured metadata, filter retrieval by metadata

### Module 5: Multi-Format Support
- [ ] PDF, DOCX, HTML, Markdown via docling

### Module 6: Hybrid Search & Reranking
- [ ] Keyword + vector search, RRF combination, reranking

### Module 7: Additional Tools
- [ ] Text-to-SQL tool
- [ ] Web search fallback

### Module 8: Sub-Agents
- [ ] Sub-agent delegation, nested tool display, reasoning visibility
