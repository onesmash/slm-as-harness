from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from runtime.errors import TransportValidationError
from runtime.limits import validate_json_limits


_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:/-]{1,256}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_STATUSES = {"succeeded", "failed", "partial", "blocked"}
_PHASES = {"spawn", "progress", "wait", "join", "complete", "timeout", "failure"}
MAX_RECEIPTS = 256
MAX_ARTIFACT_REFS = 256
MAX_SUMMARY_BYTES = 16 * 1024
MAX_RECEIPT_METADATA_BYTES = 64 * 1024
_RECEIPT_CORE_METADATA_KEYS = frozenset(
    {
        "receipt_id",
        "tool_name",
        "trace_id",
        "phase",
        "status",
        "summary",
        "artifact_refs",
        "join_id",
        "timed_out",
        "partial_failure",
        "missing_fields",
    }
)


@dataclass(frozen=True)
class CanonicalArtifactRef:
    uri: str
    size_bytes: int
    sha256: str
    media_type: str = "application/octet-stream"

    @classmethod
    def from_dict(cls, payload: object, *, path: str) -> "CanonicalArtifactRef":
        if not isinstance(payload, dict):
            raise TransportValidationError(f"{path} must be an object")
        uri = payload.get("uri")
        size_bytes = payload.get("size_bytes")
        sha256 = payload.get("sha256")
        media_type = payload.get("media_type", "application/octet-stream")
        if (
            not isinstance(uri, str)
            or not _ID_PATTERN.fullmatch(uri)
            or not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 0
            or not isinstance(sha256, str)
            or not _SHA256_PATTERN.fullmatch(sha256)
            or not isinstance(media_type, str)
            or not media_type.strip()
            or len(media_type) > 128
        ):
            raise TransportValidationError(f"{path} is not a valid artifact reference")
        return cls(
            uri=uri,
            size_bytes=size_bytes,
            sha256=sha256,
            media_type=media_type.strip()[:128],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class CanonicalReceipt:
    receipt_id: str
    tool_name: str
    trace_id: str
    phase: str
    status: str
    summary: str
    # Opaque adapter metadata is retained for workflow-owned transport
    # contracts (for example, Co-STORM expert/run identity). Runtime only
    # bounds and transports it; it does not interpret domain keys.
    metadata: dict[str, Any] = field(default_factory=dict)
    artifact_refs: tuple[CanonicalArtifactRef, ...] = field(default_factory=tuple)
    join_id: str | None = None
    timed_out: bool = False
    partial_failure: bool = False
    missing_fields: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, payload: object, *, path: str) -> "CanonicalReceipt":
        if not isinstance(payload, dict):
            raise TransportValidationError(f"{path} must be an object")
        receipt_id = _required_id(payload.get("receipt_id"), f"{path}.receipt_id")
        tool_name = _required_id(payload.get("tool_name"), f"{path}.tool_name")
        trace_id = _required_id(payload.get("trace_id"), f"{path}.trace_id")
        phase = payload.get("phase")
        status = payload.get("status")
        summary = payload.get("summary", "")
        if phase not in _PHASES:
            raise TransportValidationError(f"{path}.phase is unsupported")
        if status not in _STATUSES:
            raise TransportValidationError(f"{path}.status is unsupported")
        if not isinstance(summary, str) or len(summary.encode("utf-8")) > MAX_SUMMARY_BYTES:
            raise TransportValidationError(f"{path}.summary exceeds its limit")
        raw_metadata = payload.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raise TransportValidationError(f"{path}.metadata must be an object")
        try:
            validate_json_limits(
                raw_metadata,
                path=f"{path}.metadata",
                max_bytes=MAX_RECEIPT_METADATA_BYTES,
            )
        except (TypeError, ValueError) as exc:
            raise TransportValidationError(f"{path}.metadata is not bounded JSON: {exc}") from exc
        reserved_metadata = sorted(_RECEIPT_CORE_METADATA_KEYS.intersection(raw_metadata))
        if reserved_metadata:
            raise TransportValidationError(
                f"{path}.metadata cannot shadow canonical fields: {', '.join(reserved_metadata)}"
            )
        join_id = payload.get("join_id")
        if join_id is not None:
            join_id = _required_id(join_id, f"{path}.join_id")
        timed_out = payload.get("timed_out", False)
        partial_failure = payload.get("partial_failure", False)
        if not isinstance(timed_out, bool) or not isinstance(partial_failure, bool):
            raise TransportValidationError(f"{path} timeout flags must be boolean")
        missing_fields: tuple[str, ...] = ()
        if phase == "join" and not join_id:
            missing_fields = ("join_id",)
            partial_failure = True
            if status == "succeeded":
                status = "partial"
            if not summary:
                summary = "join receipt is missing join_id"
        raw_refs = payload.get("artifact_refs", [])
        if not isinstance(raw_refs, list) or len(raw_refs) > MAX_ARTIFACT_REFS:
            raise TransportValidationError(f"{path}.artifact_refs exceeds its limit")
        refs = tuple(
            CanonicalArtifactRef.from_dict(item, path=f"{path}.artifact_refs[{index}]")
            for index, item in enumerate(raw_refs)
        )
        return cls(
            receipt_id=receipt_id,
            tool_name=tool_name,
            trace_id=trace_id,
            phase=phase,
            status=status,
            summary=summary,
            metadata=dict(raw_metadata),
            artifact_refs=refs,
            join_id=join_id,
            timed_out=timed_out,
            partial_failure=partial_failure,
            missing_fields=missing_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "receipt_id": self.receipt_id,
            "tool_name": self.tool_name,
            "trace_id": self.trace_id,
            "phase": self.phase,
            "status": self.status,
            "summary": self.summary,
            "metadata": dict(self.metadata),
            "artifact_refs": [item.to_dict() for item in self.artifact_refs],
            "timed_out": self.timed_out,
            "partial_failure": self.partial_failure,
            "missing_fields": list(self.missing_fields),
        }
        if self.join_id is not None:
            result["join_id"] = self.join_id
        return result

    def to_tool_trace(self) -> dict[str, Any]:
        metadata = dict(self.metadata)
        metadata.update(
            {
                "receipt_id": self.receipt_id,
                "trace_id": self.trace_id,
                "phase": self.phase,
                "join_id": self.join_id,
                "timed_out": self.timed_out,
                "partial_failure": self.partial_failure,
                "missing_fields": list(self.missing_fields),
                "artifact_refs": [item.to_dict() for item in self.artifact_refs],
            }
        )
        return {
            "tool_name": self.tool_name,
            "status": self.status,
            "output_summary": self.summary,
            "artifact_refs": [item.uri for item in self.artifact_refs],
            "metadata": metadata,
        }


