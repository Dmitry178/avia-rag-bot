"""RAG client adapters for embedded and MCP retrieval."""

import os

from typing import Protocol

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, get_default_environment, stdio_client

from app.core.config import Settings
from app.core.db_manager import DBManager
from app.exceptions.service import ServiceError
from app.rag.mcp_deserialize import deserialize_mcp_retrieve_result, parse_mcp_tool_payload
from app.rag.types import RagPipelineResult, RagQueryContext
from app.schemas.rag import McpConnectionConfig, RagConfig


class RagClient(Protocol):
    """
    Retrieve knowledge-base context for chat generation.
    """

    async def retrieve(self, ctx: RagQueryContext) -> RagPipelineResult: ...


def _embed_import_error(exc: ImportError) -> None:
    raise ServiceError(
        detail="In-process RAG (embed) is not installed in this backend image.",
        error_code="rag_embed_not_installed",
        status_code=503,
    ) from exc


def _to_src_rag_config(rag_config: RagConfig):
    from src.schemas.rag import RagConfig as SrcRagConfig

    return SrcRagConfig.model_validate(
        rag_config.model_dump(
            include={
                "use_hyde",
                "use_multi_query",
                "use_query_rewriting",
                "use_rerank",
                "top_chunks",
            }
        )
    )


class EmbedRagClient:
    """
    Embedded RAG path using in-process ``src.rag.RagPipeline``.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @staticmethod
    async def retrieve(ctx: RagQueryContext) -> RagPipelineResult:
        """
        Execute the canonical retrieval pipeline from ``mcp-rag``.
        """

        try:
            from src.core.config import settings as kb_settings
            from src.core.db_manager import DBManager as KbDBManager
            from src.db.session import SessionLocal
            from src.rag.pipeline import RagPipeline
            from src.rag.types import RagQueryContext as SrcRagQueryContext
        except ImportError as exc:
            _embed_import_error(exc)

        src_ctx = SrcRagQueryContext(
            query=ctx.query,
            history=ctx.history,
            rag_config=_to_src_rag_config(ctx.rag_config),
            reply_language=ctx.reply_language,
            language_code=ctx.language_code,
        )

        async with KbDBManager(SessionLocal) as kb_db:
            pipeline = RagPipeline(kb_db, kb_settings)
            return await pipeline.run(src_ctx)


class McpRagClient:
    """
    MCP-backed RAG path that calls the external ``mcp-rag`` ``retrieve`` tool.
    """

    def __init__(
        self,
        mcp_config: McpConnectionConfig | None,
        settings: Settings,
    ) -> None:
        self._mcp_config = mcp_config or McpConnectionConfig()
        self._settings = settings

    def _stdio_parameters(self) -> StdioServerParameters:
        cwd = self._mcp_config.cwd or str(self._settings.repo_root / "mcp-rag")
        env = get_default_environment()
        env.update(self._mcp_config.env)

        return StdioServerParameters(
            command=self._mcp_config.command,
            args=self._mcp_config.args,
            cwd=cwd,
            env=env,
        )

    @staticmethod
    def _build_tool_arguments(ctx: RagQueryContext) -> dict:
        rag_config = ctx.rag_config
        return {
            "query": ctx.query,
            "language_code": ctx.language_code,
            "reply_language": ctx.reply_language,
            "history": ctx.history,
            "rag_config": {
                "use_hyde": rag_config.use_hyde,
                "use_multi_query": rag_config.use_multi_query,
                "use_query_rewriting": rag_config.use_query_rewriting,
                "use_rerank": rag_config.use_rerank,
                "top_chunks": rag_config.top_chunks,
            },
        }

    async def retrieve(self, ctx: RagQueryContext) -> RagPipelineResult:
        """
        Spawn the MCP server, call ``retrieve``, and deserialize the response.
        """

        params = self._stdio_parameters()
        if not os.path.isdir(params.cwd or ""):
            raise ServiceError(
                detail=f"MCP working directory does not exist: {params.cwd}",
                error_code="mcp_invalid_cwd",
                status_code=400,
            )

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("retrieve", arguments=self._build_tool_arguments(ctx))

        payload = parse_mcp_tool_payload(result)
        return await deserialize_mcp_retrieve_result(payload, language_code=ctx.language_code)


def get_rag_client(rag_config: RagConfig, db: DBManager, settings: Settings) -> RagClient:
    """
    Return the configured RAG client implementation.
    """

    _ = db

    if rag_config.runtime == "mcp":
        return McpRagClient(rag_config.mcp, settings)

    return EmbedRagClient(settings)
