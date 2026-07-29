"""Shared filesystem paths for tests."""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
RAG_DOCUMENT_RU = BACKEND_ROOT / "data" / "rag-document-ru.md"
RAG_DOCUMENT_EN = BACKEND_ROOT / "data" / "rag-document-en.md"
RAG_DOCUMENT = RAG_DOCUMENT_RU
