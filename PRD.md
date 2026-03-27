# Agentic RAG Masterclass - PRD

## What We're Building

A RAG application with two interfaces:
1. **Chat** (default view) - Threaded conversations with retrieval-augmented responses
2. **Documents** - Upload PDFs manually, track processing status, manage documents

This is **not** an automated pipeline with connectors. Files are uploaded manually. Configuration is via environment variables, no admin UI.

## Target Users

Technically-minded people who want to build production RAG systems using AI coding tools (Claude Code, Cursor, etc.). They don't need to know Python or React - that's the AI's job.

**They need to understand:**
- RAG concepts deeply (chunking, embeddings, retrieval, reranking)
- Codebase structure (what sits where, how pieces connect)
- How to direct AI to build what they need
- How to direct AI to fix things when they break

## Scope

### In Scope
- ✅ Document ingestion and processing
- ✅ Vector search with pgvector
- ✅ Hybrid search (keyword + vector)
- ✅ Reranking
- ✅ Metadata extraction
- ✅ Record management (deduplication)
- ✅ Multi-format support (PDF, DOCX, HTML, Markdown)
- ✅ Text-to-SQL tool
- ✅ Web search fallback
- ✅ Sub-agents with isolated context
- ✅ Chat with threads and memory
- ✅ Streaming responses
- ✅ Auth with RLS

### Out of Scope
- ❌ Knowledge graphs / GraphRAG
- ❌ Code execution / sandboxing
- ❌ Image/audio/video processing
- ❌ Fine-tuning
- ❌ Multi-tenant admin features
- ❌ Billing/payments
- ❌ Data connectors (Google Drive, SFTP, APIs, webhooks)
- ❌ Scheduled/automated ingestion
- ❌ Admin UI (config via env vars)

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | React + TypeScript + Vite + Tailwind + shadcn/ui |
| Backend | Python + FastAPI |
| Database | Supabase (Postgres + pgvector + Auth + Storage + Realtime) |
| LLM | Groq API (`llama-3.1-8b-instant`) via OpenAI-compatible SDK |
| Embeddings | Hugging Face Inference API (`sentence-transformers/all-MiniLM-L6-v2`, 384 dims, free tier) |
| Observability | LangSmith |

## Runtime

- Backend: `http://localhost:8001` — `cd backend && venv/Scripts/uvicorn app.main:app --reload --port 8001`
- Frontend: `http://localhost:5174` — `cd frontend && npm run dev`

## Repository

**GitHub:** https://github.com/Emkon/claude-code-agentic-rag-masterclass

| Module | Status | Commit |
|--------|--------|--------|
| Module 1: App Shell + Observability | Pushed | `7c9856b` |
| Module 2: BYO Retrieval + Memory | Pushed | `7c9856b` |
| Module 3: Record Manager | Pushed | `f9ba135` |
| Module 4: Metadata Extraction | Pushed | `be42f14` |

## Constraints

- No LLM frameworks — raw OpenAI Python SDK pointed at Groq base URL. Pydantic for structured outputs.
- Row-Level Security on all tables — users only see their own data
- Streaming chat via SSE
- Ingestion status via Supabase Realtime (postgres_changes on `documents` table)
- No LangChain, no LlamaIndex

---

## Architectural Decision: Bypassing Managed RAG

The original course used OpenAI's managed Vector Store (platform.openai.com/storage/vector-stores) — a black box where you upload a file and OpenAI handles embedding, storage, and retrieval invisibly via `file_search`.

**We skipped this entirely.** We built the equivalent from scratch:

| OpenAI Managed | Our Implementation |
|---|---|
| Vector Store UI | Supabase `chunks` table + pgvector |
| OpenAI file upload | `/documents` endpoint + Supabase Storage |
| OpenAI embeddings (hidden) | HuggingFace `all-MiniLM-L6-v2` |
| `file_search` tool | `match_chunks` RPC + `retrieval_service.py` |

This gives total control, zero cost, and full understanding of every layer.

---

## Module 1: App Shell + Observability ✅ COMPLETE

**Built:**
- Supabase Auth (email/password) with RLS on all tables
- Threaded chat — create, rename (pencil icon on hover), delete (trash icon on hover), persistent history
- Groq Chat Completions (`llama-3.1-8b-instant`) with SSE streaming
- Stateless API — full chat history fetched from DB and sent on every request
- LangSmith tracing
- Dynamic system prompt with today's date injected
- Dark sidebar UI with Chat/Documents nav toggle
- ChatGPT-style message bubbles (dark bubble right for user, light bubble + avatar left for assistant)
- Icon send button (dark circle, grays out when empty)
- Separate Sign In / Sign Up / Confirm Email pages with password match validation
- Auto-title threads from first 5 words of first message

**Key decisions:**
- `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` for speed
- OpenAI embeddings → Hugging Face free API
- Vite proxy: `/api` → `http://localhost:8001`
- Port 8000 blocked on Windows → using 8001
- Frontend landed on port 5174 (5173 was in use)
- `python-multipart` required for file uploads (added to requirements.txt)

---

## Module 2: BYO Retrieval + Memory ✅ COMPLETE

