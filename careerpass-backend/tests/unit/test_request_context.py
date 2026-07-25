"""Tests for request correlation ID validation."""

from app.core.request_context import resolve_request_id


def test_resolve_request_id_preserves_valid_upstream_value() -> None:
    assert resolve_request_id("edge.trace-42") == "edge.trace-42"


def test_resolve_request_id_replaces_invalid_or_missing_value() -> None:
    assert resolve_request_id(None)
    assert resolve_request_id("invalid value with spaces") != "invalid value with spaces"
    assert resolve_request_id("x" * 65) != "x" * 65
