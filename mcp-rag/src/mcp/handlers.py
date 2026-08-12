"""MCP tool handler implementations."""

from pathlib import Path

from src.core.config import Settings, settings
from src.core.db_manager import DBManager
from src.etl.chunking_schema import load_runtime_schema_for_language, resolve_schema_output_root
from src.exceptions.service import ServiceError
from src.mcp.runtime import resolve_schema_path, resolve_schemas_dir, with_app_db
from src.mcp.schemas import (
    IngestAllToolInput,
    IngestDirectoryToolInput,
    IngestSchemaToolInput,
    LanguageToolInput,
    RetrieveToolInput,
    StatsToolInput,
)
from src.mcp.serialize import serialize_rag_pipeline_result
from src.rag.pipeline import RagPipeline
from src.rag.types import RagQueryContext
from src.schemas.rag import RagConfig
from src.services.etl import ETLService, ingest_chunking_schema_at_path


async def handle_retrieve(payload: RetrieveToolInput) -> dict:
    """
    Run the full RAG retrieval pipeline and return the MCP JSON contract.
    """

    async def _run(db: DBManager, app_settings: Settings) -> dict:
        pipeline = RagPipeline(db, app_settings)
        reply_language = payload.reply_language or payload.language_code
        rag_config = payload.rag_config or RagConfig()

        result = await pipeline.run(
            RagQueryContext(
                query=payload.query,
                history=payload.history,
                rag_config=rag_config,
                reply_language=reply_language,
                language_code=payload.language_code,
            ),
        )

        return serialize_rag_pipeline_result(result, language_code=payload.language_code)

    return await with_app_db(_run)


async def handle_ingest_schema(payload: IngestSchemaToolInput) -> dict:
    """
    Ingest one chunking schema JSON file.
    """

    schema_path = resolve_schema_path(payload.schema_path)
    result = await ingest_chunking_schema_at_path(
        schema_path,
        rebuild=payload.rebuild,
        source_path=payload.source_path,
    )

    return result.model_dump(mode="json")


async def handle_ingest_directory(payload: IngestDirectoryToolInput) -> dict:
    """
    Ingest every supported schema JSON in a directory.
    """

    schemas_dir = Path(payload.directory) if payload.directory else resolve_schemas_dir()
    if not schemas_dir.is_absolute():
        schemas_dir = resolve_schemas_dir() / schemas_dir

    async def _run(db: DBManager, app_settings: Settings) -> dict:
        service = ETLService(db, app_settings)
        result = await service.ingest_directory(
            schemas_dir=schemas_dir.resolve(),
            rebuild=payload.rebuild,
        )
        return result.model_dump(mode="json")

    return await with_app_db(_run)


async def handle_ingest_all(payload: IngestAllToolInput) -> dict:
    """
    Ingest every supported schema in the default KB data directory.
    """

    async def _run(db: DBManager, app_settings: Settings) -> dict:
        service = ETLService(db, app_settings)
        result = await service.ingest_all(rebuild=payload.rebuild)
        return result.model_dump(mode="json")

    return await with_app_db(_run)


async def handle_index_status(payload: LanguageToolInput) -> dict:
    """
    Return manifest metadata and filesystem checks for a language index.
    """

    async def _run(db: DBManager, app_settings: Settings) -> dict:
        service = ETLService(db, app_settings)
        manifest = await service.manifest(payload.language_code)

        context = load_runtime_schema_for_language(payload.language_code, str(app_settings.backend_root))
        output_root = resolve_schema_output_root(
            context.schema,
            schema_dir=context.schema_dir,
            backend_root=app_settings.backend_root,
            repo_root=app_settings.repo_root,
            output_root_override=None,
        )
        faiss_path = (output_root / context.schema.io.faiss_index_path).resolve()
        manifest_path = (output_root / context.schema.io.manifest_path).resolve()

        return {
            "language_code": payload.language_code,
            "manifest": manifest.model_dump(mode="json"),
            "paths": {
                "output_root": str(output_root),
                "faiss_index": str(faiss_path),
                "faiss_index_exists": faiss_path.is_file(),
                "manifest_json": str(manifest_path),
                "manifest_json_exists": manifest_path.is_file(),
            },
        }

    try:
        return await with_app_db(_run)
    except ServiceError as exc:
        if exc.error_code != "etl_not_indexed":
            raise

        context = load_runtime_schema_for_language(payload.language_code, str(settings.backend_root))
        output_root = resolve_schema_output_root(
            context.schema,
            schema_dir=context.schema_dir,
            backend_root=settings.backend_root,
            repo_root=settings.repo_root,
            output_root_override=None,
        )
        faiss_path = (output_root / context.schema.io.faiss_index_path).resolve()
        manifest_path = (output_root / context.schema.io.manifest_path).resolve()

        return {
            "language_code": payload.language_code,
            "manifest": None,
            "paths": {
                "output_root": str(output_root),
                "faiss_index": str(faiss_path),
                "faiss_index_exists": faiss_path.is_file(),
                "manifest_json": str(manifest_path),
                "manifest_json_exists": manifest_path.is_file(),
            },
            "error_code": exc.error_code,
            "detail": exc.detail,
        }


async def handle_stats(payload: StatsToolInput) -> dict:
    """
    Return chunk counts grouped by content type.
    """

    async def _run(db: DBManager, app_settings: Settings) -> dict:
        service = ETLService(db, app_settings)
        result = await service.stats(payload.language_code)
        return result.model_dump(mode="json")

    return await with_app_db(_run)
