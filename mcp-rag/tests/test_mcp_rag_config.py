"""Tests for MCP_RAG__* environment aliases in mcp-rag settings."""

from src.core.config import Settings


def test_mcp_rag_db_url_alias_overrides_default(monkeypatch) -> None:
    """
    KB database URL should be readable via MCP_RAG__DB__URL without using backend DB__URL.
    """

    monkeypatch.delenv("DB__URL", raising=False)
    monkeypatch.setenv("MCP_RAG__DB__URL", "sqlite:///./tmp/kb-alias.db")

    settings = Settings()

    assert settings.db.url == "sqlite:///./tmp/kb-alias.db"
