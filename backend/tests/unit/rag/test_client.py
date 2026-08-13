"""Unit tests for RAG client adapters."""

import json
import pytest

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.client import EmbedRagClient, McpRagClient, get_rag_client
from app.rag.mcp_deserialize import deserialize_mcp_retrieve_result, parse_mcp_tool_payload
from app.rag.types import RagPipelineResult, RagQueryContext, RagTraceStep, RetrievedChunk
from app.schemas.rag import McpConnectionConfig, RagConfig


def _sample_context() -> RagQueryContext:
    return RagQueryContext(
        query="test query",
        history=[],
        rag_config=RagConfig(),
        reply_language="ru",
        language_code="ru",
    )


def test_rag_config_defaults_to_embed_runtime() -> None:
    """
    Existing chats without runtime should keep the embedded default.
    """

    config = RagConfig()

    assert config.runtime == "embed"
    assert config.mcp is None


def test_get_rag_client_returns_embed_by_default() -> None:
    """
    Factory should return the embedded client unless runtime is mcp.
    """

    db = MagicMock()
    settings = MagicMock()

    client = get_rag_client(RagConfig(), db, settings)

    assert isinstance(client, EmbedRagClient)


def test_get_rag_client_returns_mcp_client() -> None:
    """
    Factory should return MCP client when runtime is mcp.
    """

    db = MagicMock()
    settings = MagicMock()

    client = get_rag_client(RagConfig(runtime="mcp"), db, settings)

    assert isinstance(client, McpRagClient)


@pytest.mark.asyncio
async def test_embed_rag_client_delegates_to_pipeline() -> None:
    """
    Embedded client should call RagPipeline.run with the provided context.
    """

    settings = MagicMock()
    ctx = _sample_context()
    expected = RagPipelineResult(context="ctx", chunks=[], trace=[])

    mock_kb_db = AsyncMock()
    mock_kb_db.__aenter__ = AsyncMock(return_value=mock_kb_db)
    mock_kb_db.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("src.rag.pipeline.RagPipeline") as pipeline_cls,
        patch("src.core.db_manager.DBManager", return_value=mock_kb_db),
        patch("src.db.session.SessionLocal"),
    ):
        pipeline = pipeline_cls.return_value
        pipeline.run = AsyncMock(return_value=expected)

        result = await EmbedRagClient(settings).retrieve(ctx)

    pipeline.run.assert_awaited_once()
    assert result is expected


def test_parse_mcp_tool_payload_reads_structured_content() -> None:
    """
    Parser should prefer structured MCP tool payloads.
    """

    payload = parse_mcp_tool_payload(SimpleNamespace(structuredContent={"context": "ok"}, content=[]))

    assert payload["context"] == "ok"


def test_parse_mcp_tool_payload_reads_json_text() -> None:
    """
    Parser should fall back to JSON encoded text blocks.
    """

    payload = parse_mcp_tool_payload(
        SimpleNamespace(
            structuredContent=None,
            isError=False,
            content=[SimpleNamespace(text=json.dumps({"context": "from-text"}))],
        ),
    )

    assert payload["context"] == "from-text"


@pytest.mark.asyncio
async def test_deserialize_mcp_retrieve_result_builds_pipeline_result() -> None:
    """
    MCP retrieve JSON should deserialize into RagPipelineResult.
    """

    payload = {
        "context": "assembled context",
        "search_queries": ["test query"],
        "chunks": [
            {
                "id": 7,
                "section": "01. Test",
                "title": "Title",
                "content_type": "sop",
                "retrieval_lane": "sop",
                "retrieval_lane_label": "SOP",
                "similarity": 0.5,
                "score": 0.5,
                "content_preview": "preview",
            }
        ],
        "trace": [{"step": "rag_config", "duration_ms": 0, "data": {"use_hyde": False}}],
        "verification_candidates": [],
        "applicable_decision_trees": [],
    }

    with patch("app.rag.mcp_deserialize.get_retrieval_runtime") as runtime_mock:
        runtime_mock.return_value = SimpleNamespace(lane_by_id={})
        result = await deserialize_mcp_retrieve_result(payload, language_code="ru")

    assert result.context == "assembled context"
    assert len(result.chunks) == 1
    assert result.chunks[0].chunk.id == 7
    assert result.trace[0].step == "rag_config"


@pytest.mark.asyncio
async def test_mcp_rag_client_calls_retrieve_tool() -> None:
    """
    MCP client should spawn stdio transport and call the retrieve tool.
    """

    settings = MagicMock()
    settings.repo_root = MagicMock()
    settings.repo_root.__truediv__ = lambda self, other: f"/repo/{other}"

    ctx = RagQueryContext(
        query="hello",
        history=[],
        rag_config=RagConfig(runtime="mcp"),
        reply_language="ru",
        language_code="ru",
    )

    tool_result = SimpleNamespace(
        structuredContent={
            "context": "ctx",
            "search_queries": ["hello"],
            "chunks": [],
            "trace": [],
            "verification_candidates": [],
            "applicable_decision_trees": [],
        },
        content=[],
        isError=False,
    )

    session = AsyncMock()
    session.initialize = AsyncMock()
    session.call_tool = AsyncMock(return_value=tool_result)

    class _SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _TransportContext:
        async def __aenter__(self):
            return (MagicMock(), MagicMock())

        async def __aexit__(self, exc_type, exc, tb):
            return False

    client = McpRagClient(McpConnectionConfig(cwd="/repo/mcp-rag"), settings)

    with (
        patch("app.rag.client.os.path.isdir", return_value=True),
        patch("app.rag.client.stdio_client", return_value=_TransportContext()),
        patch("app.rag.client.ClientSession", return_value=_SessionContext()),
    ):
        result = await client.retrieve(ctx)

    session.call_tool.assert_awaited_once()
    assert session.call_tool.await_args.args[0] == "retrieve"
    assert session.call_tool.await_args.kwargs["arguments"]["language_code"] == "ru"
    assert "schema_path" not in session.call_tool.await_args.kwargs["arguments"]
    assert isinstance(result, RagPipelineResult)
    assert result.context == "ctx"
