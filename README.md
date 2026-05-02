# AI Airport Staff Assistant

**English** · [Русский](README_RU.md)

Educational RAG bot for airport staff: answers questions from an internal knowledge base (SOP, FAQ, scenarios, decision trees).  
Monorepo: backend (FastAPI) + web UI (React, in development). Telegram and Docker are planned for later stages.

## Stack

| Part | Technologies |
|------|--------------|
| Backend | Python 3.13, FastAPI, SQLModel, SQLite, FAISS, uv |
| LLM | OpenAI-compatible API (chat + embeddings) |
| Frontend | React, TypeScript, Vite, PrimeReact |
| Data | SQLite (`chunk_meta`, chats) + FAISS index on disk |

## Project structure

```
avia-bot/
├── backend/          # API and business logic
│   ├── app/          # FastAPI app (api → services → repositories)
│   ├── etl/          # markdown parser and chunker (no I/O)
│   ├── faiss/        # vector index artifact directory (faiss.index)
│   ├── data/         # SQLite, manifest.json, source document
│   └── scripts/      # ETL CLI
├── frontend/         # web UI — in development, not in the repo yet
├── Makefile          # commands for backend, frontend, and ETL
├── README.md
└── README_RU.md
```

### Backend (`backend/app/`)

- **`api/`** — HTTP routes (`/api/healthz`, `/api/etl/*`, `/api/chats/*`)
- **`services/`** — use cases (`ETLService`, `ChatService`)
- **`repositories/`** — SQLite access
- **`models/`** — SQLModel tables
- **`llm/`** — chat completions and embeddings clients
- **`core/`** — config, logging, `faiss_manager`, `sse_manager`

Dependency flow: **API → Service → Repository → Model**.  
External integrations (LLM, FAISS, SSE) live in `llm/` and `core/`, not directly in services.

### Frontend

**Status: in development.** The `frontend/` directory.

Planned SPA on React + Vite: `/api` proxy → backend `:8000`, light/dark themes, i18n (ru/en), three-column layout (chats, dialog, trace).

## ETL

Knowledge base indexing pipeline:

1. **Parse** markdown → section tree (`etl/parser.py`)
2. **Chunk** with content-type awareness (`etl/chunker.py`)
3. **Embeddings** via LLM provider
4. **Persist** metadata in SQLite + vectors in FAISS

Run from the repository root:

```bash
cp backend/.env.example backend/.env   # fill in LLM__*
make backend-install
make etl-ingest                        # full index rebuild
make etl-stats                         # chunk statistics
make etl-manifest                      # latest manifest
```

The same pipeline is available via API: `POST /api/etl/ingest`, `GET /api/etl/stats`, `GET /api/etl/manifest`.

Default source document: `backend/data/rag-document.md` (env var `ETL__DOCUMENT_PATH`).

Artifacts after ingest:

| Path | Purpose |
|------|---------|
| `backend/data/app.db` | SQLite: chunks, manifest, chats |
| `backend/faiss/faiss.index` | FAISS index |
| `backend/data/manifest.json` | manifest copy for tooling |

## Quick start (dev)

```bash
# Backend
cp backend/.env.example backend/.env
make backend-install
make backend-dev          # http://127.0.0.1:8000
```

Frontend — in development.

Full command list: `make help`.

## Current status

**Done (backend, in the repository):**
- health-check, ETL, indexing, chat API (synchronous LLM)

**In development:**
- web UI (`frontend/`): chats, dialog, trace panel

**Planned:**
- RAG retrieval, router/guard, streaming, Telegram, Docker
