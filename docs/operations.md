# Operations guide

**English** · [Русский](operations_ru.md)

Day-2 operations for **avia-bot**: knowledge base maintenance, backups, health checks, and troubleshooting. For initial setup see [deployment.md](deployment.md).

---

## Health endpoints

| Endpoint | Purpose | Healthy response |
|----------|---------|------------------|
| `GET /api/healthz` | Liveness — process is up | `200` |
| `GET /api/readyz` | Readiness — DB reachable | `200` when DB OK |

Docker backend service uses `healthz` in its healthcheck.

---

## ETL operations

### Commands

| Command | Description |
|---------|-------------|
| `make etl-ingest` | Incremental ingest — all schemas in `backend/data` (`ru` + `en` by default) |
| `make etl-stats` | Chunk counts by `content_type` (optional `LANG=ru\|en`) |
| `make etl-manifest` | Latest index manifest (optional `LANG=ru\|en`) |

Custom schema directory: `ETL_SCHEMAS_DIR=path make etl-ingest` (uses `ingest-dir`).

Docker: `make docker-etl-ingest` indexes all schemas in `backend/data`.

### API equivalents

| Method | Path |
|--------|------|
| `POST` | `/api/etl/ingest` — body: `{ "schema_path": "data/chunking-schema-ru.json", "rebuild": false }` |
| `POST` | `/api/etl/ingest-all` — body: `{ "rebuild": false }` |
| `GET` | `/api/etl/stats` — optional `?language_code=ru` |
| `GET` | `/api/etl/manifest` — `?language_code=ru` |

### Knowledge-base languages

Supported languages are **hardcoded** in `backend/app/core/config.py` (`KB_LANGUAGES`, not stored in the database):

| Code | Document | UI label |
|------|----------|----------|
| `ru` | `backend/data/rag-document-ru.md` | Русский |
| `en` | `backend/data/rag-document-en.md` | English |

Chats, chunks, and manifests use `language_code` column values `ru` or `en`. To change paths, edit `KB_LANGUAGES` in `config.py` and re-run ingest.

### On-disk artifacts

| File | Purpose |
|------|---------|
| `backend/data/app.db` | SQLite (chunks, chats, manifests) |
| `backend/data/faiss-ru.index` | FAISS vectors (Russian KB) |
| `backend/data/faiss-en.index` | FAISS vectors (English KB) |
| `backend/data/manifest-ru.json` | Latest Russian build metadata |
| `backend/data/manifest-en.json` | Latest English build metadata |
| `backend/data/ingest_checkpoint_{lang}.json` | Checkpoint resume (transient; see below) |
| `backend/data/ingest_checkpoint_{lang}.tmp` | Temp file while writing checkpoint (transient) |

Chunk `id` in SQLite must match FAISS row index per language — both are rebuilt together on full ingest.

### When to re-ingest

| Trigger | Action |
|---------|--------|
| KB content changed | `make etl-ingest` (incremental) |
| Embedding model changed | same targets with `REBUILD=1` |
| FAISS/DB corruption suspected | Stop backend → backup `backend/data/` → full rebuild |
| Interrupted ingest | Re-run same command — checkpoint resumes |

### Ingest checkpoint (transient)

During embedding, ETL writes **resume state** so a long ingest can continue after a failure or `Ctrl+C` without re-calling the embeddings API for batches already completed.

| File | Purpose | Lifetime |
|------|---------|----------|
| `ingest_checkpoint_{lang}.json` | Partial run state: `doc_hash`, embedding model, `vectors_by_hash` (content hash → vector) | **Transient** — removed when ingest succeeds |
| `ingest_checkpoint_{lang}.tmp` | Atomic-write temp while saving the checkpoint JSON | Removed with the checkpoint (or on successful cleanup) |
| `faiss-{lang}.index.tmp` | Atomic-write temp while saving the FAISS index | Replaced on successful FAISS save; orphan safe to delete if no ingest is running |

Per language: `ingest_checkpoint_ru.json`, `ingest_checkpoint_en.json`. Updated after each embedding batch.

**On successful completion** (`ETLService.ingest_schema`, `scripts/run_etl.py ingest-schema` / `ingest-dir`):

1. SQLite + FAISS + manifest are persisted.
2. Checkpoint files for the finished language(s) are **deleted automatically** (service layer + CLI safety pass).

