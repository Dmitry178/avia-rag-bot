"""CLI entrypoint for ETL (same pipeline as POST /api/etl/*)."""

import argparse
import asyncio
import sys

from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from app.core.config import DBSettings, settings
from app.core.db_manager import DBManager
from app.core.logs import logger
from app.db.init_db import init_db
from app.db.session import SessionLocal, dispose_engine
from app.exceptions.base import BaseCustomException
from app.exceptions.ingest import IngestInterruptedError
from app.services.etl import ETLService, ingest_chunking_schema_at_path
from app.services.etl_progress import IngestProgress
from app.services.schema_etl import SchemaETLService
from etl.chunking_schema import (
    discover_chunking_schemas,
    load_runtime_schema,
    resolve_schema_chunk_meta_db_path,
)


def _truncate(text: str, max_len: int = 55) -> str:
    """
    Shorten long titles for terminal progress lines.
    """

    stripped = text.strip()
    if len(stripped) <= max_len:
        return stripped

    return stripped[: max_len - 3] + "..."


def _print_progress(progress: IngestProgress) -> None:
    """
    Render ingest progress to stderr (single updating line).
    """

    line = (
        f"\r[{progress.overall_percent:3d}%] {progress.phase}: "
        f"{progress.current}/{progress.total}"
    )

    if progress.section:
        if progress.section_current is not None and progress.section_total is not None:
            line += f" | {progress.section} ({progress.section_current}/{progress.section_total})"
        else:
            line += f" | {progress.section}"

    if progress.item_title:
        line += f" — {_truncate(progress.item_title)}"

    print(line, end="", flush=True, file=sys.stderr)


async def _with_db[T](handler: Callable[[DBManager], Coroutine[Any, Any, T]]) -> T:
    """
    Open DB session, run handler, commit lifecycle and dispose engine.
    """

    settings.data.ensure_exists(settings.backend_root)
    await init_db()

    try:
        async with DBManager(SessionLocal) as db:
            return await handler(db)
    finally:
        await dispose_engine()


async def _with_db_file[T](db_file: Path, handler: Callable[[DBManager], Coroutine[Any, Any, T]]) -> T:
    """
    Point the app database at a schema-declared SQLite file and run handler.
    """

    db_file.parent.mkdir(parents=True, exist_ok=True)
    await dispose_engine()
    settings.db = DBSettings(url=f"sqlite:///{db_file.resolve().as_posix()}")
    settings.data.ensure_exists(settings.backend_root)
    await init_db()

    try:
        async with DBManager(SessionLocal) as db:
            return await handler(db)
    finally:
        await dispose_engine()


def _resolve_cli_path(path_value: str) -> Path:
    """
    Resolve a CLI path relative to backend root when not absolute.
    """

    path = Path(path_value)
    if not path.is_absolute():
        path = (settings.backend_root / path).resolve()

    return path


async def cmd_ingest_schema(
    schema_path: str,
    source_path: str | None,
    *,
    rebuild: bool,
) -> int:
    """
    Ingest one chunking schema JSON into SQLite + FAISS.
    """

    path = _resolve_cli_path(schema_path)
    result = await ingest_chunking_schema_at_path(
        path,
        rebuild=rebuild,
        source_path=source_path,
        on_progress=_print_progress,
    )

    print(file=sys.stderr)
    print("Ingest-schema completed.")
    print(f"  schema_path:     {path}")
    print(f"  language_code:   {result.language_code}")
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


async def cmd_ingest_dir(
    schemas_dir: str,
    *,
    rebuild: bool,
) -> int:
    """
    Discover schema JSON files in a directory and ingest each one into SQLite + FAISS.
    """

    dir_path = _resolve_cli_path(schemas_dir)

    schema_paths = discover_chunking_schemas(dir_path)
    first_context = load_runtime_schema(schema_paths[0], settings.backend_root, settings.repo_root)
    db_path = resolve_schema_chunk_meta_db_path(first_context.schema, schema_dir=first_context.schema_dir)

    async def _run(db: DBManager):
        return await ETLService(db).ingest_directory(
            schemas_dir=dir_path,
            rebuild=rebuild,
            on_progress=_print_progress,
        )

    if db_path is not None:
        result = await _with_db_file(db_path, _run)
    else:
        result = await _with_db(_run)

    print(file=sys.stderr)
    print("Ingest-dir completed.")

    for item in result.results:
        print(f"  [{item.language_code}] chunks={item.chunk_count} embedded={item.embedded}")

    return 0


