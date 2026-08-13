# Configuration reference

**English** · [Русский](configuration_ru.md)

Backend settings: **pydantic-settings** from `backend/.env` (`app/core/config.py`).  
KB / indexing settings: **`mcp-rag/.env`** (`mcp-rag/src/core/config.py`).  
Nested keys use `__` (e.g. `LLM__BASE_URL`).

See also: [deployment.md](deployment.md), [ARCHITECTURE.md](ARCHITECTURE.md#data-volumes).

---

## Quick start

```bash
cp backend/.env.example backend/.env
# LLM__BASE_URL, LLM__API_KEY, LLM__MODEL, LLM__EMBEDDING_MODEL

cp backend/.env mcp-rag/.env   # same LLM vars for ingest + RAG
make etl-ingest                # builds data/kb.db + FAISS in repo-root data/
```

Frontend (optional): `cp frontend/.env.example frontend/.env`.

---

## Data volumes (after stage 9)

| Volume | Owner | Contents |
|--------|-------|----------|
| **`data/`** (repo root) | **mcp-rag** | KB sources (git), `kb.db`, FAISS, manifest JSON, ingest checkpoints |
| **`backend/data/`** | **backend** | **`app.db` only** — `Chat`, `ChatMessage` |

Both `runtime=embed` and `runtime=mcp` read KB artifacts from **`data/`** (`data/kb.db` + `data/faiss-*.index`).

```
runtime=embed  →  backend/data/app.db  +  data/kb.db  +  data/faiss-*
runtime=mcp    →                        data/kb.db  +  data/faiss-*
```

---

## Backend application (`APP__`, `LOG__`)

| Prefix | Examples |
|--------|----------|
| `APP__` | `TITLE`, `DESCRIPTION`, `CORS_ORIGINS` |
| `LOG__` | `NAME`, `LEVEL`, `FORMAT` |

Docker overrides CORS to `http://localhost:8080` — see [deployment.md](deployment.md).

---

## Backend database (`DB__`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB__URL` | `sqlite:///./data/app.db` | Chat DB only; path relative to `backend/` |

SQLite → `sqlite+aiosqlite` at runtime. **No** KB tables in this file.

---

## LLM provider (`LLM__`) — backend + mcp-rag

Set in **both** `backend/.env` and `mcp-rag/.env` (or shared copy):

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM__BASE_URL` | Yes | OpenAI-compatible API |
| `LLM__API_KEY` | Provider-dependent | Bearer token |
| `LLM__MODEL` | Yes | Chat (RAG answers, HyDE, rerank, titles) |
| `LLM__EMBEDDING_MODEL` | Yes (ETL/RAG) | Embeddings |

Changing `LLM__EMBEDDING_MODEL` requires full re-ingest (`REBUILD=1` / `rebuild=true`). Manifest stores the model used at build time.

---

## Knowledge-base languages (code, not env)

Defined in **`mcp-rag/src/core/config.py`** → `KB_LANGUAGES` (paths relative to **repo root**):

| Code | Document | Schema |
|------|----------|--------|
| `ru` | `data/rag-document-ru.md` | `data/chunking-schema-ru.json` |
| `en` | `data/rag-document-en.md` | `data/chunking-schema-en.json` |

Schema contract: [etl_chunking_schema_spec.md](etl_chunking_schema_spec.md).

Per-request markdown override: CLI `--source` on `ingest-schema` (no HTTP ETL API on backend).

---

## mcp-rag / KB database (`MCP_RAG__`)

Used by `mcp-rag` CLI, MCP tools, and embed in-process RAG.

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_RAG__SCHEMAS_DIR` | `../data` | KB volume; relative to `mcp-rag/` cwd |
| `MCP_RAG__LANGUAGE` | `en` | Default KB language; UI syncs RU/EN header |
| `MCP_RAG__DB__URL` | `sqlite:///./data/kb.db` | KB SQLite (`data/kb.db` under repo root) |

Prefer **`MCP_RAG__DB__URL`** (or `MCP_RAG__DB_URL`) over bare `DB__URL` in shared Docker/env files so it does not clash with backend chat `DB__URL`. Legacy `DB__URL` in `mcp-rag/.env` still works for local-only setups.

MCP subprocess JSON (UI): `python -m src.server`, `cwd: ../mcp-rag`, env `MCP_RAG__SCHEMAS_DIR=../data`.

---

## Embed runtime dependency

Backend optional extra **`rag`** installs editable **`mcp-rag`** (`backend/pyproject.toml`):

```bash
cd backend && uv sync --extra rag   # full RAG (embed + dev)
cd backend && uv sync               # thin backend (chat API; runtime=mcp)
```

Dev dependency group includes `mcp-rag` by default for local work (`uv sync` in backend).

`runtime=embed` lazy-imports `src.rag` — requires the `rag` extra (or dev group). Missing package → HTTP **503** `rag_embed_not_installed`.

`runtime=mcp` spawns subprocess only; core backend imports do not require `mcp-rag`.

---

## Indexing commands (not backend HTTP)

| Command | Description |
|---------|-------------|
| `make etl-ingest` | All schemas → `data/kb.db` + FAISS (delegates to `mcp-rag/`) |
| `make -C mcp-rag etl-ingest` | Same, from mcp-rag Makefile |
| `make etl-stats` / `etl-manifest` | CLI via mcp-rag |

MCP tools: `ingest_schema`, `ingest_all`, `stats`, `index_status`.

---

## Frontend (`VITE_*`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `""` | Empty = relative `/api` |

---

## Docker Compose

Compose mounts two host directories:

| Host | Container | Purpose |
|------|-----------|---------|
| `./backend/data` | `/app/data` | Chat SQLite (`app.db`) |
| `./data` | `/data` | KB (`kb.db`, FAISS, markdown, schemas) |

Backend image includes `mcp-rag` at `/mcp-rag`. Do **not** set a single `DB__URL` in Compose for both apps — backend defaults to `app.db`; mcp-rag loads `kb.db` from `mcp-rag/.env` or defaults.

Ingest inside a running stack: `make docker-etl-ingest`. See [deployment.md](deployment.md).

---

## Parity tests

```bash
cd backend
# After: make etl-ingest, LLM__* in .env, data/kb.db + faiss-*.index present
uv run pytest tests/parity --run-parity -v
```

Single KB volume; compares embed in-process vs MCP stdio. Skipped in default CI without `--run-parity`.

---

## RAG tuning constants (code)

In **`mcp-rag/src/core/rag_constants.py`**:

| Constant | Default | Purpose |
|----------|---------|---------|
| `RETRIEVAL_TOP_K` | 30 | FAISS oversampling |
| `RERANK_TOP_N` | 5 | Rerank candidates |
| `MULTI_QUERY_COUNT` | 3 | Multi-query variants |
| `DEFAULT_TOP_CHUNKS` | 5 | Context size |
| `DECISION_TREE_MIN_SIMILARITY` | 0.30 | Decision-tree threshold |

Per-request: `rag_config.top_chunks` (3–21) via API/UI.

---

## Related documentation

| Document | Content |
|----------|---------|
| [operations.md](operations.md) | ETL, backups, troubleshooting |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Component diagram |
| [mcp_rag_migration_agent.md](../_/mcp_rag_migration_agent.md) | Migration playbook |
