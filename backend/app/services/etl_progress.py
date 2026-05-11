"""ETL progress reporting."""

from collections.abc import Callable
from dataclasses import dataclass

IngestProgressCallback = Callable[["IngestProgress"], None]


@dataclass(frozen=True)
class IngestProgress:
    """
    Progress snapshot for CLI or logging during ingest.
    """

    phase: str
    current: int
    total: int
    overall_percent: int
