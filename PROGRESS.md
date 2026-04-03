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

### Module 4: Metadata Extraction ✅
- [x] Database — `metadata` JSONB column on documents table, `match_chunks` RPC updated with optional `filter_document_ids`, `documents_status_check` constraint updated
- [x] Backend — `metadata_service.py` with `DocumentMetadata` + `QueryFilters` Pydantic models, `extract_document_metadata()`, `extract_query_filters()`
- [x] Backend — `ingestion_service.py` — Stage 2 "extracting" between parse and chunk
- [x] Backend — `retrieval_service.py` — pre-filter by metadata before vector search, unfiltered fallback
- [x] Frontend — `types/index.ts` — `extracting` status + `metadata` field
- [x] Frontend — `DocumentsPage.tsx` — "Extracting metadata..." status + blue pill badges
- [x] Tests — 8 unit tests, all passing (`pytest tests/test_metadata_service.py -v`)

### Module 5: Multi-Format Support ✅
- [x] Backend — `parsing_service.py` with docling `DocumentConverter` (singleton + async executor pattern)
- [x] Backend — `ingestion_service.py` Stage 1 replaced: pypdf → `parse_document(file_bytes, filename)`
- [x] Backend — `routers/documents.py` — accepts PDF, DOCX, HTML, Markdown; generic MIME fallback uses extension check; storage content-type fixed
- [x] Frontend — `DocumentsPage.tsx` — `accept` updated to `.pdf,.docx,.html,.htm,.md,.markdown`; help text updated
- [x] Tests — 11 unit tests, all passing (`pytest tests/test_parsing_service.py -v`); full suite 19/19

### Module 6: Hybrid Search & Reranking ✅
- [x] Database — `keyword_search_chunks` Supabase RPC (Postgres FTS via `plainto_tsquery`/`ts_rank`) + GIN index on `chunks.content`
- [x] Backend — `reranking_service.py` — CrossEncoder singleton (`cross-encoder/ms-marco-MiniLM-L-6-v2`) + `rerank_chunks()`
- [x] Backend — `retrieval_service.py` — `_reciprocal_rank_fusion()`, `_keyword_search()`, updated `retrieve_context()` (vector + keyword → RRF → rerank → Top-5)
- [x] Tests — `test_reranking_service.py` (8 tests) + `test_retrieval_service.py` (8 tests), full suite 35/35

### Module 7: Additional Tools
- [ ] Text-to-SQL tool
- [ ] Web search fallback

### Module 8: Sub-Agents
- [ ] Sub-agent delegation, nested tool display, reasoning visibility
