"""Base application exceptions (no FastAPI dependency)."""

from typing import Any


class BaseCustomException(Exception):
    """
    Base application exception with structured error fields.
    """

    status_code = 400
    detail = "Bad Request"
    error_code = "bad_request"

    def __init__(
        self,
        detail: str | None = None,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.detail
        self.error_code = error_code or self.error_code
        self.status_code = status_code or self.status_code
        self.extra = extra or {}
        super().__init__(self.detail)
