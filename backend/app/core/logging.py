"""Structured JSON logging with a per-request correlation ID.

Every log line is one JSON object on stdout. Docker keeps it, and Splunk
indexes it. Search a single request in Splunk with:  correlation_id="<id>"
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")
user_var: ContextVar[str] = ContextVar("user", default="-")

# Fields we never want in logs, even by accident (PII / PHI).
_BLOCKED_KEYS = {"first_name", "last_name", "date_of_birth", "weekly_salary", "tax_id", "password"}

_RESERVED = set(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
            "user": user_var.get(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = "***" if key in _BLOCKED_KEYS else value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's own access log duplicates ours; keep only errors from it.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
