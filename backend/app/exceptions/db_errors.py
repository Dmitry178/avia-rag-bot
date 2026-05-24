import httpx

from functools import wraps
from inspect import iscoroutinefunction

from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound, SQLAlchemyError

from app.exceptions.base import BaseCustomException
from app.exceptions.database import (
    DatabaseMultipleResultsError,
    DatabaseNoResultError,
    DatabaseServiceError,
    DatabaseUniqueFieldError,
)
from app.exceptions.service import ServiceError


def _is_unique_violation(error: IntegrityError) -> bool:
    """
    Detect unique-constraint violations (Postgres, SQLite).
    """

    orig = getattr(error, "orig", None)
    if orig is None:
        return False

    if getattr(orig, "pgcode", None) == "23505":
        return True

    message = str(orig).lower()

    return (
        "unique constraint failed" in message  # SQLite
        or "duplicate key value" in message  # Postgres
        or "unique key constraint" in message
    )


def _unique_violation_extra(error: IntegrityError) -> dict[str, str]:
    """
    Build optional metadata for unique-violation responses.
    """

    orig = getattr(error, "orig", None)
    pgcode = getattr(orig, "pgcode", None)
    if pgcode == "23505":
        return {"pgcode": pgcode}

    return {}


def _exception_detail(exc: Exception) -> str:
    """
    Prefer structured app errors, otherwise surface the underlying message.
    """

    if isinstance(exc, BaseCustomException):
        return exc.detail

    message = str(exc).strip()
    if message:
        return message

    cause = exc.__cause__ or exc.__context__
    if cause is not None:
        return _exception_detail(cause)

    return ServiceError.detail


def _map_exception(exc: Exception) -> Exception:
    if isinstance(exc, NoResultFound):
        return DatabaseNoResultError()

    if isinstance(exc, MultipleResultsFound):
        return DatabaseMultipleResultsError()

    if isinstance(exc, IntegrityError):
        if _is_unique_violation(exc):
            extra = _unique_violation_extra(exc)
            return DatabaseUniqueFieldError(extra=extra or None)
        return DatabaseServiceError(extra={"kind": "integrity_error"})

    if isinstance(exc, SQLAlchemyError):
        return DatabaseServiceError(extra={"kind": "sqlalchemy_error"})

    if isinstance(exc, httpx.HTTPError):
        return ServiceError(
            detail=_exception_detail(exc),
            error_code="external_api_error",
            status_code=502,
            extra={"kind": type(exc).__name__},
        )

    return ServiceError(
        detail=_exception_detail(exc),
        error_code="internal_error",
        extra={"kind": type(exc).__name__},
    )


def handle_basic_db_errors(func):
    """
    Wrap service/repository methods and normalize low-level DB errors.
    """

    if iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseCustomException:
                raise
            except Exception as exc:  # noqa: BLE001
                raise _map_exception(exc) from exc

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseCustomException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise _map_exception(exc) from exc

    return sync_wrapper
