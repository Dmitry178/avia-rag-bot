BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help \
	etl-ingest etl-stats etl-manifest \
	backend-install backend-dev backend-test backend-test-api backend-test-unit backend-lint backend-typecheck \
	frontend-install frontend-dev frontend-build frontend-typecheck

help:
	@echo "Targets:"
	@echo "  make etl-ingest          Run full ETL ingest (rebuild index)"
	@echo "  make etl-ingest SOURCE=path/to/doc.md   Ingest from custom markdown"
	@echo "  make etl-stats           Show chunk counts by content_type"
	@echo "  make etl-manifest        Show latest index manifest"
	@echo ""
	@echo "Backend:"
	@echo "  make backend-install     Install backend deps (uv sync)"
	@echo "  make backend-dev         Start FastAPI on :8000"
	@echo "  make backend-test        Run all backend tests"
	@echo "  make backend-test-api    Run API integration tests"
	@echo "  make backend-test-unit   Run unit tests"
	@echo "  make backend-lint        Run ruff check"
	@echo "  make backend-typecheck   Run pyright"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-install    Install frontend npm dependencies"
	@echo "  make frontend-dev        Start Vite dev server on :5173"
	@echo "  make frontend-build      Build frontend for production"
	@echo "  make frontend-typecheck  Run TypeScript check"

# Parse, embed, and rebuild SQLite + FAISS (same as POST /api/etl/ingest).
etl-ingest:
	cd $(BACKEND_DIR) && uv run python scripts/etl.py ingest \
		$(if $(SOURCE),--source $(SOURCE),)

etl-stats:
	cd $(BACKEND_DIR) && uv run python scripts/etl.py stats

etl-manifest:
	cd $(BACKEND_DIR) && uv run python scripts/etl.py manifest

backend-install:
	cd $(BACKEND_DIR) && uv sync

backend-dev:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

backend-test:
	cd $(BACKEND_DIR) && uv run pytest

backend-test-api:
	cd $(BACKEND_DIR) && uv run pytest tests/api

backend-test-unit:
	cd $(BACKEND_DIR) && uv run pytest tests/unit

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
