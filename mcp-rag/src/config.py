"""Environment-based configuration for the mcp-rag server."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class McpRagSettings(BaseSettings):
    """
    Paths and runtime options for mcp-rag (repo-root ``data/`` volume).
    """

    model_config = SettingsConfigDict(env_prefix="MCP_RAG__")

    schemas_dir: str = "../data"
    repo_root: str = ".."
    language: str = "en"


settings = McpRagSettings()
