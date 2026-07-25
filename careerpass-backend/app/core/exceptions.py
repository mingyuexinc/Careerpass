"""Exception types and uniform FastAPI exception handlers."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import ErrorCode
from app.schemas.response import error_response

logger = logging.getLogger("careerpass.exceptions")


class AppException(Exception):
    """Known, safe-to-return application failure."""

    def __init__(self, *, status_code: int, code: ErrorCode, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _json_error(
    status_code: int,
    code: ErrorCode,
    message: str,
    request: Request | None = None,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content=error_response(code=code, msg=message),
    )
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def _http_error_code(status_code: int) -> ErrorCode:
    mapping: dict[int, ErrorCode] = {
        status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
        status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
        status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
        status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.TOO_MANY_REQUESTS,
    }
    return mapping.get(status_code, ErrorCode.INTERNAL_ERROR)


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers that preserve the mandatory response envelope."""

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return _json_error(exc.status_code, exc.code, exc.message, request)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        _: RequestValidationError,
    ) -> JSONResponse:
        return _json_error(
            status.HTTP_400_BAD_REQUEST,
            ErrorCode.VALIDATION_ERROR,
            "validation error",
            request,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        error_code = _http_error_code(exc.status_code)
        message = "not found" if error_code is ErrorCode.NOT_FOUND else "request failed"
        return _json_error(exc.status_code, error_code, message, request)

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled application exception on %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return _json_error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_ERROR,
            "internal server error",
            request,
        )
