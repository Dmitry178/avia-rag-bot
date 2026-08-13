"""Fixtures for embed vs MCP parity tests."""

import pytest

from app.core.config import Settings
from app.schemas.rag import McpConnectionConfig
from tests.paths import KB_DATA_DIR, KB_DB, MCP_RAG_ROOT


def _faiss_index_path(data_dir, language_code: str):
    return data_dir / f"faiss-{language_code}.index"


@pytest.fixture(scope="session")
def parity_settings() -> Settings:
    """
    Application settings for parity tests.
    """

    return Settings()


@pytest.fixture(scope="session")
def mcp_connection_config() -> McpConnectionConfig:
    """
    Default stdio MCP connection pointing at the repo ``mcp-rag`` server.
    """

    return McpConnectionConfig(
        command="uv",
        args=["run", "python", "-m", "src.server"],
        cwd=str(MCP_RAG_ROOT),
        env={
            "MCP_RAG__SCHEMAS_DIR": "../data",
            "MCP_RAG__LANGUAGE": "en",
        },
    )


@pytest.fixture(scope="session", autouse=True)
def _require_parity_prerequisites() -> None:
    """
    Skip parity module when KB artifacts or LLM credentials are missing.
    """

    settings = Settings()

    missing: list[str] = []

    if not settings.llm.base_url:
        missing.append("LLM__BASE_URL")

    if not settings.llm.embedding_model:
        missing.append("LLM__EMBEDDING_MODEL")

    for language_code in ("ru", "en"):
        index_path = _faiss_index_path(KB_DATA_DIR, language_code)
        if not index_path.is_file():
            missing.append(str(index_path))

    if not KB_DB.is_file():
        missing.append(str(KB_DB))

    if not MCP_RAG_ROOT.is_dir():
        missing.append(str(MCP_RAG_ROOT))

    if missing:
        pytest.skip(f"parity prerequisites missing: {', '.join(missing)}")
