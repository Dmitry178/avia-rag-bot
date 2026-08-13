"""RAG pipeline configuration schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.core.rag_constants import DEFAULT_TOP_CHUNKS, MAX_TOP_CHUNKS, MIN_TOP_CHUNKS


class McpConnectionConfig(BaseModel):
    """
    How the backend spawns the mcp-rag server over stdio.
    """

    command: str = Field(default="uv", description="Executable used to start the MCP subprocess.")
    args: list[str] = Field(
        default_factory=lambda: ["run", "python", "-m", "src.server"],
        description="Arguments passed to the MCP server command.",
    )
    cwd: str | None = Field(
        default=None,
        description="Working directory for the MCP subprocess (defaults to <repo>/mcp-rag).",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Extra environment variables merged into the MCP subprocess environment.",
    )


class RagConfig(BaseModel):
    """
    Toggle flags for optional RAG retrieval stages and runtime selection.
    """

    use_hyde: bool | None = Field(
        default=None,
        description="Enable HyDE (hypothetical document embeddings) retrieval.",
    )
    use_multi_query: bool | None = Field(
        default=None,
        description="Enable multi-query retrieval with result fusion.",
    )
    use_query_rewriting: bool | None = Field(
        default=None,
        description="Enable query rewriting before retrieval.",
    )
    use_rerank: bool | None = Field(
        default=None,
        description="Enable cross-encoder reranking after vector search.",
    )
    top_chunks: int = Field(
        default=DEFAULT_TOP_CHUNKS,
        ge=MIN_TOP_CHUNKS,
        le=MAX_TOP_CHUNKS,
        description="Number of knowledge chunks included in the LLM context.",
    )
    runtime: Literal["embed", "mcp"] = Field(
        default="embed",
        description="RAG execution path: embedded pipeline in backend or external mcp-rag MCP server.",
    )
    mcp: McpConnectionConfig | None = Field(
        default=None,
        description="MCP subprocess configuration when runtime is mcp.",
    )

    def to_metadata_dict(self) -> dict[str, bool]:
        """
        Return a compact dict with only non-null flags for message metadata.
        """

        payload: dict[str, bool] = {}

        if self.use_hyde is not None:
            payload["use_hyde"] = self.use_hyde

        if self.use_multi_query is not None:
            payload["use_multi_query"] = self.use_multi_query

        if self.use_query_rewriting is not None:
            payload["use_query_rewriting"] = self.use_query_rewriting

        if self.use_rerank is not None:
            payload["use_rerank"] = self.use_rerank

        return payload
