import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict

PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+"),
    re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b"),
    re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{4}\b"),
]


def redact_text(message: str) -> str:
    redacted = message
    for pattern in PII_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_value(value: Any):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def __init__(self, debug_content: bool = False):
        super().__init__()
        self.debug_content = debug_content

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            payload.update(getattr(record, "extra_data"))
        if not self.debug_content:
            payload = redact_value(payload)
        return json.dumps(payload)


def get_logger(name: str = "docetl", debug_content: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    desired_level = logging.DEBUG if os.getenv("DOCETL_DEBUG", "0") == "1" else logging.INFO
    formatter_debug = debug_content or os.getenv("DOCETL_DEBUG_CONTENT", "0") == "1"
    if logger.handlers:
        logger.setLevel(desired_level)
        return logger
    logger.setLevel(desired_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(debug_content=formatter_debug))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
