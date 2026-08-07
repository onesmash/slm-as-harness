from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeLimits:
    """Shared protocol limits for untrusted host and workflow payloads."""

    max_request_bytes: int = 512 * 1024
    max_observation_bytes: int = 1024 * 1024
    max_structured_output_bytes: int = 512 * 1024
    max_raw_output_bytes: int = 256 * 1024
    max_string_bytes: int = 128 * 1024
    max_list_items: int = 2048
    max_object_keys: int = 2048
    max_depth: int = 32
    max_artifacts: int = 256
    max_artifact_bytes: int = 256 * 1024
    max_tool_trace_entries: int = 256
    max_trace_metadata_bytes: int = 64 * 1024
    max_verifier_output_bytes: int = 64 * 1024
    max_history_entries: int = 256
    max_history_bytes: int = 256 * 1024


DEFAULT_RUNTIME_LIMITS = RuntimeLimits()


class PayloadLimitError(ValueError):
    """Raised when a JSON payload exceeds a runtime-owned limit."""

    code = "payload_too_large"

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


def json_byte_size(value: Any) -> int:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not valid finite JSON: {exc}") from exc
    return len(encoded)


def validate_json_limits(
    value: Any,
    *,
    path: str,
    limits: RuntimeLimits = DEFAULT_RUNTIME_LIMITS,
    max_bytes: int | None = None,
) -> None:
    """Validate JSON shape/resource usage without interpreting business fields."""

    encoded_size = json_byte_size(value)
    if max_bytes is not None and encoded_size > max_bytes:
        raise PayloadLimitError(path, f"payload is {encoded_size} bytes; limit is {max_bytes}")
    _walk_json_limits(value, path=path, depth=0, limits=limits)


def validate_observation_payload(
    payload: Any,
    *,
    limits: RuntimeLimits = DEFAULT_RUNTIME_LIMITS,
) -> None:
    validate_json_limits(
        payload,
        path="observation",
        limits=limits,
        max_bytes=limits.max_observation_bytes,
    )
    if not isinstance(payload, dict):
        return
    raw_output = payload.get("raw_output", "")
    if isinstance(raw_output, str) and len(raw_output.encode("utf-8")) > limits.max_raw_output_bytes:
        raise PayloadLimitError(
            "observation.raw_output",
            f"raw output exceeds {limits.max_raw_output_bytes} bytes",
        )
    structured_output = payload.get("structured_output")
    if structured_output is not None:
        validate_json_limits(
            structured_output,
            path="observation.structured_output",
            limits=limits,
            max_bytes=limits.max_structured_output_bytes,
        )
    artifacts = payload.get("artifacts", [])
    if isinstance(artifacts, list):
        if len(artifacts) > limits.max_artifacts:
            raise PayloadLimitError(
                "observation.artifacts",
                f"artifact count exceeds {limits.max_artifacts}",
            )
        for index, artifact in enumerate(artifacts):
            validate_json_limits(
                artifact,
                path=f"observation.artifacts[{index}]",
                limits=limits,
                max_bytes=limits.max_artifact_bytes,
            )
    tool_trace = payload.get("tool_trace", [])
    if isinstance(tool_trace, list) and len(tool_trace) > limits.max_tool_trace_entries:
        raise PayloadLimitError(
            "observation.tool_trace",
            f"tool trace entry count exceeds {limits.max_tool_trace_entries}",
        )
    if isinstance(tool_trace, list):
        for index, entry in enumerate(tool_trace):
            if isinstance(entry, dict) and "metadata" in entry:
                validate_json_limits(
                    entry["metadata"],
                    path=f"observation.tool_trace[{index}].metadata",
                    limits=limits,
                    max_bytes=limits.max_trace_metadata_bytes,
                )


def _walk_json_limits(value: Any, *, path: str, depth: int, limits: RuntimeLimits) -> None:
    if depth > limits.max_depth:
        raise PayloadLimitError(path, f"nested depth exceeds {limits.max_depth}")
    if isinstance(value, str):
        size = len(value.encode("utf-8"))
        if size > limits.max_string_bytes:
            raise PayloadLimitError(path, f"string is {size} bytes; limit is {limits.max_string_bytes}")
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} must not contain NaN or Infinity")
    if isinstance(value, list):
        if len(value) > limits.max_list_items:
            raise PayloadLimitError(path, f"list has {len(value)} items; limit is {limits.max_list_items}")
        for index, item in enumerate(value):
            _walk_json_limits(item, path=f"{path}[{index}]", depth=depth + 1, limits=limits)
        return
    if isinstance(value, dict):
        if len(value) > limits.max_object_keys:
            raise PayloadLimitError(path, f"object has {len(value)} keys; limit is {limits.max_object_keys}")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} keys must be strings")
            _walk_json_limits(item, path=f"{path}.{key}", depth=depth + 1, limits=limits)
