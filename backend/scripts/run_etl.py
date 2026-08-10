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
from app.exceptions.ingest import IngestInterruptedError
from app.services.etl import ETLService
from app.services.etl_progress import IngestProgress
from app.services.schema_etl import SchemaETLService


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


async def cmd_ingest(
    language_code: str,
    source_path: str | None,
    *,
    rebuild: bool,
) -> int:
    """
    Run document ingest (incremental by default, with progress output).
    """

    async def _run(db: DBManager):
        return await ETLService(db).ingest(
            language_code=language_code,
            rebuild=rebuild,
            source_path=source_path,
            on_progress=_print_progress,
        )

    result = await _with_db(_run)

    print(file=sys.stderr)
    print("Ingest completed.")
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


async def cmd_ingest_all(*, rebuild: bool) -> int:
    """
    Run document ingest for all active knowledge-base languages.
    """

    async def _run(db: DBManager):
        return await ETLService(db).ingest_all(rebuild=rebuild, on_progress=_print_progress)

    result = await _with_db(_run)

    print(file=sys.stderr)
    print("Ingest-all completed.")

    for item in result.results:
        print(f"  [{item.language_code}] chunks={item.chunk_count} embedded={item.embedded}")

    return 0


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


def _prompt_bool(prompt: str, *, default: bool = False) -> bool:
    """
    Read yes/no flag from stdin.
    """

    label = "Y/n" if default else "y/N"

    while True:
        value = input(f"{prompt} ({label}): ").strip().lower()

        if not value:
            return default

        if value in {"y", "yes"}:
            return True

        if value in {"n", "no"}:
            return False

        print("Please answer y or n.")


def _interactive_command() -> Callable[[], Coroutine[Any, Any, int]]:
    """
    Build command coroutine from interactive stdin prompts.
    """

    print("Interactive ETL mode")
    print("1) ingest")
    print("2) ingest-all")
    print("3) stats")
    print("4) manifest")
    print("5) schema-ingest")

    choice = _prompt_text("Select command number", default="1", required=True)
    if choice == "1":
        language_code = _prompt_text("Language code", default="ru") or "ru"
        source_path = _prompt_text("Source markdown path override", default=None)
        rebuild = _prompt_bool("Force rebuild", default=False)
        return lambda: cmd_ingest(language_code, source_path, rebuild=rebuild)

    if choice == "2":
        rebuild = _prompt_bool("Force rebuild for all languages", default=False)
        return lambda: cmd_ingest_all(rebuild=rebuild)

    if choice == "3":
        language_code = _prompt_text("Language code filter (empty = all)", default=None)
        return lambda: cmd_stats(language_code)

    if choice == "4":
        language_code = _prompt_text("Language code", default="ru") or "ru"
        return lambda: cmd_manifest(language_code)

    if choice == "5":
        schema_path = _prompt_text("Schema path", required=True)
        source_path = _prompt_text("Source markdown path override", default=None)
        output_root = _prompt_text("Output root override", default=None)
        run_id = _prompt_text("Run id (namespace under output root)", default=None)
        no_embed = _prompt_bool("Skip embeddings and FAISS build", default=False)
        allow_overwrite = _prompt_bool("Allow overwrite and production-path override", default=False)

        return lambda: cmd_schema_ingest(
            schema_path or "",
            source_path=source_path,
            output_root=output_root,
            run_id=run_id,
            no_embed=no_embed,
            allow_overwrite=allow_overwrite,
        )

    raise ValueError(f"Unknown command selection: {choice}")


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
        "--lang",
        metavar="CODE",
        default="ru",
        help="Knowledge-base language code (default: ru)",
    )
    ingest.add_argument(
        "--source",
        metavar="PATH",
        default=None,
        help="Markdown source path override (relative to backend root or absolute)",
    )
    ingest.add_argument(
        "--rebuild",
        action="store_true",
        help="Force full re-embed (ignore reusable vectors and checkpoint)",
    )

    ingest_all = subparsers.add_parser(
        "ingest-all",
        help="Ingest all active knowledge-base languages",
    )
    ingest_all.add_argument(
        "--rebuild",
        action="store_true",
        help="Force full re-embed for every language",
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
            "ingest": lambda: cmd_ingest(args.lang, args.source, rebuild=args.rebuild),
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
