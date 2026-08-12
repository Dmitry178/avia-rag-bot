"""Register MCP tools on a FastMCP server instance."""

from fastmcp import FastMCP

from src.mcp.handlers import (
    handle_index_status,
    handle_ingest_all,
    handle_ingest_directory,
    handle_ingest_schema,
    handle_retrieve,
    handle_stats,
)
from src.mcp.schemas import (
    IngestAllToolInput,
    IngestDirectoryToolInput,
    IngestSchemaToolInput,
    LanguageToolInput,
    RetrieveToolInput,
    StatsToolInput,
)
from src.config import settings as mcp_rag_settings
from src.schemas.rag import RagConfig

_DEFAULT_LANGUAGE = mcp_rag_settings.language


def register_tools(mcp: FastMCP) -> None:
    """
    Attach all v1 MCP tools to the given server.
    """

    @mcp.tool(description="Run the full RAG retrieval pipeline.")
    async def retrieve(
        query: str,
        language_code: str = _DEFAULT_LANGUAGE,
        reply_language: str | None = None,
        history: list[dict[str, str]] | None = None,
        rag_config: dict | None = None,
    ) -> dict:
        parsed_config = RagConfig.model_validate(rag_config) if rag_config is not None else None
        payload = RetrieveToolInput(
            query=query,
            language_code=language_code,
            reply_language=reply_language,
            history=history or [],
            rag_config=parsed_config,
        )
        return await handle_retrieve(payload)

    @mcp.tool(description="Ingest one chunking schema JSON file.")
    async def ingest_schema(
        schema_path: str,
        rebuild: bool = False,
        source_path: str | None = None,
    ) -> dict:
        payload = IngestSchemaToolInput(
            schema_path=schema_path,
            rebuild=rebuild,
            source_path=source_path,
        )
        return await handle_ingest_schema(payload)

    @mcp.tool(description="Ingest all supported schema JSON files in a directory.")
    async def ingest_directory(
        directory: str | None = None,
        rebuild: bool = False,
    ) -> dict:
        payload = IngestDirectoryToolInput(directory=directory, rebuild=rebuild)
        return await handle_ingest_directory(payload)

    @mcp.tool(description="Ingest all supported schemas in the default KB data directory.")
    async def ingest_all(rebuild: bool = False) -> dict:
        payload = IngestAllToolInput(rebuild=rebuild)
        return await handle_ingest_all(payload)

    @mcp.tool(description="Return manifest metadata and index file existence for a language.")
    async def index_status(language_code: str = _DEFAULT_LANGUAGE) -> dict:
        payload = LanguageToolInput(language_code=language_code)
        return await handle_index_status(payload)

    @mcp.tool(description="Return chunk counts grouped by content type.")
    async def stats(language_code: str | None = None) -> dict:
        payload = StatsToolInput(language_code=language_code)
        return await handle_stats(payload)
