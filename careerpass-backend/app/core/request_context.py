"""Request-scoped correlation context."""

from contextvars import ContextVar, Token
from re import compile
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_PATTERN = compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def resolve_request_id(candidate: str | None) -> str:
    """Use a safe upstream correlation ID or create a new opaque one."""
    if candidate and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())


def set_request_id(request_id: str) -> Token[str | None]:
    """Bind a request ID for the current async execution context."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Clear request context after a request is completed."""
    _request_id.reset(token)


def get_request_id() -> str | None:
    """Return the active request ID without creating a new value."""
    return _request_id.get()
