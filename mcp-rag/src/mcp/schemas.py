"""Pydantic models for MCP tool inputs."""

from pydantic import BaseModel, Field

from src.schemas.rag import RagConfig


class RetrieveToolInput(BaseModel):
    """
    Input contract for the ``retrieve`` MCP tool.
    """

    query: str
    language_code: str = "en"
    reply_language: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)
    rag_config: RagConfig | None = None


class IngestSchemaToolInput(BaseModel):
    """
    Input contract for the ``ingest_schema`` MCP tool.
    """

    schema_path: str
    rebuild: bool = False
    source_path: str | None = None


class IngestDirectoryToolInput(BaseModel):
    """
    Input contract for the ``ingest_directory`` MCP tool.
    """

    directory: str | None = None
    rebuild: bool = False


class IngestAllToolInput(BaseModel):
    """
    Input contract for the ``ingest_all`` MCP tool.
    """

    rebuild: bool = False


class LanguageToolInput(BaseModel):
    """
    Input contract for language-scoped MCP tools.
    """

    language_code: str = "en"


class StatsToolInput(BaseModel):
    """
    Input contract for the ``stats`` MCP tool.
    """

    language_code: str | None = None
