"""Structured JSON logging to stdout, with PII masking by default."""

import json
import logging
import sys
from datetime import date, datetime, timezone
from typing import Any

from app.config import get_settings

# Fields whose values are masked in logs unless LOG_PII=true.
_SENSITIVE = {
    "first_name", "last_name", "date_of_birth", "phone_number", "email",
    "address_line_1", "address_line_2", "insurance_member_id",
    "emergency_contact_name", "emergency_contact_phone", "caller_number",
}


def mask_value(field: str, value: Any) -> Any:
    if value is None or field not in _SENSITIVE or get_settings().log_pii:
        return value
    text = value.isoformat() if isinstance(value, (date, datetime)) else str(value)
    if field in {"phone_number", "emergency_contact_phone", "caller_number"}:
        return f"***{text[-4:]}"
    if field == "date_of_birth":
        return f"****-**-** ({len(text)} chars)"
    if field in {"first_name", "last_name", "emergency_contact_name"}:
        return f"{text[:1]}***"
    return "***"


def redact(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: mask_value(k, v) for k, v in payload.items()}


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if extra:
            entry.update(extra)
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def log_event(logger: logging.Logger, msg: str, **fields: Any) -> None:
    logger.info(msg, extra={"fields": fields})
