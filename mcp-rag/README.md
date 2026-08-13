# mcp-rag

**English** · [Русский](README_RU.md)

Canonical RAG + ETL package for avia-bot. Backend uses it via:

- **`runtime=embed`** — lazy in-process import of `src.rag` (`EmbedRagClient`)
- **`runtime=mcp`** — stdio MCP server (`McpRagClient`)

## Run (stdio)

From this directory:

```bash
uv sync
uv run python -m src.server
```

The server speaks MCP over stdin/stdout. Use an MCP client (Cursor, backend `McpRagClient`, or the official `mcp` SDK) to connect.

## Data volume

KB artifacts live in **repo-root `data/`**:

| Path | Purpose |
|------|---------|
| `data/kb.db` | `chunk_meta`, `index_manifest` |
| `data/faiss-{lang}.index` | FAISS vectors |
| `data/rag-document-{lang}.md` | Source markdown |
| `data/chunking-schema-{lang}.json` | ETL schema v3 |

Chats stay in `backend/data/app.db` (backend only).

## Indexing

```bash
make etl-ingest          # from repo root
# or
make -C mcp-rag etl-ingest
uv run python scripts/run_etl.py ingest-dir --dir ../data
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_RAG__SCHEMAS_DIR` | `../data` | KB volume root |
| `MCP_RAG__DB__URL` | `sqlite:///./data/kb.db` | Chunk/manifest SQLite (prefer over bare `DB__URL` in shared env) |
| `LLM__API_KEY`, `LLM__BASE_URL`, `LLM__MODEL`, `LLM__EMBEDDING_MODEL` | — | LLM/embeddings |

## Verify imports

```bash
uv run pytest tests/test_import_smoke.py -v
```

## Tools

| Tool | Purpose |
|------|---------|
| `retrieve` | Full RAG retrieval pipeline (`RagPipeline.run`) |
| `ingest_schema` | Ingest one chunking schema JSON |
| `ingest_directory` | Ingest all schemas in a directory |
| `ingest_all` | Ingest default KB data directory |
| `index_status` | Manifest + FAISS/manifest file existence |
| `stats` | Chunk counts by content type |

Handlers: `src/mcp/handlers.py`; registration: `src/mcp/register.py`.

See `docs/mcp_rag_migration_agent.md` for the full migration playbook.
