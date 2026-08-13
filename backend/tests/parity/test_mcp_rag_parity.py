"""Parity checks between embedded backend RAG and mcp-rag stdio MCP."""

import pytest

from app.rag.client import EmbedRagClient, McpRagClient
from app.rag.types import RagQueryContext
from app.schemas.rag import McpConnectionConfig, RagConfig
from tests.parity.compare import assert_retrieve_parity
from tests.paths import PARITY_QUERY_EN, PARITY_QUERY_RU


pytestmark = pytest.mark.parity


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("language_code", "query"),
    [
        ("ru", PARITY_QUERY_RU),
        ("en", PARITY_QUERY_EN),
    ],
)
async def test_retrieve_embed_matches_mcp_stdio(
    language_code: str,
    query: str,
    parity_settings,
    mcp_connection_config: McpConnectionConfig,
) -> None:
    """
    Retrieval parity: chunk ids, similarities, context, and trace steps must align.
    """

    rag_config = RagConfig()
    ctx = RagQueryContext(
        query=query,
        history=[],
        rag_config=rag_config,
        reply_language=language_code,
        language_code=language_code,
    )

    mcp_config = mcp_connection_config.model_copy(deep=True)
    mcp_config.env = {
        **(mcp_config.env or {}),
        "MCP_RAG__LANGUAGE": language_code,
    }

    embed_result = await EmbedRagClient(parity_settings).retrieve(ctx)
    mcp_result = await McpRagClient(mcp_config, parity_settings).retrieve(ctx)

    assert_retrieve_parity(embed_result, mcp_result)
