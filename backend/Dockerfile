# syntax=docker/dockerfile:1
# Build from repository root: docker compose build (context = .)

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS base

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_HTTP_TIMEOUT=120

FROM base AS deps

COPY backend/pyproject.toml backend/uv.lock ./
COPY mcp-rag /mcp-rag
RUN uv sync --frozen --no-dev --extra rag --no-install-project

FROM base AS runtime

COPY --from=deps /app/.venv /app/.venv
COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/app ./app
COPY mcp-rag /mcp-rag
RUN uv sync --frozen --no-dev --extra rag

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
