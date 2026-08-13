"""Shared filesystem paths for tests."""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
BACKEND_DATA_DIR = BACKEND_ROOT / "data"
KB_DATA_DIR = REPO_ROOT / "data"
MCP_RAG_ROOT = REPO_ROOT / "mcp-rag"

BACKEND_APP_DB = BACKEND_DATA_DIR / "app.db"
KB_DB = KB_DATA_DIR / "kb.db"

RAG_DOCUMENT_RU = KB_DATA_DIR / "rag-document-ru.md"
RAG_DOCUMENT_EN = KB_DATA_DIR / "rag-document-en.md"
RAG_DOCUMENT = RAG_DOCUMENT_RU

PARITY_QUERY_RU = "правила провоза багажа"
PARITY_QUERY_EN = "baggage allowance rules"
