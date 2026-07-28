"""Factories for the mandatory CareerPass response envelope."""

from typing import Any

from app.core.errors import ErrorCode


def success_response(
    data: Any,
    msg: str = "success",
    code: int | ErrorCode = ErrorCode.SUCCESS,
) -> dict[str, Any]:
    """Create a successful response using the project-wide envelope."""
    return {"code": int(code), "msg": msg, "data": data}


def error_response(*, code: ErrorCode, msg: str) -> dict[str, Any]:
    """Create a safe error response using the project-wide envelope."""
    return {"code": int(code), "msg": msg, "data": None}
