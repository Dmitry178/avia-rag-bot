"""Shared filesystem paths for mcp-rag tests."""

from pathlib import Path

MCP_RAG_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = MCP_RAG_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"
KB_ROOT = REPO_ROOT
DATA_DIR = REPO_ROOT / "data"
RAG_DOCUMENT_RU = DATA_DIR / "rag-document-ru.md"
RAG_DOCUMENT_EN = DATA_DIR / "rag-document-en.md"
RAG_DOCUMENT = RAG_DOCUMENT_RU
