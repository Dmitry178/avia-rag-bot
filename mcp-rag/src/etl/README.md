# ETL (Schema-Driven)

**English** · [Русский](README_RU.md)

`mcp-rag/src/etl/` is a schema-driven chunking package. It transforms markdown documents into `ChunkDraft` items using JSON schema v3 only.

The single runtime path is:

1. Load schema (`chunking_schema.py`)
2. Build chunks (`universal_chunker.py`)
3. Persist/index in service layer (`src/services/etl.py` or `src/services/schema_etl.py`)

## Key files

- `chunking_schema.py` — pydantic schema models, loader, path resolution, schema link validation.
- `universal_chunker.py` — classification + policy execution (`whole_section`, `by_subheading`, `qa_pairs`, `qa_by_heading_prefix`, `regex_split`, `token_window`).
- `faq_regex.py` — FAQ extraction regex helper.
- `types.py` — shared ETL dataclass (`ChunkDraft`).

## Entry points

- Main KB ingest: `src/services/etl.py`
- Universal schema ingest for external docs: `src/services/schema_etl.py`
- CLI: `mcp-rag/scripts/run_etl.py` (`ingest-all`, `ingest-dir`, `ingest-schema`, `stats`, `manifest`, `schema-ingest`, interactive mode without args)
- Makefile: `make -C mcp-rag etl-ingest` (or `make etl-ingest` from repo root)

## Schemas and docs

- Runtime schemas: `data/chunking-schema-ru.json`, `data/chunking-schema-en.json` (repo root)
- Specification: `docs/etl_chunking_schema_spec.md`
- Templates: `docs/examples/chunking-schema-template-*.json`

## Tests

Run ETL unit tests from `mcp-rag/`:

```bash
uv run pytest tests/unit/etl -v
```
