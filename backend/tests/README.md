# Backend tests

**English** · [Русский](README_RU.md)

Test suite for `avia-bot-backend`. Split into three areas:

| Layer | Directory | What it covers |
|-------|-----------|----------------|
| **API** (integration) | `tests/api/` | FastAPI HTTP endpoints via `httpx.AsyncClient` |
| **Unit** | `tests/unit/` | RAG client, LLM guards, chat services, SSE |
| **Parity** (opt-in) | `tests/parity/` | embed vs MCP on single `data/` volume |
| **Exceptions** | `tests/exceptions/` | DB/API error normalization helpers |

Stack: **pytest**, **pytest-asyncio** (`auto` mode), **httpx** (ASGI transport).

Currently **148 tests** across all areas (53 API).

## Directory layout

```
tests/
├── README.md
├── conftest.py
├── paths.py            # KB paths → repo-root data/
├── api/
│   ├── test_chat.py
│   ├── test_chat_events.py
│   └── test_health.py
├── parity/             # --run-parity
│   ├── compare.py
│   └── test_mcp_rag_parity.py
├── exceptions/
│   └── test_db_errors.py
└── unit/
    ├── core/
    ├── llm/
    ├── rag/
    │   └── test_client.py
    └── services/
```

ETL unit tests live in **`mcp-rag/tests/`**.

## Running tests

From the repository root (via Makefile):

```bash
make backend-test          # all tests
uv run pytest tests/api      # tests/api/ only
uv run pytest tests/unit     # tests/unit/ only
```

From `backend/`:

```bash
uv run pytest                    # all
uv run pytest tests/api          # API
uv run pytest tests/unit         # unit
uv run pytest tests/parity --run-parity -v   # embed vs MCP (needs indexes + LLM)
uv run pytest tests/api/test_chat.py -v   # single file
uv run pytest -k "soft_delete"   # by test name
```

Pytest configuration lives in `pyproject.toml` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`).

## Database isolation

Tests **do not use** the dev database `data/app.db`. Before the application is imported, `tests/conftest.py`:

1. sets `DB__URL` to a separate file `tests/.pytest_app.db`;
2. deletes it at the start of the session (if left over from a previous run);
3. asserts the async engine points at that file before any test runs;
4. disposes the engine and deletes the file after all tests finish.

This applies to both API integration tests and unit tests that open a database session (for example `tests/unit/services/test_chat_title_service.py`).

The database engine is created lazily on first use, so `DB__URL` must be set before importing `app.db.session`. Pytest loads `tests/conftest.py` first; ad-hoc scripts and one-off `python -c` snippets do not — set `DB__URL` manually or run code through pytest.

This matters: previously tests wrote to `data/app.db`, and after `make backend-test` / `uv run pytest` stray chats appeared in the dev environment (`Test chat`, `Empty`, `LLM chat`, etc.).

The file `tests/.pytest_app.db` is listed in `.gitignore`.

## Parity tests (`tests/parity/`)

Opt-in integration suite comparing **embed** (in-process `src.rag`) vs **mcp stdio** (`mcp-rag` subprocess). Both use repo-root **`data/`** (`kb.db` + FAISS). Marked `@pytest.mark.parity`; skipped unless `--run-parity` is passed.

**Prerequisites:**

- `faiss-ru.index` / `faiss-en.index` in repo-root `data/`
- `data/kb.db` with `index_manifest` + chunks (after `make etl-ingest`)
- `LLM__BASE_URL`, `LLM__EMBEDDING_MODEL` (and API key if required) in `backend/.env`
- `uv` on PATH (MCP client spawns `uv run python -m src.server` in `mcp-rag/`)

```bash
cd backend
uv run pytest tests/parity --run-parity -v
```

**Checks:** manifest `doc_hash` / `chunk_count` (ru, en); retrieval chunk ids, similarities (±0.0001), context, trace step names for fixed queries.

## API tests (`tests/api/`)

Boot the full application (`app.main:app`) with lifespan initialization (table creation, dependencies). Requests go through in-process ASGI — no separate server required.

### Shared fixture

`api/conftest.py` — async `client` fixture:

- starts `lifespan(app)`;
- yields `httpx.AsyncClient` with `ASGITransport`;
- base URL: `http://test`.

