# Backend tests

**English** · [Русский](README_RU.md)

Test suite for `avia-bot-backend`. Split into two layers:

| Layer | Directory | What it covers |
|-------|-----------|----------------|
| **API** (integration) | `tests/api/` | FastAPI HTTP endpoints via `httpx.AsyncClient` |
| **Unit** | `tests/unit/` | Business logic without HTTP: parsers, chunkers, services, etc. |

Stack: **pytest**, **pytest-asyncio** (`auto` mode), **httpx** (ASGI transport).

## Directory layout

```
tests/
├── README.md           # this file
├── README_RU.md        # Russian version
├── conftest.py         # DB isolation for API tests (see below)
├── paths.py            # shared paths to test data
├── api/
│   ├── conftest.py     # client fixture (lifespan + AsyncClient)
│   ├── test_chat.py    # chat CRUD
│   ├── test_etl.py     # ETL endpoints
│   └── test_health.py  # healthz / readyz
└── unit/
    └── etl/
        └── test_chunker.py   # parser + chunker
```

## Running tests

From the repository root (via Makefile):

```bash
make backend-test          # all tests
make backend-test-api      # tests/api/ only
make backend-test-unit     # tests/unit/ only
```

From `backend/`:

```bash
uv run pytest                    # all
uv run pytest tests/api          # API
uv run pytest tests/unit         # unit
uv run pytest tests/api/test_chat.py -v   # single file
uv run pytest -k "soft_delete"   # by test name
```

Pytest configuration lives in `pyproject.toml` (`testpaths = ["tests"]`, `asyncio_mode = "auto"`).

## Database isolation

API tests **do not use** the dev database `data/app.db`. Before the application is imported, `tests/conftest.py`:

1. sets `DB__URL` to a separate file `tests/.pytest_app.db`;
2. deletes it at the start of the session (if left over from a previous run);
3. deletes it after all tests finish.

This matters: previously API tests wrote to `data/app.db`, and after `make backend-test` / `uv run pytest` stray chats appeared in the dev environment (`Test chat`, `Empty`, `LLM chat`, etc.).

Unit tests do not touch the database — `conftest.py` only affects the API layer that boots `app.main:app`.

The file `tests/.pytest_app.db` is listed in `.gitignore`.

## API tests (`tests/api/`)

Boot the full application (`app.main:app`) with lifespan initialization (table creation, dependencies). Requests go through in-process ASGI — no separate server required.

### Shared fixture

`api/conftest.py` — async `client` fixture:

- starts `lifespan(app)`;
- yields `httpx.AsyncClient` with `ASGITransport`;
- base URL: `http://test`.

### Coverage

| File | Endpoints | Tests |
|------|-----------|-------|
| `test_health.py` | `GET /api/healthz`, `GET /api/readyz` | liveness and readiness return `{"status": "ok"}` |
| `test_chat.py` | `POST/GET/DELETE /api/chats` | create and list; `chat_type` field (`llm` by default); filter `GET /api/chats?chat_type=llm\|rag`; new chat detail with empty messages; soft-delete → 404 |
| `test_etl.py` | `GET /api/etl/stats`, `GET /api/etl/manifest` | chunk statistics; manifest without index → 404 |

## Unit tests (`tests/unit/`)

Call functions and classes directly, without the HTTP layer. Fast; no FastAPI startup required.

### `unit/etl/test_chunker.py`

Exercises the RAG document parsing pipeline (`etl/parser.py`, `etl/chunker.py`) against the real file `backend/data/rag-document.md`:

| Test | Assertion |
|------|-----------|
| `test_parse_markdown_finds_all_main_sections` | parser finds intro, FAQ, and glossary sections |
| `test_chunk_document_produces_expected_types` | chunker emits SOP, FAQ, GLOSSARY, DECISION_TREE, SCENARIO; ≥ 200 chunks |
| `test_chunks_have_retrieval_prefix` | every chunk has `[Раздел:` and `[Тип:` prefixes |

## Shared modules

### `paths.py`

Path constants for test data:

- `BACKEND_ROOT` — `backend/` root;
- `RAG_DOCUMENT` — `backend/data/rag-document.md`.

Use when adding unit tests that need files from disk.

## Conventions

1. **File naming** — `test_<module>.py`; functions — `test_<behavior>`.
2. **Docstrings** — in English, briefly describe expected behavior (see existing tests).
3. **API tests** — only in `tests/api/`; HTTP fixtures in `tests/api/conftest.py`; DB isolation in the root `tests/conftest.py`.
4. **Unit tests** — mirror code layout: `app/services/chat.py` → `tests/unit/services/test_chat.py`, `etl/parser.py` → `tests/unit/etl/test_parser.py`.
5. **New API routers** — add `tests/api/test_<router>.py`; do not mix with unit tests.
6. **Async** — mark API tests with `@pytest.mark.asyncio` (or rely on `asyncio_mode = "auto"`).

## Planned additions

As the project grows:

- `tests/unit/services/` — service layer (mocked repositories);
- `tests/unit/etl/test_parser.py` — parser edge cases on synthetic markdown;
- `tests/api/test_chat_message.py` — message sending and RAG replies when the endpoint is ready.

## Pytest markers

`pyproject.toml` registers `api` and `unit` markers — tag tests and filter when needed:

```bash
uv run pytest -m api
uv run pytest -m unit
```

Markers are not applied to tests yet; directory layout is enough for Makefile targets.
