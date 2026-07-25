"""Stable application error codes used in the API response envelope."""

from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 200
    VALIDATION_ERROR = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    TOO_MANY_REQUESTS = 429
    INTERNAL_ERROR = 500
