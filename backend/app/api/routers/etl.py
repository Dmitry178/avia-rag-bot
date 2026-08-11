"""ETL ingestion routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.core.db_manager import DBManager
from app.db.deps import get_db
from app.schemas.etl import (
    ChunkStatsResponse,
    IngestAllRequest,
    IngestAllResponse,
    IngestRequest,
    IngestResponse,
    ManifestResponse,
)
from app.services.etl import ETLService, ingest_chunking_schema_at_path

router = APIRouter(prefix="/etl", tags=["etl"])


def _resolve_schema_path(schema_path: str) -> Path:
    """
    Resolve a schema path relative to backend root when not absolute.
    """

    path = Path(schema_path)
    if not path.is_absolute():
        path = (settings.backend_root / path).resolve()

    return path


@router.post(
    "/ingest",
    summary="Ingest one chunking schema",
    description="Parse a schema-driven document, embed chunks, and update SQLite + FAISS.",
    response_model=IngestResponse,
)
async def ingest_document(
    body: IngestRequest,
    db: DBManager = Depends(get_db),
) -> IngestResponse:
    """
    Run full ETL pipeline for one chunking schema JSON file.
    """

    return await ingest_chunking_schema_at_path(
        _resolve_schema_path(body.schema_path),
        rebuild=body.rebuild,
        source_path=body.source_path,
        db=db,
    )


@router.post(
    "/ingest-all",
    summary="Ingest all schemas in backend/data",
    description="Discover every chunking schema in backend/data and run ETL for each.",
    response_model=IngestAllResponse,
)
async def ingest_all_documents(
    body: IngestAllRequest,
    db: DBManager = Depends(get_db),
) -> IngestAllResponse:
    """
    Run full ETL pipeline for all schemas in the default data directory.
    """

    return await ETLService(db).ingest_all(rebuild=body.rebuild)


@router.get(
    "/stats",
    summary="Chunk statistics",
    description="Return chunk counts grouped by content type, optionally for one language.",
    response_model=ChunkStatsResponse,
)
async def chunk_stats(
    language_code: str | None = Query(
        default=None,
        description="Filter stats to one knowledge-base language (e.g. ru, en).",
    ),
    db: DBManager = Depends(get_db),
) -> ChunkStatsResponse:
    """
    Return distribution of indexed chunks.
    """

    return await ETLService(db).stats(language_code=language_code)


@router.get(
    "/manifest",
    summary="Index manifest",
    description="Return metadata for the latest vector index build of a language.",
    response_model=ManifestResponse,
)
async def index_manifest(
    language_code: str = Query(
        default="ru",
        description="Knowledge-base language code (e.g. ru, en).",
    ),
    db: DBManager = Depends(get_db),
) -> ManifestResponse:
    """
    Return latest index build metadata for a language.
    """

    return await ETLService(db).manifest(language_code=language_code)