**If ingest was interrupted** (exit code `130`, API error mid-embed, process killed):

- Checkpoint **remains on disk** — re-run the **same** command (`make etl-ingest`, etc.); compatible checkpoints are resumed.
- Do **not** delete the checkpoint manually unless you intend to restart embedding from scratch.

Files are listed in `backend/data/.gitignore` — not committed to git.

On `Ctrl+C`, the CLI prints resume instructions (`exit code 130`).

---

## Backups

### What to back up

Minimum for RAG recovery:

```
backend/data/app.db
backend/data/faiss-ru.index
backend/data/faiss-en.index
backend/data/manifest-ru.json
backend/data/manifest-en.json
backend/data/rag-document-ru.md
backend/data/rag-document-en.md
```

### Suggested procedure

1. Stop backend (or ensure no ingest in progress).
2. Copy entire `backend/data/` directory with timestamp.
3. Store `.env` secrets separately (not in git).

### Restore

1. Stop backend.
2. Replace `backend/data/` from backup.
3. Verify `manifest.json` `embedding_model` matches current `LLM__EMBEDDING_MODEL`.
4. Start backend; run `make etl-stats`.

---

## Logging

| Setting | Recommendation |
|---------|----------------|
| `LOG__LEVEL=INFO` | Default production |
| `LOG__FORMAT=JSON` | Structured logs for aggregation |
| `LOG__LEVEL=DEBUG` | Short-term troubleshooting only |

Key log events: `etl_ingest_*`, `sse_subscribed`, `llm_api_error`, `rag_index_missing`.

---

## Monitoring checklist

| Signal | How to check |
|--------|--------------|
| API up | `/api/healthz` |
| DB ready | `/api/readyz` |
| Index present | `/api/etl/manifest` or `make etl-manifest` |
| Chunk distribution | `make etl-stats` |
| LLM connectivity | Send test message in LLM mode |
| RAG pipeline | Send test message in RAG mode; inspect trace panel |

---

## Troubleshooting

### `503 rag_index_missing`

**Cause:** FAISS index or manifest not found.

**Fix:** Run `make etl-ingest` (or the language-specific target). Verify `backend/data/faiss-ru.index` and `faiss-en.index` exist.

### `503 rag_chunks_missing`

**Cause:** FAISS index exists but `chunk_meta` table is empty or out of sync.

**Fix:** Full re-ingest with `rebuild=true`.

### `etl_embedding_mismatch`

**Cause:** `LLM__EMBEDDING_MODEL` differs from manifest.

**Fix:** Re-ingest with `rebuild=true`, or revert model config to match manifest.

### `embedding_api_error` / `llm_api_error`

**Cause:** External LLM API failure, timeout, or misconfiguration.

**Fix:** Verify `LLM__BASE_URL`, `LLM__API_KEY`, model names. Check provider status and quotas.

### `etl_source_not_found`

**Cause:** `KB_LANGUAGES` path or ingest `source_path` points to missing file.

**Fix:** Verify path relative to `backend/` or use absolute path.

### Slow RAG responses

**Causes:** Multiple LLM calls (HyDE + rerank + decision tree), large `top_chunks`, slow provider.

**Mitigations:** Disable optional methods for baseline; reduce `top_chunks`; use faster models for pilot.

### SSE trace not appearing

**Causes:** `client_id` mismatch between SSE subscription and `POST /messages`; connection dropped.

**Fix:** Frontend opens SSE before send; same `client_id` in request body. Check browser network tab for `/api/chats/events`.

### Docker: frontend loads but API fails

**Causes:** Backend unhealthy; missing `.env`; CORS (rare in Docker same-origin).

**Fix:** `make docker-logs`; check backend healthcheck; verify root `.env`.

---

## Capacity notes (MVP)

| Resource | Typical demo load |
|----------|-------------------|
| SQLite | Single writer; fine for pilot < 100 concurrent users |
| FAISS | In-process CPU search; latency grows with index size |
| SSE | In-memory per process; one backend instance |

For production scale see [roadmap.md](roadmap.md) and ADR [001](adr/001-sqlite-faiss-on-disk.md).

---

## Related documentation

| Document | Content |
|----------|---------|
| [knowledge_base.md](knowledge_base.md) | KB authoring |
| [configuration.md](configuration.md) | Env variables |
| [operations.md](operations.md) | This document |
