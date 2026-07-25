"""Structured, minimally scoped logging with sensitive-value redaction."""

import json
import logging
import re
from collections.abc import Mapping
from typing import Any

from app.core.request_context import get_request_id

_SENSITIVE_KEY_PARTS = frozenset(
    {
        "authorization",
        "cookie",
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "database_url",
        "connection_string",
        "email",
        "phone",
        "phone_number",
        "address",
        "resume",
        "raw_content",
    }
)
_DATABASE_URL_PATTERN = re.compile(r"\b(?:postgres(?:ql)?|redis)://[^\s]+", re.IGNORECASE)
_REDACTED = "[REDACTED]"
_SAFE_LOG_EXTRA_FIELDS = ("method", "path", "status_code", "duration_ms")


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def redact_log_value(value: Any, *, key: object | None = None) -> Any:
    """Recursively remove sensitive values before they reach a log formatter."""
    if key is not None and _is_sensitive_key(key):
        return _REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_log_value(item_value, key=item_key)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple | set | frozenset):
        return [redact_log_value(item) for item in value]
    if isinstance(value, str):
        return _DATABASE_URL_PATTERN.sub(_REDACTED, value)
    return value


class JsonFormatter(logging.Formatter):
    """Emit only whitelisted structured fields in JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "event": redact_log_value(record.getMessage()),
        }
        request_id = get_request_id()
        if request_id is not None:
            payload["request_id"] = request_id
        for field in _SAFE_LOG_EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = redact_log_value(getattr(record, field), key=field)
        return json.dumps(payload, ensure_ascii=False, default=str)


class CareerPassLogFilter(logging.Filter):
    """Keep third-party records out of the CareerPass structured log sink."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith("careerpass.")


def configure_logging(level_name: str) -> None:
    """Configure one managed JSON handler without disturbing test handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level_name)
    for handler in list(root_logger.handlers):
        if getattr(handler, "_careerpass_managed", False):
            root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler._careerpass_managed = True  # type: ignore[attr-defined]
    handler.addFilter(CareerPassLogFilter())
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
