"""Shared Pydantic field types."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BeforeValidator


def ensure_utc_datetime(value: datetime) -> datetime:
    """
    Normalize naive datetimes from SQLite as UTC-aware values for JSON output.
    """

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


UtcDatetime = Annotated[datetime, BeforeValidator(ensure_utc_datetime)]
