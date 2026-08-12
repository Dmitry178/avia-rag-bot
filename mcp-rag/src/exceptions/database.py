"""Database-layer exceptions."""

from src.exceptions.base import BaseCustomException


class DatabaseNoResultError(BaseCustomException):
    """
    Raised when a query expected exactly one row but found none.
    """

    status_code = 404
    detail = "Object not found"
    error_code = "db_not_found"


class DatabaseMultipleResultsError(BaseCustomException):
    """
    Raised when a query expected at most one row but found multiple.
    """

    status_code = 409
    detail = "Multiple objects found"
    error_code = "db_multiple_results"


class DatabaseUniqueFieldError(BaseCustomException):
    """
    Raised when an insert or update violates a unique constraint.
    """

    status_code = 409
    detail = "Object already exists"
    error_code = "db_unique_violation"


class DatabaseServiceError(BaseCustomException):
    """
    Raised for generic SQLAlchemy or non-unique integrity failures.
    """

    status_code = 503
    detail = "Database error"
    error_code = "db_service_error"


class DatabaseConnectionTimeoutError(BaseCustomException):
    """
    Raised when the database server does not respond within the timeout.
    """

    status_code = 503
    detail = "Database server is unavailable"
    error_code = "db_connection_timeout"


class DatabaseUpdateError(BaseCustomException):
    """
    Raised when a persisted update operation fails unexpectedly.
    """

    status_code = 503
    detail = "Data update error"
    error_code = "db_update_error"
