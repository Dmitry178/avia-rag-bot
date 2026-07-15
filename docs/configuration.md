# Configuration reference

**English** · [Русский](configuration_ru.md)

All backend settings are loaded via **pydantic-settings** from `backend/.env` and environment variables. Nested keys use double underscore (`__`) as delimiter.

Example: `LLM__BASE_URL` → `settings.llm.base_url`.

See also: [deployment.md](deployment.md), [architecture.md](architecture.md#configuration).

---

## Quick start

```bash
cp backend/.env.example backend/.env
# Edit LLM__BASE_URL, LLM__API_KEY, LLM__MODEL, LLM__EMBEDDING_MODEL
```

Frontend (optional): `cp frontend/.env.example frontend/.env` — only needed when overriding `VITE_API_URL`.

---

## Application (`APP__`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP__TITLE` | string | `Avia Bot API` | OpenAPI title |
| `APP__DESCRIPTION` | string | `RAG assistant for airport staff` | OpenAPI description |
| `APP__CORS_ORIGINS` | JSON array | `["http://localhost:5173"]` | Allowed browser origins |

**Docker:** `docker-compose.yml` overrides CORS to `http://localhost:8080`.

---

## Logging (`LOG__`)

| Variable | Type | Default | Values |
|----------|------|---------|--------|
| `LOG__NAME` | string | `avia-bot-api` | Logger name |
| `LOG__LEVEL` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `FATAL`, `CRITICAL` |
| `LOG__FORMAT` | string | `TEXT` | `TEXT`, `JSON` |

Use `LOG__FORMAT=JSON` in production for log aggregation.

---

## Database (`DB__`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DB__URL` | string | `sqlite:///./data/app.db` | SQLAlchemy URL; file paths are relative to `backend/` |

SQLite URLs are automatically converted to async (`sqlite+aiosqlite`) at runtime.

---

## Data directory (`DATA__`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATA__DIR` | string | `./data` | Runtime artifacts: SQLite, manifest JSON, ingest checkpoint |

Created on startup if missing.

---

## FAISS (`FAISS__`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FAISS__DIR` | string | `./data` | Directory for vector index file |
| `FAISS__INDEX_FILE` | string | `faiss.index` | Index filename inside `FAISS__DIR` |

---

## ETL (`ETL__`)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ETL__DOCUMENT_PATH` | string | `data/rag-document.md` | Knowledge base markdown (relative to `backend/` or absolute) |

Override per ingest via API `source_path` or CLI `--source`.

---

## LLM provider (`LLM__`)

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM__BASE_URL` | **Yes** (for chat/RAG/ETL) | OpenAI-compatible API base URL (e.g. `https://api.example/v1`) |
| `LLM__API_KEY` | Depends on provider | Bearer token; may be empty for local gateways |
| `LLM__MODEL` | **Yes** | Chat completion model (RAG answers, HyDE, rerank, titles) |
| `LLM__SUMMARIZATION_MODEL` | Optional | Reserved for future summarization; may match `LLM__MODEL` |
| `LLM__EMBEDDING_MODEL` | **Yes** (for ETL/RAG) | Embeddings model name |

**Important:** changing `LLM__EMBEDDING_MODEL` requires a full re-ingest (`rebuild=true`). The manifest stores the model used at build time; mismatch raises `etl_embedding_mismatch`.

---

## Telegram (`TELEGRAM__`) — planned

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TELEGRAM__BOT_TOKEN` | string | `""` | Bot token (not used in current MVP) |

See [telegram.md](telegram.md).

---

## Frontend (`VITE_*`)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `""` (empty) | API base URL; empty = relative `/api` (dev proxy / Docker Nginx) |

---

## Docker Compose overrides

`docker-compose.yml` sets:

```yaml
DATA__DIR: ./data
DB__URL: sqlite:///./data/app.db
FAISS__DIR: ./data
ETL__DOCUMENT_PATH: data/rag-document.md
APP__CORS_ORIGINS: '["http://localhost:8080","http://127.0.0.1:8080"]'
```

Host port: `FRONTEND_PORT` (default `8080`). Data bind-mount: `./backend/data:/app/data`.

---

## RAG tuning constants (code, not env)

These live in `backend/app/core/rag_constants.py` and require a code change to adjust:

| Constant | Default | Purpose |
|----------|---------|---------|
| `RETRIEVAL_TOP_K` | 30 | FAISS oversampling per search |
| `RERANK_TOP_N` | 5 | Candidates sent to LLM reranker |
| `MULTI_QUERY_COUNT` | 3 | Variants for Multi-Query |
| `DEFAULT_TOP_CHUNKS` | 5 | Chunks in generation context |
| `DECISION_TREE_MIN_SIMILARITY` | 0.30 | Threshold for decision-tree walkthrough |

Per-request overrides: `rag_config.top_chunks` (3–21) via API/UI.

---

## Related documentation

| Document | Content |
|----------|---------|
| [deployment.md](deployment.md) | Where to set variables per environment |
| [operations.md](operations.md) | ETL after config changes |
| [security.md](security.md) | Secrets handling |
