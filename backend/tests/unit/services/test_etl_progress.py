"""Unit tests for ETL progress helpers."""

from app.services.etl import ETLService
from etl.types import ChunkDraft, ContentType


def _draft(section: str, title: str) -> ChunkDraft:
    return ChunkDraft(
        content=f"{section}:{title}",
        content_type=ContentType.FAQ,
        section=section,
        title=title,
        node_id="n",
        content_hash=f"{section}:{title}",
    )


def test_chunk_progress_context_returns_section_counters() -> None:
    """
    Progress context should expose H1 section name and per-section completion.
    """

    drafts = [
        _draft("14. FAQ", "Question A"),
        _draft("14. FAQ", "Question B"),
        _draft("15. Глоссарий", "Term"),
    ]
    ordered_indices = [0, 1, 2]

    section, title, section_current, section_total = ETLService._chunk_progress_context(
        drafts,
        ordered_indices,
        completed_count=2,
    )

    assert section == "14. FAQ"
    assert title == "Question B"
    assert section_current == 2
    assert section_total == 2
