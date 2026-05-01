from typing import Any

from fastapi import FastAPI, HTTPException, Request
from starlette import status
from starlette.responses import JSONResponse


class BaseCustomException(Exception):
    """
    Base application exception with unified API response payload.
    """

    status_code = status.HTTP_400_BAD_REQUEST
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

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to API response dictionary.
        """

        payload: dict[str, Any] = {
            "detail": self.detail,
            "error_code": self.error_code,
        }

        if self.extra:
            payload["extra"] = self.extra

        return payload

    @property
    def json_response(self) -> JSONResponse:
        """
        Return JSON response representation (backward-compatible helper).
        """

        return JSONResponse(status_code=self.status_code, content=self.to_dict())

    @property
    def http_exception(self) -> HTTPException:
        """
        Raise FastAPI HTTPException representation of this application error.
        """

        raise HTTPException(status_code=self.status_code, detail=self.detail)


async def base_custom_exception_handler(_request: Request, exc: BaseCustomException) -> JSONResponse:
    """
    Convert application exceptions to unified JSON responses.
    """

    return exc.json_response


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the FastAPI application.
    """

    app.add_exception_handler(BaseCustomException, base_custom_exception_handler)
