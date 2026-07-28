BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: help \
	etl-ingest-ru etl-ingest-en etl-ingest-all etl-stats etl-manifest \
	backend-install backend-dev backend-test backend-test-api backend-test-unit backend-lint backend-typecheck \
	frontend-install frontend-dev frontend-build frontend-typecheck \
	docker-up docker-down docker-build \
	docker-etl-ingest docker-etl-ingest-ru docker-etl-ingest-en docker-logs

help:
	@echo "Targets:"
	@echo "ETL — index knowledge base (creates faiss-<lang>.index per language):"
	@echo "  make etl-ingest-ru       Index Russian KB only  (ru → faiss-ru.index)"
	@echo "  make etl-ingest-en       Index English KB only (en → faiss-en.index)"
	@echo "  make etl-ingest-all      Index both ru and en"
	@echo "  Optional: REBUILD=1      Force full re-embed"
	@echo "  Optional: SOURCE=path    Override markdown file (with -ru or -en targets)"
	@echo "  make etl-stats           Chunk counts (optional LANG=ru|en)"
	@echo "  make etl-manifest        Latest manifest (optional LANG=ru|en, default ru)"
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
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up              Build and start backend + frontend (:8080)"
	@echo "  make docker-down            Stop containers"
	@echo "  make docker-build           Build images only"
	@echo "  make docker-etl-ingest      Index ru + en inside backend container"
	@echo "  make docker-etl-ingest-ru   Index ru only inside backend container"
	@echo "  make docker-etl-ingest-en   Index en only inside backend container"
	@echo "  make docker-logs            Follow compose logs"

# Index one language or both (same as POST /api/etl/ingest and /api/etl/ingest-all).
etl-ingest-ru:
	cd $(BACKEND_DIR) && uv run python scripts/run_etl.py ingest --lang ru \
		$(if $(SOURCE),--source $(SOURCE),) \
		$(if $(REBUILD),--rebuild,)

etl-ingest-en:
	cd $(BACKEND_DIR) && uv run python scripts/run_etl.py ingest --lang en \
		$(if $(SOURCE),--source $(SOURCE),) \
		$(if $(REBUILD),--rebuild,)

etl-ingest-all:
	cd $(BACKEND_DIR) && uv run python scripts/run_etl.py ingest-all \
		$(if $(REBUILD),--rebuild,)

etl-stats:
	cd $(BACKEND_DIR) && uv run python scripts/run_etl.py stats \
		$(if $(LANG),--lang $(LANG),)

etl-manifest:
	cd $(BACKEND_DIR) && uv run python scripts/run_etl.py manifest \
		--lang $(or $(LANG),ru)

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

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-etl-ingest:
	docker compose exec backend uv run python scripts/run_etl.py ingest-all \
		$(if $(REBUILD),--rebuild,)

docker-etl-ingest-ru:
	docker compose exec backend uv run python scripts/run_etl.py ingest --lang ru \
		$(if $(REBUILD),--rebuild,)

docker-etl-ingest-en:
	docker compose exec backend uv run python scripts/run_etl.py ingest --lang en \
		$(if $(REBUILD),--rebuild,)

docker-logs:
	docker compose logs -f
