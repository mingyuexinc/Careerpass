"""Tests for safe structured logging helpers."""

import json
import logging

from app.core.logging import CareerPassLogFilter, JsonFormatter, redact_log_value
from app.core.request_context import reset_request_id, set_request_id


def test_redact_log_value_removes_sensitive_nested_data() -> None:
    value = {
        "authorization": "Bearer very-secret",
        "profile": {"email": "candidate@example.com", "skills": ["Python"]},
        "database_url": "postgresql://user:password@host/db",
    }

    assert redact_log_value(value) == {
        "authorization": "[REDACTED]",
        "profile": {"email": "[REDACTED]", "skills": ["Python"]},
        "database_url": "[REDACTED]",
    }


def test_json_formatter_emits_only_safe_fields_and_request_id() -> None:
    token = set_request_id("request-42")
    try:
        record = logging.makeLogRecord(
            {
                "name": "careerpass.request",
                "levelno": logging.INFO,
                "levelname": "INFO",
                "msg": "request_completed",
                "args": (),
                "method": "GET",
                "path": "/resume",
                "status_code": 200,
                "authorization": "Bearer never-log-me",
            }
        )
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["request_id"] == "request-42"
    assert payload["method"] == "GET"
    assert payload["path"] == "/resume"
    assert "authorization" not in payload


def test_careerpass_log_filter_rejects_third_party_logger_records() -> None:
    log_filter = CareerPassLogFilter()

    assert log_filter.filter(logging.makeLogRecord({"name": "careerpass.request"}))
    assert not log_filter.filter(logging.makeLogRecord({"name": "httpx"}))