async def cmd_ingest_all(*, rebuild: bool) -> int:
    """
    Ingest every schema in backend/data (shorthand for ``ingest-dir --dir data``).
    """

    return await cmd_ingest_dir("data", rebuild=rebuild)


async def cmd_stats(language_code: str | None) -> int:
    """
    Print chunk counts by content type.
    """

    result = await _with_db(lambda db: ETLService(db).stats(language_code=language_code))
    prefix = f"[{result.language_code}] " if result.language_code else ""
    print(f"{prefix}Total chunks: {result.total}")

    for content_type, count in sorted(result.by_content_type.items()):
        print(f"  {content_type}: {count}")

    return 0


async def cmd_manifest(language_code: str) -> int:
    """
    Print latest index manifest.
    """

    result = await _with_db(lambda db: ETLService(db).manifest(language_code=language_code))

    print(f"language_code:   {result.language_code}")
    print(f"source_path:     {result.source_path}")
    print(f"doc_hash:        {result.doc_hash}")
    print(f"embedding_model: {result.embedding_model}")
    print(f"chunker_version: {result.chunker_version}")
    print(f"chunk_count:     {result.chunk_count}")
    print(f"built_at:        {result.built_at.isoformat()}")

    return 0


async def cmd_schema_ingest(
    schema_path: str,
    *,
    source_path: str | None,
    output_root: str | None,
    run_id: str | None,
    no_embed: bool,
    allow_overwrite: bool,
) -> int:
    """
    Run schema-driven ingest into an isolated output directory.
    """

    result = await SchemaETLService().ingest(
        schema_path=schema_path,
        source_path=source_path,
        output_root=output_root,
        run_id=run_id,
        no_embed=no_embed,
        allow_overwrite=allow_overwrite,
    )

    print("Schema ingest completed.")
    print(f"  schema_path:      {result.schema_path}")
    print(f"  language_code:    {result.language_code}")
    print(f"  source_path:      {result.source_path}")
    print(f"  output_root:      {result.output_root}")
    print(f"  chunk_count:      {result.chunk_count}")
    print(f"  doc_hash:         {result.doc_hash}")
    print(f"  chunker_version:  {result.chunker_version}")
    print(f"  embedded (API):   {result.embedded}")
    print(f"  chunks_export:    {result.chunks_export_path}")
    print(f"  manifest_path:    {result.manifest_path}")
    print(f"  faiss_index_path: {result.faiss_index_path or '<skipped>'}")

    return 0


def _prompt_text(prompt: str, *, default: str | None = None, required: bool = False) -> str | None:
    """
    Read one text value from stdin with optional default.
    """

    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()

        if value:
            return value

        if default is not None:
            return default

        if not required:
            return None

        print("Value is required.")


