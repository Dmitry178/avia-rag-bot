"""ETL ingestion routes."""

from fastapi import APIRouter, Depends

from app.core.db_manager import DBManager
from app.db.deps import get_db
from app.schemas.etl import ChunkStatsResponse, IngestRequest, IngestResponse, ManifestResponse
from app.services.etl import ETLService

router = APIRouter(prefix="/etl", tags=["etl"])


@router.post(
    "/ingest",
    summary="Ingest knowledge document",
    description="Parse rag-document.md, embed chunks, and update SQLite + FAISS index (incremental by default).",
    response_model=IngestResponse,
)
async def ingest_document(
    body: IngestRequest,
    db: DBManager = Depends(get_db),
) -> IngestResponse:
    """
    Run full ETL pipeline for the knowledge base document.
    """

    return await ETLService(db).ingest(rebuild=body.rebuild, source_path=body.source_path)


@router.get(
    "/stats",
    summary="Chunk statistics",
    description="Return chunk counts grouped by content type.",
    response_model=ChunkStatsResponse,
)
async def chunk_stats(db: DBManager = Depends(get_db)) -> ChunkStatsResponse:
    """
    Return distribution of indexed chunks.
    """

    return await ETLService(db).stats()


@router.get(
    "/manifest",
    summary="Index manifest",
    description="Return metadata for the latest vector index build.",
    response_model=ManifestResponse,
)
async def index_manifest(db: DBManager = Depends(get_db)) -> ManifestResponse:
    """
    Return latest index build metadata.
    """

    return await ETLService(db).manifest()