**Built:**
- `documents` table (id, user_id, filename, storage_path, size_bytes, status, error_msg, chunk_count) + RLS
- `chunks` table (id, document_id, user_id, content, embedding vector(384), chunk_index) + RLS + HNSW index
- `match_chunks` Supabase RPC function for cosine similarity search (threshold 0.3, top-K 5)
- Supabase Storage bucket `documents` (private, 50MB limit, PDF only) + RLS policies
- Supabase Realtime enabled on `documents` table via `alter publication supabase_realtime add table documents`
- `embedding_service.py` — HuggingFace API, 500-char chunks / 50-char overlap, batch size 32, 60s timeout, `wait_for_model: True`
- `ingestion_service.py` — parse (pypdf) → chunk → embed → store in batches of 100 → broadcast status via DB writes
- `retrieval_service.py` — embed query → `match_chunks` RPC → `build_context_block()`
- `chat_service.py` — retrieves context before every chat turn, injects into system prompt, yields `__sources:N` SSE event
- `routers/documents.py` — POST (upload + background ingest task), GET (list), DELETE (cascade)
- Frontend Documents page — upload button, live status labels with animation, chunk count + file size on complete, delete button
- Frontend `useDocuments` hook — Realtime subscription updates document status in-place without re-fetch
- Sources indicator in ChatWindow — "Searching N document chunks..." while streaming
- Chat/Documents nav toggle in sidebar

**New packages added:**
- `pypdf==4.3.1`
- `python-multipart>=0.0.9`
- `sentence-transformers==3.3.1` (replaces HuggingFace Inference API — deprecated 410)

**Key decisions:**
- Realtime via `postgres_changes` (not Broadcast) — backend just writes to DB, frontend listens
- `asyncio.create_task()` for background ingestion — no Celery needed
- FormData upload: do NOT set Content-Type manually — browser must set boundary
- Storage path: `{user_id}/{sanitized_filename}` — sanitize brackets/spaces with regex
- Embeddings run locally via `sentence-transformers` — HF `/pipeline/feature-extraction/` and `/models/` endpoints both return 410
- Vite proxy must target `http://127.0.0.1:8001` (not `localhost`) on Windows — IPv6 resolution issue
- Upload button lives in the chat input (paperclip icon), not a separate Documents page

**UI Redesign (v1.0):**
- Clean white sidebar with Chat/Documents nav items and user profile at bottom (initials avatar + email + sign out)
- Documents page redesigned with drag-and-drop upload zone + document list (filename, status badge, size, chunks, delete)
- Upload moved from chat input to Documents page only
- Stop generation button (filled square icon) replaces Send while LLM is streaming — uses `AbortController` to cancel fetch mid-stream, partial response cleared cleanly

---

## Module 3: Record Manager ✅ COMPLETE

**Goal:** Prevent duplicate chunks when the same file is uploaded more than once. Only re-ingest if the file content has actually changed.

**Built:**
- `content_hash` (SHA-256) column on `documents` table
- On upload: hash file bytes, check `(user_id, filename)` for existing record
- Three cases: same hash → skip; different hash → delete old chunks + re-ingest; no match → normal first-time ingestion
- `X-Dedup-Result` response header signals outcome to frontend
- UI badges: "Already up to date" / "Updating..." / "Updated"

**Key decisions:**
- Hash-only lookup scoped to `(user_id, filename)` — same content, different filename treated as new document
- Response header used instead of a new DB column — dedup result is transient display state, not persistent data

---

## Module 4: Metadata Extraction ✅ COMPLETE

**Goal:** Extract structured metadata from documents at ingestion time and use it to filter retrieval at query time.

**Built:**
- `metadata` JSONB column on `documents` table
- `match_chunks` RPC updated with optional `filter_document_ids uuid[]` parameter (backward-compatible)
- `metadata_service.py` — `DocumentMetadata` + `QueryFilters` Pydantic models; `extract_document_metadata()` and `extract_query_filters()` using Groq with `response_format={"type": "json_object"}`
- Ingestion pipeline gains Stage 2 "extracting" — LLM extracts `document_type`, `topic`, `entity`, `year`, `quarter`, `language`, `summary` from first 3000 chars
- Retrieval pre-filters candidate documents by JSONB containment before vector search; falls back to unfiltered if no matches
- UI shows "Extracting metadata..." status + blue pill badges (entity, year, quarter, type) on document rows
- 8 unit tests covering happy path and graceful failure for both extraction functions

**Key decisions:**
- Metadata extraction wrapped in try/except — failure never kills ingestion
- Query filter extraction uses `max_tokens=150` to keep chat latency low
- Unfiltered fallback is critical — prevents zero results when query filters match no documents
- `documents_status_check` constraint updated to include `"extracting"`

---

## Module 5: Multi-Format Support
**Build:** PDF/DOCX/HTML/Markdown via docling, cascade deletes
**Learn:** Document parsing challenges, format considerations

---

## Module 6: Hybrid Search & Reranking
**Build:** Keyword + vector search, RRF combination, local reranking
**Learn:** Why vector alone isn't enough, hybrid strategies, reranking

---

## Module 7: Additional Tools
**Build:** Text-to-SQL tool (query structured data), web search fallback (when docs don't have the answer)
**Learn:** Multi-tool agents, routing between structured/unstructured data, graceful fallbacks

---

## Module 8: Sub-Agents
**Build:** Detect full-document scenarios, spawn isolated sub-agent with its own tools, nested tool call display in UI
**Learn:** Context management, agent delegation, hierarchical agent display, when to isolate