def _interactive_command() -> Callable[[], Coroutine[Any, Any, int]]:
    """
    Ask for a schemas directory and run ingest-dir on it.
    """

    print("Interactive ETL mode")
    schemas_dir = _prompt_text("Schemas directory", default="data", required=True) or "data"

    return lambda: cmd_ingest_dir(schemas_dir, rebuild=False)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run ETL ingest and index maintenance (same as /api/etl endpoints).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_schema = subparsers.add_parser(
        "ingest-schema",
        help="Ingest one chunking schema JSON into SQLite + FAISS",
    )
    ingest_schema.add_argument(
        "--schema",
        metavar="PATH",
        required=True,
        help="Path to chunking schema JSON (relative to backend root or absolute)",
    )
    ingest_schema.add_argument(
        "--source",
        metavar="PATH",
        default=None,
        help="Markdown source path override (relative to schema directory or absolute)",
    )
    ingest_schema.add_argument(
        "--rebuild",
        action="store_true",
        help="Force full re-embed (ignore reusable vectors and checkpoint)",
    )
    ingest_dir = subparsers.add_parser(
        "ingest-dir",
        help="Discover schema JSON files in a directory and ingest each into SQLite + FAISS",
    )
    ingest_dir.add_argument(
        "--dir",
        metavar="PATH",
        required=True,
        help="Directory with chunking-schema-*.json files (relative to backend root or absolute)",
    )
    ingest_dir.add_argument(
        "--rebuild",
        action="store_true",
        help="Force full re-embed (ignore reusable vectors and checkpoint)",
    )
    ingest_all = subparsers.add_parser(
        "ingest-all",
        help="Ingest every schema in backend/data (same as ingest-dir --dir data)",
    )
    ingest_all.add_argument(
        "--rebuild",
        action="store_true",
        help="Force full re-embed (ignore reusable vectors and checkpoint)",
    )

    stats = subparsers.add_parser("stats", help="Show chunk counts by content_type")
    stats.add_argument(
        "--lang",
        metavar="CODE",
        default=None,
        help="Filter stats to one language",
    )

    manifest = subparsers.add_parser("manifest", help="Show latest index manifest")
    manifest.add_argument(
        "--lang",
        metavar="CODE",
        default="ru",
        help="Knowledge-base language code (default: ru)",
    )

    schema_ingest = subparsers.add_parser(
        "schema-ingest",
        help="Run schema-driven ingest to isolated output (no app DB writes)",
    )
    schema_ingest.add_argument(
        "--schema",
        metavar="PATH",
        required=True,
        help="Path to chunking schema JSON file",
    )
    schema_ingest.add_argument(
        "--source",
        metavar="PATH",
        default=None,
        help="Optional source markdown path override",
    )
    schema_ingest.add_argument(
        "--output-root",
        metavar="PATH",
        default=None,
        help="Optional output root override (keeps production FAISS untouched)",
    )
    schema_ingest.add_argument(
        "--run-id",
        metavar="ID",
        default=None,
        help="Optional run namespace appended under output root",
    )
    schema_ingest.add_argument(
        "--no-embed",
        action="store_true",
        help="Skip embeddings and FAISS build, export chunks + manifest only",
    )
    schema_ingest.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="Allow overwrite even if schema overwrite_policy is forbid",
    )

    return parser


def main() -> None:
    """
    CLI entrypoint.
    """

    if len(sys.argv) == 1:
        command = _interactive_command()
    else:
        args = _build_parser().parse_args()
        commands: dict[str, Callable[[], Coroutine[Any, Any, int]]] = {
            "ingest-schema": lambda: cmd_ingest_schema(
                args.schema,
                args.source,
                rebuild=args.rebuild,
            ),
            "ingest-dir": lambda: cmd_ingest_dir(args.dir, rebuild=args.rebuild),
            "ingest-all": lambda: cmd_ingest_all(rebuild=args.rebuild),
            "stats": lambda: cmd_stats(args.lang),
            "manifest": lambda: cmd_manifest(args.lang),
            "schema-ingest": lambda: cmd_schema_ingest(
                args.schema,
                source_path=args.source,
                output_root=args.output_root,
                run_id=args.run_id,
                no_embed=args.no_embed,
                allow_overwrite=args.allow_overwrite,
            ),
        }
        command = commands[args.command]

    try:
        exit_code = asyncio.run(command())

    except IngestInterruptedError as exc:
        print(file=sys.stderr)
        print(
            f"Ingest interrupted after {exc.embedded}/{exc.total} chunks.",
            file=sys.stderr,
        )
        print("Checkpoint saved. Re-run the same ingest command to resume.", file=sys.stderr)
        logger.info(
            "etl_ingest_interrupted",
            embedded=exc.embedded,
            total=exc.total,
        )
        exit_code = 130

    except KeyboardInterrupt:
        print(file=sys.stderr)
        print("Ingest interrupted.", file=sys.stderr)
        logger.info("etl_ingest_interrupted_keyboard")
        exit_code = 130

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
