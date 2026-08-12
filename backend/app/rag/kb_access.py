"""Read-only access to the knowledge-base SQLite (``data/kb.db``)."""

from datetime import UTC, datetime

from app.rag.types import ChunkRecord


def _chunk_record_from_src_row(row: object) -> ChunkRecord:
    """
    Map an mcp-rag ``ChunkMeta`` SQLModel row to a backend ``ChunkRecord``.
    """

    created_at = getattr(row, "created_at", None)
    if created_at is None:
        created_at = datetime.now(UTC)

    return ChunkRecord(
        language_code=str(getattr(row, "language_code", "")),
        id=getattr(row, "id", None),
        content=str(getattr(row, "content", "")),
        content_type=str(getattr(row, "content_type", "")),
        section=str(getattr(row, "section", "")),
        title=str(getattr(row, "title", "")),
        node_id=str(getattr(row, "node_id", "")),
        content_hash=str(getattr(row, "content_hash", "")),
        parent_id=getattr(row, "parent_id", None),
        token_count=int(getattr(row, "token_count", 0) or 0),
        source_path=str(getattr(row, "source_path", "")),
        created_at=created_at,
    )


async def load_chunks_by_ids(language_code: str, chunk_ids: list[int]) -> dict[int, ChunkRecord]:
    """
    Load chunk rows from the KB database for trace/message enrichment.
    """

    if not chunk_ids:
        return {}

    try:
        from src.core.db_manager import DBManager as KbDBManager
        from src.db.session import SessionLocal
    except ImportError:
        return {}

    async with KbDBManager(SessionLocal) as kb_db:
        rows = await kb_db.etl.chunks.list_by_ids(language_code, chunk_ids)

    result: dict[int, ChunkRecord] = {}

    for row in rows:
        record = _chunk_record_from_src_row(row)
        if record.id is not None:
            result[record.id] = record

    return result
