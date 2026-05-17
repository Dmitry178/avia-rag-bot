# AI Airport Staff Assistant

**English** · [Русский](README_RU.md)

Educational project — a RAG bot for airport staff: answers questions from an internal knowledge base (SOP, FAQ, scenarios, decision trees). The UI lets you chat with the assistant, manage conversations, configure LLM/RAG parameters, and (in RAG mode) watch the pipeline trace.

Monorepo: **backend** (FastAPI, indexing, RAG, chat API) + **frontend** (React SPA). Telegram and Docker are planned for later stages.

## What the app does

- **Knowledge base indexing** — a markdown document is split into chunks; embeddings are built for each and stored in SQLite + FAISS.
- **Chats** — create, select, close, and delete conversations; message history and settings are stored on the backend.
- **Two operating modes** (switched in the header):
  - **LLM** — direct dialogue with the language model, no knowledge base search. **Parameters** panel: chat history, custom system prompt (free mode without guards).
  - **RAG** — answers grounded in indexed documents. **Trace** panel: retrieval settings and pipeline steps.
- **Per-chat settings** — RAG/LLM parameters are saved on the chat and snapshotted in each message’s metadata.
- **Theme** — light, dark, or system (follows OS settings).
- **UI language** — Russian and English; the choice persists across sessions.

## Stack

| Part | Technologies |
|------|--------------|
| Backend | Python 3.13, FastAPI, SQLModel, SQLite, FAISS, uv |
| LLM | OpenAI-compatible API (chat + embeddings) |
| Frontend | React 19, TypeScript, Vite, PrimeReact, TanStack Query, Zustand |
| Data | SQLite (`chunk_meta`, chats) + FAISS index on disk |

## Project structure

```
avia-bot/
├── backend/
│   ├── app/
│   │   ├── api/routers/        # health, etl, chats
│   │   ├── services/           # ETLService, ChatService
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── schemas/            # chat, rag, llm DTOs
│   │   ├── rag/                # RAG pipeline
│   │   │   ├── pipeline.py
│   │   │   ├── retrieval.py    # FAISS + RRF fusion
│   │   │   └── methods/        # HyDE, Multi-Query, Query Rewriting, Rerank
│   │   ├── llm/                # chat, embeddings, prompts, guard
│   │   ├── core/               # config, faiss_manager, sse_manager
│   │   ├── db/
│   │   └── exceptions/
│   ├── etl/                    # markdown parser and chunker
│   ├── faiss/                  # faiss.index
│   ├── data/                   # SQLite, manifest, source document
│   ├── scripts/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                # layout, providers
│   │   ├── features/
│   │   │   ├── chats/          # chat list
│   │   │   ├── chat/           # dialog, composer
│   │   │   ├── rag/            # RAG settings
│   │   │   ├── llm/            # LLM parameters
│   │   │   └── trace/          # trace panel (RAG mode)
│   │   ├── shared/             # API, i18n
│   │   ├── theme/
│   │   └── styles/
│   └── package.json
├── Makefile
├── README.md
└── README_RU.md
```

### Backend (`backend/app/`)

Dependency flow: **API → Service → Repository → Model**.  
External integrations (LLM, FAISS, SSE) live in `llm/`, `core/`, and `rag/`.

| Directory | Purpose |
|-----------|---------|
| `api/routers/` | `/api/healthz`, `/api/etl/*`, `/api/chats/*` |
| `services/` | `ETLService`, `ChatService` |
| `rag/` | Modular RAG: query transform → FAISS → rerank → LLM context |
| `llm/` | Chat completions, embeddings, system prompts, prompt guard |
| `core/` | Config, logging, `faiss_manager`, `sse_manager` |

### Frontend (`frontend/src/`)

React + Vite SPA. In dev mode, requests to `/api` are proxied to the backend (`http://127.0.0.1:8000`).

| Directory | Purpose |
|-----------|---------|
| `features/chats/` | Chat list, create, delete (empty chats — no confirmation) |
| `features/chat/` | Dialog, send messages, markdown replies |
| `features/rag/` | RAG settings panel (HyDE, Multi-Query, Query Rewriting, Rerank, history) |
| `features/llm/` | LLM parameters panel (history, custom system prompt) |
| `features/trace/` | RAG pipeline trace (RAG mode) |
| `shared/api/` | HTTP client for `/api/chats/*` |

## LLM and RAG modes

The header switch sets the **UI mode** and chat type. Chat lists are separate per mode.

| Mode | Description | Right panel |
|------|-------------|-------------|
| **LLM** | Free-form LLM dialogue. Knowledge base is not used. Guards and aviation system prompt apply by default; **custom system prompt** disables guards. | **Parameters** |
| **RAG** | FAISS retrieval, optional retrieval methods, answer with knowledge-base context. | **Trace** (settings + pipeline steps) |

On send, the frontend passes current settings (`rag_config` / `llm_config`, `use_history`). The backend stores them on the chat and in user/assistant message metadata.

