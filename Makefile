BACKEND_DIR := backend
FRONTEND_DIR := frontend
ETL_SCHEMAS_DIR ?= data

.PHONY: help \
	etl-ingest etl-stats etl-manifest \
	backend-install backend-dev backend-test backend-lint backend-typecheck \
	frontend-install frontend-dev frontend-build frontend-typecheck \
	docker-up docker-down docker-build \
	docker-etl-ingest docker-logs

help:
	@echo "Targets:"
	@echo "ETL — discover schema JSON files in a directory and build SQLite + FAISS:"
	@echo "  make etl-ingest           Ingest all schemas in backend/$(ETL_SCHEMAS_DIR)"
	@echo "  Optional: REBUILD=1       Force full re-embed"
	@echo "  Optional: ETL_SCHEMAS_DIR=path   Schema directory relative to backend/ (default: data)"
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
	@echo "  make docker-etl-ingest      Index all schemas in backend/data (inside container)"
	@echo "  make docker-logs            Follow compose logs"

# Discover schema JSON files in a directory and ingest each into SQLite + FAISS.
ifeq ($(ETL_SCHEMAS_DIR),data)
etl-ingest:
	cd $(BACKEND_DIR) && uv run python scripts/run_etl.py ingest-all \
		$(if $(REBUILD),--rebuild,)
else
etl-ingest:
	cd $(BACKEND_DIR) && uv run python scripts/run_etl.py ingest-dir --dir $(ETL_SCHEMAS_DIR) \
		$(if $(REBUILD),--rebuild,)
endif

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

docker-logs:
	docker compose logs -f
