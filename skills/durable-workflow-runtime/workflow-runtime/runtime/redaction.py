from __future__ import annotations

import re
from typing import Any


_SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|secret|credential)", re.IGNORECASE)
_ASSIGNMENT = re.compile(
    r"(?P<key>\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|secret|credential)\b)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<quote>['\"]?)(?P<value>[^\s,;}'\"]+)(?P=quote)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)


def redact_sensitive_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("redaction input must be text")
    redacted = _BEARER.sub("Bearer [REDACTED]", value)
    return _ASSIGNMENT.sub(
        lambda match: f"{match.group('key')}{match.group('separator')}[REDACTED]",
        redacted,
    )


def redact_sensitive_json(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if isinstance(key, str) and _SENSITIVE_KEY.search(key):
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_sensitive_json(child)
        return result
    if isinstance(value, list):
        return [redact_sensitive_json(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value
