"""Application exceptions and DB error helpers."""

from app.exceptions.base import BaseCustomException, register_exception_handlers
from app.exceptions.database import (
    DatabaseConnectionTimeoutError,
    DatabaseMultipleResultsError,
    DatabaseNoResultError,
    DatabaseServiceError,
    DatabaseUniqueFieldError,
    DatabaseUpdateError,
)
from app.exceptions.db_errors import handle_basic_db_errors
from app.exceptions.service import ServiceError

__all__ = [
    "BaseCustomException",
    "DatabaseConnectionTimeoutError",
    "DatabaseMultipleResultsError",
    "DatabaseNoResultError",
    "DatabaseServiceError",
    "DatabaseUniqueFieldError",
    "DatabaseUpdateError",
    "ServiceError",
    "handle_basic_db_errors",
    "register_exception_handlers",
]
