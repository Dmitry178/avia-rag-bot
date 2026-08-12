"""ETL progress reporting."""

from collections.abc import Callable
from dataclasses import dataclass

IngestProgressCallback = Callable[["IngestProgress"], None]


@dataclass(frozen=True)
class IngestProgress:
    """
    Progress snapshot for CLI or logging during ingest.

    Optional section fields describe the document chapter (H1) and item being
    processed; section_current/section_total give per-chapter progress when set.
    """

    phase: str
    current: int
    total: int
    overall_percent: int
    section: str | None = None
    item_title: str | None = None
    section_current: int | None = None
    section_total: int | None = None
