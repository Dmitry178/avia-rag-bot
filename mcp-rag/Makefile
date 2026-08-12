MCP_RAG_DIR := .
ETL_SCHEMAS_DIR ?= ../data

.PHONY: help etl-ingest etl-stats etl-manifest install test

help:
	@echo "mcp-rag indexing (repo-root data/ + data/kb.db):"
	@echo "  make etl-ingest           Ingest all schemas in $(ETL_SCHEMAS_DIR)"
	@echo "  Optional: REBUILD=1       Force full re-embed"
	@echo "  make etl-stats            Chunk counts (optional LANG=ru|en)"
	@echo "  make etl-manifest         Latest manifest (optional LANG=ru|en, default ru)"
	@echo "  make install              uv sync"
	@echo "  make test                 pytest"

etl-ingest:
	cd $(MCP_RAG_DIR) && uv run python scripts/run_etl.py ingest-all \
		$(if $(REBUILD),--rebuild,)

etl-stats:
	cd $(MCP_RAG_DIR) && uv run python scripts/run_etl.py stats \
		$(if $(LANG),--lang $(LANG),)

etl-manifest:
	cd $(MCP_RAG_DIR) && uv run python scripts/run_etl.py manifest \
		--lang $(or $(LANG),ru)

install:
	cd $(MCP_RAG_DIR) && uv sync

test:
	cd $(MCP_RAG_DIR) && uv run pytest
