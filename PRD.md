# Agentic RAG Masterclass - PRD

## What We're Building

A RAG application with two interfaces:
1. **Chat** (default view) - Threaded conversations with retrieval-augmented responses
2. **Ingestion** - Upload files manually, track processing, manage documents

This is **not** an automated pipeline with connectors. Files are uploaded manually via drag-and-drop. Configuration is via environment variables, no admin UI.

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
| LLM | Groq API (e.g., Llama-3.3-70B) via OpenAI-compatible SDK |
| Embeddings | Local models (e.g., sentence-transformers) to keep it 100% free |
| Observability | LangSmith |

## Constraints

- No LLM frameworks - raw OpenAI Python SDK pointed to Groq's Base URL using the standard Chat Completions API. Pydantic for structured outputs.
- Row-Level Security on all tables - users only see their own data
- Streaming chat via SSE
- Ingestion status via Supabase Realtime

---

## Module 1: The App Shell + Observability

**Build:** Auth, chat UI, Groq Chat Completions API integration (managing threads manually), LangSmith tracing

**Learn:** Setting up the foundation for custom RAG, standardizing API calls, and avoiding vendor lock-in from day one.

**Note:** By starting directly with Groq, we bypass the "black box" managed RAG phase entirely. This gives us total control over our memory and retrieval pipeline right out of the gate, while benefiting from Groq's blazing inference speed.

---

## Architectural Decision: Bypassing Managed RAG

The original tutorial included a transition phase from OpenAI's managed Responses API (which handled memory and file search invisibly) to a custom Chat Completions setup. Since we are optimizing for speed and zero cost with Groq, we are skipping the managed "training wheels" entirely.

**The decision:** We implement the standard OpenAI-compatible Chat Completions API from Module 1, configuring the client to hit the Groq API. 

**This is a lesson in steering Claude Code**: you need to clearly communicate to the AI that we are *not* using OpenAI's proprietary endpoints or managed file search. You must explicitly guide the AI to use Groq, set the correct environment variables (`GROQ_API_KEY`), and handle message history manually in the database from the very beginning.

---

## Module 2: BYO Retrieval + Memory

**Build:** Ingestion UI, file storage, local chunking → local embedding → pgvector, retrieval tool, Groq Chat Completions integration, chat history storage (stateless API - you manage memory now), realtime ingestion status

**Learn:** Chunking, embeddings, vector search, tool calling, relevance thresholds, managing conversation history, **steering AI agents to build custom pipelines.**

---

## Module 3: Record Manager

**Build:** Content hashing, detect changes, only process what's new/modified

**Learn:** Why naive ingestion duplicates, incremental updates

---

## Module 4: Metadata Extraction

**Build:** LLM (Groq) extracts structured metadata, filter retrieval by metadata

**Learn:** Structured extraction, schema design, metadata-enhanced retrieval

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

**Learn:** Multi-tool agents, routing between structured/unstructured data, graceful fallbacks, attribution for trust

---

## Module 8: Sub-Agents

**Build:** Detect full-document scenarios, spawn isolated sub-agent with its own tools, nested tool call display in UI, show reasoning from both main agent and sub-agents

**Learn:** Context management, agent delegation, hierarchical agent display, when to isolate