def canonicalize_native_receipts(
    receipts: object,
    *,
    run_id: str,
    step_id: str,
    base_status: str,
) -> tuple[list[dict[str, Any]], str]:
    """Convert adapter-owned native receipts into runtime ToolTrace entries.

    This function deliberately does not inspect structured business output.
    It only maps operational facts and upgrades a claimed success to partial or
    blocked when the execution facts say that the tool did not complete.
    """

    if not _ID_PATTERN.fullmatch(run_id) or not _ID_PATTERN.fullmatch(step_id):
        raise TransportValidationError("run_id and step_id must be stable identifiers")
    if base_status not in {"succeeded", "failed", "partial", "blocked"}:
        raise TransportValidationError("base observation status is unsupported")
    if not isinstance(receipts, list) or len(receipts) > MAX_RECEIPTS:
        raise TransportValidationError("native_receipts must be a bounded list")
    parsed: list[CanonicalReceipt] = []
    seen: set[str] = set()
    for index, item in enumerate(receipts):
        receipt = CanonicalReceipt.from_dict(item, path=f"native_receipts[{index}]")
        if receipt.receipt_id in seen:
            raise TransportValidationError("duplicate receipt_id in one observation")
        seen.add(receipt.receipt_id)
        parsed.append(receipt)

    normalized_status = base_status
    if any(item.timed_out or item.status == "blocked" for item in parsed):
        normalized_status = "blocked"
    elif any(item.partial_failure or item.status in {"partial", "failed"} for item in parsed):
        normalized_status = "partial" if base_status == "succeeded" else base_status
    trace_entries = [item.to_tool_trace() for item in parsed]
    return trace_entries, normalized_status


def canonicalize_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Normalize optional adapter-native receipts without changing workflow fields."""

    if not isinstance(observation, dict):
        raise TransportValidationError("observation must be an object")
    native_receipts = observation.get("native_receipts")
    if native_receipts is None:
        return dict(observation)
    normalized = dict(observation)
    normalized.pop("native_receipts", None)
    trace_entries, status = canonicalize_native_receipts(
        native_receipts,
        run_id=normalized.get("run_id", ""),
        step_id=normalized.get("step_id", ""),
        base_status=normalized.get("status", ""),
    )
    existing_trace = normalized.get("tool_trace", [])
    if not isinstance(existing_trace, list):
        raise TransportValidationError("tool_trace must be a list")
    normalized["tool_trace"] = existing_trace + trace_entries
    normalized["status"] = status
    return normalized


def _required_id(value: object, path: str) -> str:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise TransportValidationError(f"{path} must be a stable identifier")
    return value


def receipt_fingerprint(receipt: CanonicalReceipt) -> str:
    canonical = json.dumps(
        receipt.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
