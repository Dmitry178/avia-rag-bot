"""Import smoke tests for stage 3 stack."""

from src.core.config import settings
from src.rag import RagPipeline
from src.rag.pipeline import RagPipeline as RagPipelineDirect
from src.services.etl import ETLService, ingest_chunking_schema_at_path


def test_rag_pipeline_importable() -> None:
    """
    RAG pipeline should be importable from the mcp-rag package.
    """

    assert RagPipeline is RagPipelineDirect


def test_etl_service_importable() -> None:
    """
    ETL service and schema ingest entrypoints should import.
    """

    assert ETLService is not None
    assert callable(ingest_chunking_schema_at_path)


def test_settings_point_at_repo_data_volume() -> None:
    """
    Default settings should resolve KB artifacts under repo-root data/.
    """

    assert settings.data_root.name == "data"
    assert (settings.data_root / "chunking-schema-ru.json").exists()
