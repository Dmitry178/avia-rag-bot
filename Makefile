BACKEND_DIR := backend
FRONTEND_DIR := frontend
MCP_RAG_DIR := mcp-rag

.PHONY: help \
	etl-ingest etl-stats etl-manifest \
	backend-install backend-dev backend-test backend-lint backend-typecheck \
	frontend-install frontend-dev frontend-build frontend-typecheck \
	docker-up docker-down docker-build \
	docker-etl-ingest docker-logs

help:
	@echo "Targets:"
	@echo "ETL (mcp-rag / repo-root data/ + data/kb.db):"
	@echo "  make etl-ingest           Ingest all schemas (delegates to mcp-rag)"
	@echo "  Optional: REBUILD=1       Force full re-embed"
	@echo "  make etl-stats           Chunk counts (optional LANG=ru|en)"
	@echo "  make etl-manifest        Latest manifest (optional LANG=ru|en, default ru)"
	@echo ""
	@echo "Backend:"
	@echo "  make backend-install     Install backend deps (uv sync)"
	@echo "  make backend-dev         Start FastAPI on :8000"
	@echo "  make backend-test        Run all backend tests"
	@echo "  make backend-lint        Run ruff check"
	@echo "  make backend-typecheck   Run pyright"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-install    Install frontend npm dependencies"
	@echo "  make frontend-dev        Start Vite dev server on :5173"
	@echo "  make frontend-build      Build frontend for production"
	@echo "  make frontend-typecheck  Run TypeScript check"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up              Build and start backend + frontend (:8080)"
	@echo "  make docker-down            Stop containers"
	@echo "  make docker-build           Build images only"
	@echo "  make docker-etl-ingest      Index schemas via mcp-rag (inside container)"
	@echo "  make docker-logs            Follow compose logs"

etl-ingest:
	$(MAKE) -C $(MCP_RAG_DIR) etl-ingest $(if $(REBUILD),REBUILD=1,)

etl-stats:
	$(MAKE) -C $(MCP_RAG_DIR) etl-stats $(if $(LANG),LANG=$(LANG),)

etl-manifest:
	$(MAKE) -C $(MCP_RAG_DIR) etl-manifest $(if $(LANG),LANG=$(LANG),)

backend-install:
	cd $(BACKEND_DIR) && uv sync

backend-dev:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

backend-test:
	cd $(BACKEND_DIR) && uv run pytest

backend-lint:
	cd $(BACKEND_DIR) && uv run ruff check .

backend-typecheck:
	cd $(BACKEND_DIR) && uv run pyright

frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-dev:
	cd $(FRONTEND_DIR) && npm run dev

frontend-build:
	cd $(FRONTEND_DIR) && npm run build

frontend-typecheck:
	cd $(FRONTEND_DIR) && npm run typecheck

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-etl-ingest:
	docker compose exec backend sh -c 'cd /mcp-rag && uv run python scripts/run_etl.py ingest-dir --dir /data $(if $(REBUILD),--rebuild,)'

docker-logs:
	docker compose logs -f
