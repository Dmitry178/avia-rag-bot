"""Health check routes."""

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.core.db_manager import DBManager
from app.db.deps import get_db
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(tags=["health"])


@router.get(
    "/healthz",
    summary="Liveness probe",
    description="Report whether the API process is running.",
    response_model=HealthResponse,
)
async def healthz() -> HealthResponse:
    """
    Report whether the API process is running.
    """

    return HealthResponse(status="ok")


@router.get(
    "/readyz",
    summary="Readiness probe",
    description="Report whether dependencies required to serve traffic are available.",
    response_model=HealthResponse,
)
async def readyz(db: DBManager = Depends(get_db)) -> HealthResponse | JSONResponse:
    """
    Report whether dependencies required to serve traffic are available.
    """

    if await HealthService(db).is_ready():
        return HealthResponse(status="ok")

    return JSONResponse(
        status_code=503,
        content=HealthResponse(status="not_ready").model_dump(),
    )
