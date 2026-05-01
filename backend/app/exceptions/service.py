"""Service-layer exceptions mapped to HTTP responses."""

from starlette import status

from app.exceptions.base import BaseCustomException


class ServiceError(BaseCustomException):
    """
    Raised for unexpected failures in service logic not covered by DB errors.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Service error"
    error_code = "service_error"
