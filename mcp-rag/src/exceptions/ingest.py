"""ETL ingest lifecycle exceptions (not mapped to HTTP responses)."""


class IngestInterruptedError(Exception):
    """
    Raised when ingest is cancelled after saving the latest embedding checkpoint.
    """

    def __init__(self, *, embedded: int, total: int) -> None:
        self.embedded = embedded
        self.total = total
        super().__init__(f"Ingest interrupted after {embedded}/{total} chunks")
