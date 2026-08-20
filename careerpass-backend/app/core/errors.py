"""Stable application error codes used in the API response envelope."""

from enum import IntEnum


class ErrorCode(IntEnum):
    SUCCESS = 200
    UPLOAD_ACCEPTED = 201
    UPLOAD_SUCCEEDED = 201
    VALIDATION_ERROR = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    GONE = 410
    CONFLICT = 409
    PRECONDITION_NOT_MET = 409
    INTERNAL_ERROR = 500
