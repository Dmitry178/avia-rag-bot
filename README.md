# AI Airport Staff Assistant

**English** · [Русский](README_RU.md)

Educational project — a RAG bot for airport staff: answers questions from an internal knowledge base (SOP, FAQ, scenarios, decision trees). The UI lets you chat with the assistant, manage conversations, and (in RAG mode) watch the pipeline trace.

Monorepo: **backend** (FastAPI, indexing, chat API) + **frontend** (React SPA). Telegram and Docker are planned for later stages.

## What the app does

- **Knowledge base indexing** — a markdown document is split into chunks; embeddings are built for each and stored in SQLite + FAISS.
- **Chats** — create, select, close, and delete conversations; message history is stored on the backend.
- **Two operating modes** (switched in the header):
  - **LLM** — direct dialogue with the language model, no knowledge base search. **Works now.**
  - **RAG** — answers grounded in indexed documents plus a trace panel. **In development** (UI ready, backend retrieval not wired yet).
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
├── backend/                    # API and business logic
│   ├── app/                    # FastAPI application
│   │   ├── api/routers/        # HTTP routes (health, etl, chats)
│   │   ├── services/           # use cases (ETLService, ChatService)
│   │   ├── repositories/       # SQLite access
│   │   ├── models/             # SQLModel tables
│   │   ├── schemas/            # Pydantic DTOs for API
│   │   ├── llm/                # chat completions and embeddings clients
│   │   ├── core/               # config, logging, faiss_manager, sse_manager
│   │   ├── db/                 # sessions, DBManager, init
│   │   └── exceptions/         # error handling
│   ├── etl/                    # markdown parser and chunker (no I/O)
│   ├── faiss/                  # vector index artifact (faiss.index)
│   ├── data/                   # SQLite, manifest.json, source document
│   ├── scripts/                # ETL CLI
│   └── tests/                  # API and unit tests
├── frontend/                   # web UI (React SPA)
│   ├── src/
│   │   ├── app/                # app root, layout, providers
│   │   ├── features/
│   │   │   ├── chats/          # chat list sidebar
│   │   │   ├── chat/           # dialog, composer, LLM/RAG mode
│   │   │   └── trace/          # RAG trace panel (placeholder)
│   │   ├── shared/             # API client, i18n, persist, utilities
│   │   ├── theme/              # light/dark theme, CSS variables
│   │   └── styles/             # global styles
│   ├── index.html
│   ├── vite.config.ts          # dev proxy /api → backend :8000
│   └── package.json
├── Makefile                    # commands for backend, frontend, and ETL
├── README.md
└── README_RU.md
```

### Backend (`backend/app/`)

Dependency flow: **API → Service → Repository → Model**.  
External integrations (LLM, FAISS, SSE) live in `llm/` and `core/`, not directly in services.

| Directory | Purpose |
|-----------|---------|
| `api/routers/` | HTTP routes: `/api/healthz`, `/api/etl/*`, `/api/chats/*` |
| `services/` | Use cases: `ETLService`, `ChatService` |
| `repositories/` | CRUD and SQLite queries |
| `models/` | SQLModel tables (`ChunkMeta`, `Chat`, `ChatMessage`, …) |
| `llm/` | Chat completions and embeddings via OpenAI-compatible API |
| `core/` | Config, logging, `faiss_manager`, `sse_manager` |

### Frontend (`frontend/src/`)

React + Vite SPA. In dev mode, requests to `/api` are proxied to the backend (`http://127.0.0.1:8000`).

| Directory | Purpose |
|-----------|---------|
| `app/` | `AppLayout` — three-column layout; `AppHeader` — mode, language, and theme switches |
| `features/chats/` | Chat list, create new, select active |
| `features/chat/` | Dialog panel, send messages, markdown-rendered replies |
| `features/trace/` | RAG pipeline trace panel (shown only in RAG mode) |
| `shared/api/` | HTTP client and types for `/api/chats/*` |
| `shared/i18n/` | `ru` / `en` translations, persisted locale |
| `theme/` | Color tokens (`themes.json`), CSS variable application |

## LLM and RAG modes

The header switch sets the **UI mode**. The choice is stored in `localStorage`.

| Mode | Description | Status |
|------|-------------|--------|
| **LLM** | Free-form dialogue with the language model. The backend sends chat history to the chat completions API and returns the reply. The knowledge base is not used. | Working |
| **RAG** | Airport procedure questions with FAISS chunk retrieval, routing, and guard checks. A **Trace** panel on the right shows pipeline steps and timings. | In development |

Currently the backend always responds via a simple LLM call (`ChatService.send_message`), regardless of the mode selected in the UI. RAG mode in the interface is prepared in advance: layout, trace placeholder, and copy are ready for retrieval and SSE integration.

## Theme and language

Settings are in the header and **persist across reloads** (`localStorage` via Zustand persist).

**Theme** (`theme/`):
- **System** — follows browser/OS `prefers-color-scheme`.
- **Light** / **Dark** — fixed palette from `themes.json`, CSS variables on `:root`.

**UI language** (`shared/i18n/`):
- **Russian** (default) and **English**.
- Strings in `locales/ru.json` and `locales/en.json`; the document `lang` attribute updates when the language changes.

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

More on document format and chunking: [`backend/etl/README.md`](backend/etl/README.md).

Artifacts after ingest:

| Path | Purpose |
|------|---------|
| `backend/data/app.db` | SQLite: chunks, manifest, chats |
| `backend/faiss/faiss.index` | FAISS index |
| `backend/data/manifest.json` | manifest copy for tooling |

## Quick start (dev)

Requirements: Python 3.13 + [uv](https://docs.astral.sh/uv/), Node.js 20+.

```bash
# 1. Backend
cp backend/.env.example backend/.env   # set LLM__BASE_URL, LLM__API_KEY, LLM__MODEL
make backend-install
make backend-dev                       # http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cp frontend/.env.example frontend/.env # change VITE_API_URL if needed
make frontend-install
make frontend-dev                      # http://127.0.0.1:5173
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to the backend.

Optional — rebuild the index before using RAG mode (once retrieval is connected):

```bash
make etl-ingest
```

Full command list: `make help`.

## Current status

**Done:**
- Backend: health-check, ETL, FAISS indexing, chat CRUD, synchronous LLM replies
- Frontend: layout (chats · dialog · trace), send messages, markdown replies, LLM/RAG switches, theme, i18n

**In development:**
- RAG retrieval on the backend (FAISS search, router/guard, streaming)
- Wiring trace to SSE and populating the Trace panel in the UI

**Planned:**
- Telegram bot, Docker, production build
