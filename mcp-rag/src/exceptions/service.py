"""Service-layer exceptions."""

from src.exceptions.base import BaseCustomException


class ServiceError(BaseCustomException):
    """
    Raised for unexpected failures in service logic not covered by DB errors.
    """

    status_code = 500
    detail = "Service error"
    error_code = "service_error"
