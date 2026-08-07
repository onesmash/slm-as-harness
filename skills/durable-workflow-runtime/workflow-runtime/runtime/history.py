from __future__ import annotations

import hashlib
import json
from typing import Any

from runtime.redaction import redact_sensitive_json


MAX_HISTORY_ENTRIES = 256
MAX_HISTORY_BYTES = 256 * 1024
MAX_HISTORY_PAYLOAD_BYTES = 16 * 1024
MAX_HISTORY_VALUE_BYTES = 8 * 1024

_STATE_SNAPSHOT_KEYS = {
    "state",
    "graph_state",
    "run_state",
    "workflow_state",
    "state_snapshot",
    "context_snapshot",
}
_SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "credential",
    "password",
    "secret",
    "token",
}


def json_byte_size(value: Any) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


def compact_history_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Keep history diagnostic while excluding state snapshots and secrets."""

    compacted: dict[str, Any] = {}
    degraded = False
    for key, value in payload.items():
        if _is_state_snapshot_key(key):
            degraded = True
            continue
        if _is_sensitive_key(key):
            compacted[key] = "[REDACTED]"
            degraded = True
            continue
        compacted_value, value_degraded = _compact_value(value, key=key)
        compacted[key] = compacted_value
        degraded = degraded or value_degraded

    if json_byte_size(compacted) > MAX_HISTORY_PAYLOAD_BYTES:
        degraded = True
        compacted = _fit_payload_to_limit(compacted)
    return redact_sensitive_json(compacted), degraded


def trim_history(entries: list[Any]) -> tuple[list[Any], bool]:
    """Apply count and byte retention from oldest to newest entries."""

    degraded = False
    retained = list(entries)
    while len(retained) > MAX_HISTORY_ENTRIES:
        retained.pop(0)
        degraded = True
    while retained and _history_byte_size(retained) > MAX_HISTORY_BYTES:
        retained.pop(0)
        degraded = True
    return retained, degraded


def _compact_value(value: Any, *, key: str | None = None) -> tuple[Any, bool]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        degraded = False
        for child_key, child_value in value.items():
            if not isinstance(child_key, str):
                result[str(child_key)] = "[REDACTED]"
                degraded = True
                continue
            if _is_state_snapshot_key(child_key):
                degraded = True
                continue
            if _is_sensitive_key(child_key):
                result[child_key] = "[REDACTED]"
                degraded = True
                continue
            compacted_child, child_degraded = _compact_value(child_value, key=child_key)
            result[child_key] = compacted_child
            degraded = degraded or child_degraded
        return _summarize_if_large(result, degraded)
    if isinstance(value, list):
        result = []
        degraded = False
        for index, item in enumerate(value):
            compacted_item, item_degraded = _compact_value(item, key=str(index))
            result.append(compacted_item)
            degraded = degraded or item_degraded
        return _summarize_if_large(result, degraded)
    return _summarize_if_large(value, False)


def _summarize_if_large(value: Any, degraded: bool) -> tuple[Any, bool]:
    try:
        size = json_byte_size(value)
    except (TypeError, ValueError):
        return {"omitted": True, "reason": "non_json_value"}, True
    if size <= MAX_HISTORY_VALUE_BYTES:
        return value, degraded
    return {
        "omitted": True,
        "bytes": size,
        "sha256": _sha256_json(value),
    }, True


def _fit_payload_to_limit(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    while result and json_byte_size(result) > MAX_HISTORY_PAYLOAD_BYTES:
        largest_key = max(result, key=lambda key: json_byte_size(result[key]))
        value = result[largest_key]
        if isinstance(value, dict) and not value.get("omitted"):
            result[largest_key] = {
                "omitted": True,
                "bytes": json_byte_size(value),
                "sha256": _sha256_json(value),
            }
        elif isinstance(value, list) and not (
            len(value) == 3 and value[0] is True and value[1] == "bytes"
        ):
            result[largest_key] = {
                "omitted": True,
                "bytes": json_byte_size(value),
                "sha256": _sha256_json(value),
            }
        else:
            result.pop(largest_key)
    return result


def _history_byte_size(entries: list[Any]) -> int:
    return json_byte_size([entry.to_dict() for entry in entries])


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_state_snapshot_key(key: str) -> bool:
    return key.strip().lower() in _STATE_SNAPSHOT_KEYS


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)
