# Backend tests

**English** · [Русский](README_RU.md)

Test suite for `avia-bot-backend`. Split into two layers:

| Layer | Directory | What it covers |
|-------|-----------|----------------|
| **API** (integration) | `tests/api/` | FastAPI HTTP endpoints via `httpx.AsyncClient` |
| **Unit** | `tests/unit/` | Business logic without HTTP: parsers, chunkers, RAG helpers, services, etc. |

Stack: **pytest**, **pytest-asyncio** (`auto` mode), **httpx** (ASGI transport).

Currently **65 tests** across both layers.

## Directory layout

```
tests/
├── README.md           # this file
├── README_RU.md        # Russian version
├── conftest.py         # DB isolation for API tests (see below)
├── paths.py            # shared paths to test data
├── api/
│   ├── conftest.py     # client fixture (lifespan + AsyncClient)
│   ├── test_chat.py    # chat CRUD, settings, messages, guards
│   ├── test_etl.py     # ETL endpoints
│   └── test_health.py  # healthz / readyz
└── unit/
    ├── etl/
    │   └── test_chunker.py       # parser + chunker
    ├── llm/
    │   ├── test_prompts.py       # system prompt builder
    │   └── test_prompt_guard.py  # injection / off-topic guards
    ├── rag/
    │   └── test_pipeline.py      # RRF, query-transform / rerank registry
    └── services/
        ├── test_etl_plan.py      # incremental ingest planning
        └── test_etl_progress.py  # ETL progress helpers
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
| `test_chat.py` | `POST/GET/PATCH/DELETE /api/chats`, `POST/DELETE /api/chats/{id}/messages` | create, list, filter by `chat_type`; `rag_config` / `llm_config` / `use_history` on create and PATCH; empty messages on new chat; send LLM message (mocked `ChatCompletionClient`) with custom-prompt mode skipping guards; send RAG message (mocked `RagPipeline`) persisting metadata, trace, and `message_count`; soft-delete chat and message; prompt injection closes chat → 409 on follow-up; off-topic blocked without closing |
| `test_etl.py` | `GET /api/etl/stats`, `GET /api/etl/manifest` | chunk statistics; manifest without index → 404 |

Message tests patch external I/O (`ChatCompletionClient.complete`, `RagPipeline`) so no LLM or FAISS index is required.

## Unit tests (`tests/unit/`)

Call functions and classes directly, without the HTTP layer. Fast; no FastAPI startup required.

### `unit/etl/test_chunker.py`

Exercises the RAG document parsing pipeline (`etl/parser.py`, `etl/chunker.py`) against the real file `backend/data/rag-document.md`:

| Test | Assertion |
|------|-----------|
| `test_parse_markdown_finds_all_main_sections` | parser finds intro, FAQ, and glossary sections |
| `test_chunk_document_produces_expected_types` | chunker emits SOP, FAQ, GLOSSARY, DECISION_TREE, SCENARIO; ≥ 200 chunks |
| `test_chunks_have_retrieval_prefix` | every chunk has `[Раздел:` and `[Тип:` prefixes |

### `unit/services/test_etl_plan.py`

Tests incremental ingest planning (`app/services/etl_plan.py`):

| Test | Assertion |
|------|-----------|
| `test_plan_reuses_unchanged_chunks_from_faiss` | unchanged chunks reuse existing FAISS vectors |
| `test_plan_embeds_changed_and_new_chunks` | content-hash changes trigger re-embedding |
| `test_plan_marks_removed_chunks` | drafts missing from source are marked removed |
| `test_plan_uses_checkpoint_vectors_before_existing` | checkpoint vectors take priority over FAISS |
| `test_plan_rebuild_embeds_everything` | rebuild mode reuses checkpoint vectors only |

### `unit/services/test_etl_progress.py`

| Test | Assertion |
|------|-----------|
| `test_chunk_progress_context_returns_section_counters` | `_chunk_progress_context` exposes H1 section name and per-section completion |

### `unit/rag/test_pipeline.py`

| Test | Assertion |
|------|-----------|
| `test_reciprocal_rank_fusion_merges_ranked_lists` | RRF boosts chunks appearing in multiple ranked lists |
| `test_resolve_exclusive_query_method_prefers_first_enabled_flag` | only one query-transform method active (HyDE wins over multi-query / rewriting) |
| `test_resolve_rerank_method_when_enabled` | rerank method resolved independently from query transforms |

### `unit/llm/test_prompts.py`

| Test | Assertion |
|------|-----------|
| `test_build_system_prompt_adds_russian_language_hint` | Russian reply hint appended |
| `test_build_system_prompt_adds_english_language_hint` | English reply hint appended |
| `test_build_system_prompt_without_language_returns_base` | no language hint when `reply_language` omitted |

### `unit/llm/test_prompt_guard.py`

Parametrized tests for prompt-injection and off-topic detection (`app/llm/prompt_guard.py`), plus:

| Test | Assertion |
|------|-----------|
| `test_evaluate_user_message_prioritizes_injection_over_off_topic` | injection checked before off-topic |
| `test_wrap_user_message_adds_boundaries` | `<<USER>>` / `<</USER>>` delimiters |
| `test_harden_messages_for_llm_wraps_only_latest_user_message` | only the last user turn is wrapped |
| `test_reply_language_for_user_text` | Cyrillic → `ru`, Latin → `en` |
| `test_blocked_refusal_matches_user_language` | refusal text matches user language |

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
7. **External I/O in API tests** — patch LLM, RAG, and FAISS at the service boundary (`unittest.mock.patch`) so tests stay fast and offline.

## Planned additions

As the project grows:

- `tests/unit/etl/test_parser.py` — parser edge cases on synthetic markdown;
- `tests/unit/services/test_chat.py` — chat service with mocked repositories;
- `tests/api/test_rag.py` — dedicated RAG endpoint tests when exposed separately.

## Pytest markers

`pyproject.toml` registers `api` and `unit` markers — tag tests and filter when needed:

```bash
uv run pytest -m api
uv run pytest -m unit
```

Markers are not applied to tests yet; directory layout is enough for Makefile targets.
