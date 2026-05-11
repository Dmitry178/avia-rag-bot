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
from app.services.etl_progress import IngestProgress


def _print_progress(progress: IngestProgress) -> None:
    """
    Render ingest progress to stderr (single updating line).
    """

    print(
        f"\r[{progress.overall_percent:3d}%] {progress.phase}: {progress.current}/{progress.total}",
        end="",
        flush=True,
        file=sys.stderr,
    )


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


async def cmd_ingest(source_path: str | None, *, rebuild: bool) -> int:
    """
    Run document ingest (incremental by default, with progress output).
    """

    result = await _with_db(
        lambda db: ETLService(db).ingest(
            rebuild=rebuild,
            source_path=source_path,
            on_progress=_print_progress,
        ),
    )

    print(file=sys.stderr)
    print("Ingest completed.")
    print(f"  source_path:     {result.source_path}")
    print(f"  chunk_count:     {result.chunk_count}")
    print(f"  doc_hash:        {result.doc_hash}")
    print(f"  embedding_model: {result.embedding_model}")
    print(f"  built_at:        {result.built_at.isoformat()}")
    print(f"  added:           {result.added}")
    print(f"  updated:         {result.updated}")
    print(f"  unchanged:       {result.unchanged}")
    print(f"  removed:         {result.removed}")
    print(f"  embedded (API):  {result.embedded}")

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
    print(f"chunker_version: {result.chunker_version}")
    print(f"chunk_count:     {result.chunk_count}")
    print(f"built_at:        {result.built_at.isoformat()}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ETL ingest and index maintenance (same as /api/etl endpoints).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser(
        "ingest",
        help="Parse document, embed chunks, update SQLite + FAISS (incremental by default)",
    )
    ingest.add_argument(
        "--source",
        metavar="PATH",
        default=None,
        help="Markdown source path (relative to repo root or absolute); default from ETL__DOCUMENT_PATH",
    )
    ingest.add_argument(
        "--rebuild",
        action="store_true",
        help="Force full re-embed (ignore reusable vectors and checkpoint)",
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
        "ingest": lambda: cmd_ingest(args.source, rebuild=args.rebuild),
        "stats": cmd_stats,
        "manifest": cmd_manifest,
    }

    try:
        exit_code = asyncio.run(commands[args.command]())
    except BaseCustomException as exc:
        logger.error("etl_cli_failed", error_code=exc.error_code, detail=exc.detail, extra=exc.extra)
        print(file=sys.stderr)
        print(f"Error [{exc.error_code}]: {exc.detail}", file=sys.stderr)
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("etl_cli_failed", error=str(exc))
        print(file=sys.stderr)
        print(f"Error: {exc}", file=sys.stderr)
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
