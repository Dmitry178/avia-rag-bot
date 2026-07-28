"""ETL ingestion routes."""

from fastapi import APIRouter, Depends, Query

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
from app.services.etl import ETLService

router = APIRouter(prefix="/etl", tags=["etl"])


@router.post(
    "/ingest",
    summary="Ingest knowledge document",
    description="Parse a language-specific RAG document, embed chunks, and update SQLite + FAISS index.",
    response_model=IngestResponse,
)
async def ingest_document(
    body: IngestRequest,
    db: DBManager = Depends(get_db),
) -> IngestResponse:
    """
    Run full ETL pipeline for one knowledge-base language.
    """

    language_code = body.language_code or "ru"

    return await ETLService(db).ingest(
        language_code=language_code,
        rebuild=body.rebuild,
        source_path=body.source_path,
    )


@router.post(
    "/ingest-all",
    summary="Ingest all knowledge-base languages",
    description="Run ETL for every configured KB language (ru and en).",
    response_model=IngestAllResponse,
)
async def ingest_all_documents(
    body: IngestAllRequest,
    db: DBManager = Depends(get_db),
) -> IngestAllResponse:
    """
    Run full ETL pipeline for all configured languages.
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
