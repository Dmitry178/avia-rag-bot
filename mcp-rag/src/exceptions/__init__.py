"""Application exceptions and DB error helpers."""

from src.exceptions.base import BaseCustomException
from src.exceptions.database import (
    DatabaseConnectionTimeoutError,
    DatabaseMultipleResultsError,
    DatabaseNoResultError,
    DatabaseServiceError,
    DatabaseUniqueFieldError,
    DatabaseUpdateError,
)
from src.exceptions.db_errors import handle_basic_db_errors
from src.exceptions.service import ServiceError

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
]