### Coverage

See also the **API test coverage** table in [docs/api.md](../docs/api.md) (EN) / [docs/api_ru.md](../docs/api_ru.md) (RU).

| File | Endpoints | Tests |
|------|-----------|-------|
| `test_health.py` | `GET /api/healthz`, `GET /api/readyz` | ok status, JSON content-type, method validation; readiness `503` when DB unreachable (mocked) |
| `test_chat_events.py` | `GET /api/chats/events` | missing/empty `client_id` → 422; handler returns `EventSourceResponse` |
| `test_chat.py` | chat CRUD, messages, close, edit, rating | create, list, filter by `chat_type`; settings on create/PATCH; get/delete 404; close chat + idempotent close; edit user/assistant/missing message; rate assistant/user/missing; send messages (mocked LLM/RAG); guards, titles, idempotency |

Message tests patch external I/O (`ChatCompletionClient.complete`, `RagPipeline`) so no LLM or FAISS index is required.

## Unit tests (`tests/unit/`)

Call functions and classes directly, without the HTTP layer. ETL chunker/plan tests moved to **`mcp-rag/tests/unit/`**.

Notable modules:

| Path | Focus |
|------|-------|
| `unit/rag/test_client.py` | `EmbedRagClient`, `McpRagClient`, factory |
| `unit/llm/test_prompt_guard.py` | injection / off-topic guards |
| `unit/services/test_rag_metadata_enrichment.py` | trace enrichment via `kb_access` |
| `unit/services/test_chat_title_service.py` | background title persistence |

## Exception tests (`tests/exceptions/`)

Pure helpers without HTTP or DB.

### `exceptions/test_db_errors.py`

| Test | Assertion |
|------|-----------|
| `test_map_exception_preserves_httpx_message` | `httpx` errors → `ServiceError` with 502 |
| `test_map_exception_preserves_value_error_message` | `ValueError` → `internal_error` |
| `test_map_exception_preserves_existing_service_error_detail` | existing `ServiceError` passed through unchanged |

## Shared modules

### `paths.py`

Path constants for test data:

- `KB_DATA_DIR` — repo-root `data/` (markdown, FAISS, `kb.db`);
- `RAG_DOCUMENT` — `data/rag-document-ru.md`.

Use when adding unit tests that need files from disk.

## Conventions

1. **File naming** — `test_<module>.py`; functions — `test_<behavior>`.
2. **Docstrings** — in English, briefly describe expected behavior (see existing tests).
3. **API tests** — only in `tests/api/`; HTTP fixtures in `tests/api/conftest.py`; DB isolation in the root `tests/conftest.py`.
4. **Unit tests** — mirror backend layout; ETL tests belong in `mcp-rag/tests/`.
5. **New API routers** — add `tests/api/test_<router>.py` with **2–3 tests per endpoint**; see `.cursor/rules/backend-api-tests.mdc`; do not mix with unit tests.
6. **Async** — mark API tests with `@pytest.mark.asyncio` (or rely on `asyncio_mode = "auto"`).
7. **External I/O in API tests** — patch LLM, RAG, and FAISS at the service boundary (`unittest.mock.patch`) so tests stay fast and offline.

## Planned additions

As the project grows:

- `tests/unit/services/test_chat.py` — chat service with mocked repositories;
- `tests/api/test_rag.py` — dedicated RAG endpoint tests when exposed separately.

## Pytest markers

`pyproject.toml` registers `api` and `unit` markers — tag tests and filter when needed:

```bash
uv run pytest -m api
uv run pytest -m unit
```

Markers are not applied to tests yet; directory layout is enough for Makefile targets.
