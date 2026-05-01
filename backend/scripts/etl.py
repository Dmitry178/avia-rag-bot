"""CLI entrypoint for ETL (same pipeline as POST /api/etl/*)."""

import argparse
import asyncio
import sys

from collections.abc import Callable, Coroutine
from typing import Any

from app.core.config import settings
from app.core.db_manager import DBManager
from app.core.logs import logger
from app.db.init_db import init_db
from app.db.session import SessionLocal, dispose_engine
from app.exceptions.base import BaseCustomException
from app.services.etl import ETLService


async def _with_db[T](handler: Callable[[DBManager], Coroutine[Any, Any, T]]) -> T:
    """
    Open DB session, run handler, commit lifecycle and dispose engine.
    """

    settings.data.ensure_exists()
    await init_db()

    try:
        async with DBManager(SessionLocal) as db:
            return await handler(db)
    finally:
        await dispose_engine()


async def cmd_ingest(source_path: str | None) -> int:
    """
    Run full document ingest (rebuild index).
    """

    result = await _with_db(
        lambda db: ETLService(db).ingest(rebuild=True, source_path=source_path),
    )

    print("Ingest completed.")
    print(f"  source_path:     {result.source_path}")
    print(f"  chunk_count:     {result.chunk_count}")
    print(f"  doc_hash:        {result.doc_hash}")
    print(f"  embedding_model: {result.embedding_model}")
    print(f"  built_at:        {result.built_at.isoformat()}")

    return 0


async def cmd_stats() -> int:
    """
    Print chunk counts by content type.
    """

    result = await _with_db(lambda db: ETLService(db).stats())
    print(f"Total chunks: {result.total}")

    for content_type, count in sorted(result.by_content_type.items()):
        print(f"  {content_type}: {count}")

    return 0


async def cmd_manifest() -> int:
    """
    Print latest index manifest.
    """

    result = await _with_db(lambda db: ETLService(db).manifest())

    print(f"source_path:     {result.source_path}")
    print(f"doc_hash:        {result.doc_hash}")
    print(f"embedding_model: {result.embedding_model}")
    print(f"chunk_count:     {result.chunk_count}")
    print(f"built_at:        {result.built_at.isoformat()}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ETL ingest and index maintenance (same as /api/etl endpoints).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Parse document, embed chunks, rebuild SQLite + FAISS")
    ingest.add_argument(
        "--source",
        metavar="PATH",
        default=None,
        help="Markdown source path (relative to repo root or absolute); default from ETL__DOCUMENT_PATH",
    )

    subparsers.add_parser("stats", help="Show chunk counts by content_type")
    subparsers.add_parser("manifest", help="Show latest index manifest")

    return parser


def main() -> None:
    """
    CLI entrypoint.
    """

    args = _build_parser().parse_args()
    commands: dict[str, Callable[[], Coroutine[Any, Any, int]]] = {
        "ingest": lambda: cmd_ingest(args.source),
        "stats": cmd_stats,
        "manifest": cmd_manifest,
    }

    try:
        exit_code = asyncio.run(commands[args.command]())
    except BaseCustomException as exc:
        logger.error("etl_cli_failed", error_code=exc.error_code, detail=exc.detail, extra=exc.extra)
        print(f"Error [{exc.error_code}]: {exc.detail}", file=sys.stderr)
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("etl_cli_failed", error=str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
