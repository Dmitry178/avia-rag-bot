"""Shared filesystem paths for tests."""

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
RAG_DOCUMENT = BACKEND_ROOT / "data" / "rag-document.md"
