"""Tests for the response contract factories."""

from app.core.errors import ErrorCode
from app.schemas.response import error_response, success_response


def test_success_response_uses_required_contract() -> None:
    assert success_response({"key": "value"}) == {
        "code": 200,
        "msg": "success",
        "data": {"key": "value"},
    }


def test_success_response_accepts_contract_specific_success_code() -> None:
    assert success_response({"resume_id": "resume-1"}, msg="accepted", code=201) == {
        "code": 201,
        "msg": "accepted",
        "data": {"resume_id": "resume-1"},
    }


def test_error_response_has_null_data() -> None:
    assert error_response(code=ErrorCode.NOT_FOUND, msg="not found") == {
        "code": 404,
        "msg": "not found",
        "data": None,
    }