### RAG settings

| Setting | Group | Description |
|---------|-------|-------------|
| **HyDE** | Query transform (pick one) | LLM generates a hypothetical answer; search by its embedding |
| **Multi-Query** | Query transform | Several query variants → search each → fusion (RRF) |
| **Query Rewriting** | Query transform | Rewrite query using conversation history |
| **Rerank** | Independent | LLM reranking of top candidates after vector search |
| **Use chat history** | Shared | Affects LLM context and query rewriting |

HyDE, Multi-Query, and Query Rewriting are **mutually exclusive** (only one can be on in the UI). **Rerank** can be combined with any of them.

If no query transform is selected — direct vector search on the user question.

### LLM settings

| Setting | Description |
|---------|-------------|
| **Use chat history** | Whether to pass previous messages to the LLM (on by default) |
| **Custom system prompt** | Custom system prompt; guards disabled. Empty prompt = no system prompt |

### RAG pipeline (backend)

```
[HyDE | Multi-Query | Query Rewriting | direct query]
        → embed → FAISS search (top-30)
        → [optional Rerank → top-5]
        → context in system prompt → LLM → answer
```

Method classes: `backend/app/rag/methods/` (`HyDEQueryMethod`, `MultiQueryMethod`, `QueryRewritingMethod`, `LlmRerankMethod`). Orchestrator: `RagPipeline` in `rag/pipeline.py`.

Trace steps are published via SSE (`GET /api/chats/events?client_id=…`, event `trace`) and stored in `metadata.rag_trace` on the assistant message.

**Requirement:** build the index before using RAG (`make etl-ingest`). Without it, the API returns `503 rag_index_missing`.

## Prompt injection protection

Implemented in `backend/app/llm/` for **LLM** (default) and **RAG** modes:

| Layer | Module | What it does |
|-------|--------|--------------|
| System prompt | `prompts.py` | Aviation scope, refuse jailbreaks, do not reveal prompt or model |
| Message hardening | `prompt_guard.py` | `<<USER>>` / `<</USER>>` delimiters, sanitization |
| Pre-flight block | `ChatService` | Obvious injection/off-topic patterns — no LLM call |

**Not applied** when **custom system prompt** is enabled in LLM mode (free mode).

Unit tests: `backend/tests/unit/llm/test_prompt_guard.py`.

## Theme and language

Settings in the header, **persisted in `localStorage`**.

- **Theme:** system / light / dark (`theme/themes.json`)
- **Language:** Russian (default) / English (`shared/i18n/locales/`)

RAG method help texts: `rag-methods.ru.json` / `rag-methods.en.json`.

## ETL

1. **Parse** markdown → section tree
2. **Chunk** with content-type awareness
3. **Embeddings** via LLM provider
4. **Persist** to SQLite + FAISS

```bash
cp backend/.env.example backend/.env   # fill in LLM__*
make backend-install
make etl-ingest                        # required for RAG
make etl-stats
make etl-manifest
```

API: `POST /api/etl/ingest`, `GET /api/etl/stats`, `GET /api/etl/manifest`.

Default document: `backend/data/rag-document.md` (`ETL__DOCUMENT_PATH`).  
Details: [`backend/etl/README.md`](backend/etl/README.md).

| Path | Purpose |
|------|---------|
| `backend/data/app.db` | SQLite: chunks, manifest, chats |
| `backend/faiss/faiss.index` | FAISS index |
| `backend/data/manifest.json` | manifest copy for tooling |

## Chat API (summary)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chats?chat_type=rag\|llm` | List chats |
| POST | `/api/chats` | Create chat (with initial settings) |
| PATCH | `/api/chats/{id}` | Update `rag_config` / `llm_config` / `use_history` |
| POST | `/api/chats/{id}/messages` | Send message (+ settings in body) |
| GET | `/api/chats/events?client_id=…` | SSE: errors and trace |

## Quick start (dev)

Requirements: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node.js 20+.

```bash
# 1. Backend
cp backend/.env.example backend/.env
# LLM__BASE_URL, LLM__API_KEY, LLM__MODEL, LLM__EMBEDDING_MODEL
make backend-install
make etl-ingest                        # for RAG mode
make backend-dev                       # http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cp frontend/.env.example frontend/.env
make frontend-install
make frontend-dev                      # http://127.0.0.1:5173
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to the backend.

Full command list: `make help`.

## Current status

**Done:**
- Backend: ETL, FAISS, modular RAG pipeline, chat CRUD, LLM/RAG replies, settings in chat and metadata, SSE trace events
- Frontend: layout (chats · dialog · trace/parameters), RAG/LLM settings, settings sent with each message, i18n, theme

**In development:**
- Frontend SSE trace subscription (steps are in metadata today; Trace panel is a placeholder until EventSource is wired)
- Response streaming

**Planned:**
- Telegram bot, Docker, production build
