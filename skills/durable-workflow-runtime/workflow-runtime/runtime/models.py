from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TypeAlias

from runtime.history import (
    compact_history_payload,
    trim_history,
)
from runtime.limits import json_byte_size, validate_json_limits


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]

OBSERVATION_STATUSES = {"succeeded", "failed", "blocked", "partial"}
RUN_STATUSES = {"running", "waiting_for_host", "blocked", "done", "failed_terminal"}
WORKFLOW_RESPONSE_KINDS = {"yield", "done"}
CURRENT_RUN_STATE_VERSION = 3
MAX_OBSERVATION_ID_LENGTH = 256
MAX_RUNTIME_STEPS = 10_000
MAX_ARTIFACT_REFERENCE_COUNT = 256
MAX_OBSERVATION_REPLAYS = 64
MAX_OBSERVATION_REPLAY_BYTES = 4 * 1024 * 1024
MAX_OBSERVATION_REPLAY_ENTRY_BYTES = 1 * 1024 * 1024
_ARTIFACT_SHA256_LENGTH = 64
_MAX_ARTIFACT_REFERENCE_BYTES = 8 * 1024 * 1024
MAX_PROMPT_BYTES = 512 * 1024


def iso_utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


def _normalize_optional_identifier(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    identifier = _require_non_empty_string(value, field_name)
    if len(identifier) > MAX_OBSERVATION_ID_LENGTH:
        raise ValueError(f"{field_name} must be at most {MAX_OBSERVATION_ID_LENGTH} characters")
    return identifier


def _normalize_string_list(value: object, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    normalized: list[str] = []
    for item in value:
        text = _require_non_empty_string(item, field_name)
        if text not in normalized:
            normalized.append(text)
    return normalized


def _require_object(value: object, field_name: str) -> JSONObject:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    normalized: JSONObject = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} keys must be strings")
        normalized[key] = item
    return normalized


def _normalize_artifact_references(value: object, field_name: str) -> list[JSONObject]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if len(value) > MAX_ARTIFACT_REFERENCE_COUNT:
        raise ValueError(
            f"{field_name} cannot contain more than {MAX_ARTIFACT_REFERENCE_COUNT} entries"
        )
    normalized: list[JSONObject] = []
    seen_ids: set[str] = set()
    required_fields = {
        "artifact_id",
        "relative_path",
        "size_bytes",
        "sha256",
        "media_type",
        "created_at",
        "kind",
    }
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{field_name}[{index}] must be an object")
        missing = sorted(required_fields - set(item))
        if missing:
            raise ValueError(
                f"{field_name}[{index}] missing required fields: {', '.join(missing)}"
            )
        artifact_id = item["artifact_id"]
        relative_path = item["relative_path"]
        sha256 = item["sha256"]
        size_bytes = item["size_bytes"]
        if (
            not isinstance(artifact_id, str)
            or len(artifact_id) != _ARTIFACT_SHA256_LENGTH
            or any(char not in "0123456789abcdef" for char in artifact_id)
        ):
            raise ValueError(f"{field_name}[{index}].artifact_id must be a lowercase SHA-256")
        if (
            not isinstance(relative_path, str)
            or _unsafe_reference_path(relative_path)
            or len(relative_path) > 512
        ):
            raise ValueError(f"{field_name}[{index}].relative_path is unsafe")
        if not isinstance(sha256, str) or sha256 != artifact_id:
            raise ValueError(f"{field_name}[{index}].sha256 must match artifact_id")
        if (
            not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
            or size_bytes < 0
            or size_bytes > _MAX_ARTIFACT_REFERENCE_BYTES
        ):
            raise ValueError(f"{field_name}[{index}].size_bytes must be a non-negative integer")
        media_type = item["media_type"]
        kind = item["kind"]
        created_at = item["created_at"]
        if not isinstance(media_type, str) or not media_type.strip() or len(media_type) > 128:
            raise ValueError(f"{field_name}[{index}].media_type is invalid")
        if not isinstance(kind, str) or not kind.strip() or len(kind) > 128:
            raise ValueError(f"{field_name}[{index}].kind is invalid")
        if not isinstance(created_at, str) or not created_at.strip() or len(created_at) > 128:
            raise ValueError(f"{field_name}[{index}].created_at is invalid")
        if artifact_id in seen_ids:
            continue
        normalized.append(
            {
                "artifact_id": artifact_id,
                "relative_path": relative_path,
                "size_bytes": size_bytes,
                "sha256": sha256,
                "media_type": media_type.strip(),
                "created_at": created_at.strip(),
                "kind": kind.strip(),
            }
        )
        seen_ids.add(artifact_id)
    return normalized


def _unsafe_reference_path(value: str) -> bool:
    """Reject absolute, traversal, or control-character reference paths."""

    path = value.replace("\\", "/")
    return (
        path.startswith("/")
        or (len(path) >= 2 and path[1] == ":")
        or any(part in {"", ".", ".."} for part in path.split("/"))
        or any(ord(char) < 0x20 for char in path)
    )


def _normalize_observation_replays(value: object) -> dict[str, dict]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("observation_replays must be an object")
    normalized: dict[str, dict] = {}
    for observation_id, replay in value.items():
        identifier = _normalize_optional_identifier(observation_id, "observation_replays key")
        if identifier is None or not isinstance(replay, dict):
            raise ValueError("observation_replays entries must be objects")
        fingerprint = replay.get("fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint.strip():
            raise ValueError(f"observation_replays[{identifier}].fingerprint must be non-empty")
        response = replay.get("response")
        if not isinstance(response, dict):
            raise ValueError(f"observation_replays[{identifier}].response must be an object")
        try:
            validate_json_limits(
                response,
                path=f"observation_replays[{identifier}].response",
                max_bytes=MAX_OBSERVATION_REPLAY_ENTRY_BYTES,
            )
        except ValueError as exc:
            raise ValueError(f"invalid observation replay {identifier}: {exc}") from exc
        normalized[identifier] = {
            "fingerprint": fingerprint.strip(),
            "response": response,
        }
    _trim_observation_replays(normalized)
    return normalized


def _trim_observation_replays(replays: dict[str, dict]) -> None:
    while len(replays) > MAX_OBSERVATION_REPLAYS or (
        len(replays) > 1 and _observation_replay_bytes(replays) > MAX_OBSERVATION_REPLAY_BYTES
    ):
        replays.pop(next(iter(replays)))


def _observation_replay_bytes(replays: dict[str, dict]) -> int:
    return json_byte_size(replays)


def _require_top_level_fields(
    data: object,
    field_names: set[str],
    model_name: str,
    *,
    optional_fields: set[str] | None = None,
) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{model_name} must be an object")
    actual = set(data.keys())
    missing = sorted(field_names - actual)
    if missing:
        raise ValueError(f"{model_name} missing required fields: {', '.join(missing)}")
    optional_fields = optional_fields or set()
    allowed = field_names | optional_fields | {"caller"}
    extras = sorted(actual - allowed)
    if model_name != "StartRequest":
        allowed = field_names | optional_fields
        extras = sorted(actual - allowed)
    if extras:
        raise ValueError(f"{model_name} has unknown fields: {', '.join(extras)}")
    return data


@dataclass
class StartRequest:
    task_input: JSONValue
    context: JSONValue
    constraints: JSONObject
    caller: str | None = None

    @classmethod
    def from_dict(cls, data: object) -> "StartRequest":
        payload = _require_top_level_fields(
            data,
            {"task_input", "context", "constraints"},
            "StartRequest",
        )
        caller = payload.get("caller")
        if caller is not None:
            caller = _require_non_empty_string(caller, "caller")
        return cls(
            task_input=payload["task_input"],
            context=payload["context"],
            constraints=_require_object(payload["constraints"], "constraints"),
            caller=caller,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PromptEnvelope:
    run_id: str
    step_id: str
    prompt: str
    intent: str
    expected_artifact: str
    done_when: list[str] = field(default_factory=list)
    output_schema: JSONObject = field(default_factory=dict)
    failure_schema: JSONObject = field(default_factory=dict)
    resume_instructions: str = ""
    metadata: JSONObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.run_id = _require_non_empty_string(self.run_id, "run_id")
        self.step_id = _require_non_empty_string(self.step_id, "step_id")
        self.prompt = _require_non_empty_string(self.prompt, "prompt")
        if len(self.prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError(f"prompt exceeds {MAX_PROMPT_BYTES} bytes")
        self.intent = _require_non_empty_string(self.intent, "intent")
        self.expected_artifact = _require_non_empty_string(
            self.expected_artifact,
            "expected_artifact",
        )
        self.done_when = _normalize_string_list(self.done_when, "done_when")
        self.output_schema = _require_object(self.output_schema, "output_schema")
        self.failure_schema = _require_object(self.failure_schema, "failure_schema")
        self.resume_instructions = _require_non_empty_string(
            self.resume_instructions,
            "resume_instructions",
        )
        self.metadata = _require_object(self.metadata, "metadata")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ObservationError:
    type: str
    message: str
    details: JSONObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: object) -> "ObservationError":
        if not isinstance(data, dict):
            raise ValueError("ObservationError must be an object")
        missing = sorted({"type", "message"} - set(data.keys()))
        if missing:
            raise ValueError(
                f"ObservationError missing required fields: {', '.join(missing)}"
            )
        return cls(
            type=_require_non_empty_string(data["type"], "type"),
            message=_require_non_empty_string(data["message"], "message"),
            details=_require_object(data.get("details", {}), "details"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ToolTraceEntry:
    tool_name: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    artifact_refs: list[str] = field(default_factory=list)
    error_message: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    metadata: JSONObject = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: object) -> "ToolTraceEntry":
        if not isinstance(data, dict):
            raise ValueError("ToolTraceEntry must be an object")
        missing = sorted({"tool_name", "status"} - set(data.keys()))
        if missing:
            raise ValueError(f"ToolTraceEntry missing required fields: {', '.join(missing)}")
        error_message = data.get("error_message")
        started_at = data.get("started_at")
        ended_at = data.get("ended_at")
        metadata_payload = data.get("metadata", {})
        if not isinstance(metadata_payload, dict):
            raise ValueError("ToolTraceEntry metadata must be an object")
        metadata = dict(metadata_payload)
        # Host adapters may attach workflow- or vendor-specific trace
        # extensions at the entry's top level. Preserve those extensions
        # generically; the runtime model must not enumerate domain fields.
        core_fields = set(cls.__dataclass_fields__)
        for key, value in data.items():
            if key in core_fields:
                continue
            if key in metadata and metadata[key] != value:
                raise ValueError(
                    f"ToolTraceEntry flat and nested metadata conflict for {key}"
                )
            metadata.setdefault(key, value)
        return cls(
            tool_name=_require_non_empty_string(data["tool_name"], "tool_name"),
            status=_require_non_empty_string(data["status"], "status"),
            input_summary=str(data.get("input_summary", "")),
            output_summary=str(data.get("output_summary", "")),
            artifact_refs=_normalize_string_list(data.get("artifact_refs", []), "artifact_refs"),
            error_message=str(error_message) if error_message is not None else None,
            started_at=str(started_at) if started_at is not None else None,
            ended_at=str(ended_at) if ended_at is not None else None,
            metadata=_require_object(metadata, "metadata"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Observation:
    run_id: str
    step_id: str
    status: str
    summary: str
    structured_output: JSONValue
    artifacts: list[JSONValue] = field(default_factory=list)
    error: ObservationError | None = None
    tool_trace: list[ToolTraceEntry] = field(default_factory=list)
    raw_output: str = ""
    observation_id: str | None = None

    @classmethod
    def from_dict(cls, data: object) -> "Observation":
        if not isinstance(data, dict):
            raise ValueError("Observation must be an object")
        missing = sorted(
            {"run_id", "step_id", "status", "summary", "structured_output"} - set(data.keys())
        )
        if missing:
            raise ValueError(f"Observation missing required fields: {', '.join(missing)}")
        allowed = {
            "run_id",
            "step_id",
            "status",
            "summary",
            "structured_output",
            "artifacts",
            "error",
            "tool_trace",
            "raw_output",
            "observation_id",
            "attempt_id",
        }
        extras = sorted(set(data) - allowed)
        if extras:
            raise ValueError(f"Observation has unknown fields: {', '.join(extras)}")
        status = _require_non_empty_string(data["status"], "status")
        if status not in OBSERVATION_STATUSES:
            raise ValueError(f"unsupported observation status: {status}")
        tool_trace_payload = data.get("tool_trace", [])
        if not isinstance(tool_trace_payload, list):
            raise ValueError("tool_trace must be a list")
        artifacts = data.get("artifacts", [])
        if not isinstance(artifacts, list):
            raise ValueError("artifacts must be a list")
        error_payload = data.get("error")
        if error_payload is not None and not isinstance(error_payload, dict):
            raise ValueError("error must be an object or null")
        raw_output = data.get("raw_output", "")
        if not isinstance(raw_output, str):
            raise ValueError("raw_output must be a string")
        observation_id = _normalize_optional_identifier(
            data.get("observation_id"),
            "observation_id",
        )
        attempt_id = _normalize_optional_identifier(data.get("attempt_id"), "attempt_id")
        if observation_id is not None and attempt_id is not None and observation_id != attempt_id:
            raise ValueError("observation_id and attempt_id must match when both are supplied")
        return cls(
            run_id=_require_non_empty_string(data["run_id"], "run_id"),
            step_id=_require_non_empty_string(data["step_id"], "step_id"),
            status=status,
            summary=_require_non_empty_string(data["summary"], "summary"),
            structured_output=data["structured_output"],
            artifacts=list(artifacts),
            error=ObservationError.from_dict(error_payload)
            if isinstance(error_payload, dict)
            else None,
            tool_trace=[ToolTraceEntry.from_dict(item) for item in tool_trace_payload],
            raw_output=raw_output,
            observation_id=observation_id or attempt_id,
        )

    def to_dict(self) -> dict:
        result = asdict(self)
        if self.error is None:
            result["error"] = None
        if self.observation_id is None:
            result.pop("observation_id", None)
        return result


@dataclass
class YieldResponse:
    run_id: str
    step_id: str
    prompt_envelope: PromptEnvelope
    retry_context: dict | None = None
    kind: str = "yield"

    def __post_init__(self) -> None:
        if self.kind != "yield":
            raise ValueError("YieldResponse kind must be 'yield'")
        self.run_id = _require_non_empty_string(self.run_id, "run_id")
        self.step_id = _require_non_empty_string(self.step_id, "step_id")
        if self.run_id != self.prompt_envelope.run_id:
            raise ValueError("run_id must match prompt_envelope.run_id")
        if self.step_id != self.prompt_envelope.step_id:
            raise ValueError("step_id must match prompt_envelope.step_id")
        if self.retry_context is not None:
            if not isinstance(self.retry_context, dict):
                raise ValueError("retry_context must be a dict when present")
            category = _require_non_empty_string(
                self.retry_context.get("category"),
                "retry_context.category",
            )
            summary = _require_non_empty_string(
                self.retry_context.get("summary"),
                "retry_context.summary",
            )
            requirements = self.retry_context.get("requirements", [])
            if not isinstance(requirements, list):
                raise ValueError("retry_context.requirements must be a list")
            cleaned_requirements = [
                _require_non_empty_string(item, "retry_context.requirements[]")
                for item in requirements
            ]
            self.retry_context = {
                "category": category,
                "summary": summary,
                "requirements": cleaned_requirements,
            }

    def to_dict(self) -> dict:
        result = {
            "kind": self.kind,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "prompt_envelope": self.prompt_envelope.to_dict(),
        }
        if self.retry_context is not None:
            result["retry_context"] = dict(self.retry_context)
        return result


@dataclass
class DoneResponse:
    run_id: str
    step_id: str
    final_prompt_envelope: PromptEnvelope
    kind: str = "done"

    def __post_init__(self) -> None:
        if self.kind != "done":
            raise ValueError("DoneResponse kind must be 'done'")
        self.run_id = _require_non_empty_string(self.run_id, "run_id")
        self.step_id = _require_non_empty_string(self.step_id, "step_id")
        if self.run_id != self.final_prompt_envelope.run_id:
            raise ValueError("run_id must match final_prompt_envelope.run_id")
        if self.step_id != self.final_prompt_envelope.step_id:
            raise ValueError("step_id must match final_prompt_envelope.step_id")

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "final_prompt_envelope": self.final_prompt_envelope.to_dict(),
        }


@dataclass
class HistoryEntry:
    timestamp: str
    event: str
    node: str | None = None
    step_id: str | None = None
    status: str | None = None
    payload: JSONObject = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        event: str,
        node: str | None = None,
        step_id: str | None = None,
        status: str | None = None,
        payload: JSONObject | None = None,
    ) -> "HistoryEntry":
        return cls(
            timestamp=iso_utc_now(),
            event=_require_non_empty_string(event, "event"),
            node=node.strip() if isinstance(node, str) and node.strip() else None,
            step_id=step_id.strip() if isinstance(step_id, str) and step_id.strip() else None,
            status=status.strip() if isinstance(status, str) and status.strip() else None,
            payload=_require_object(payload or {}, "payload"),
        )

    @classmethod
    def branch_selected(
        cls,
        *,
        node: str,
        step_id: str,
        payload: JSONObject,
    ) -> "HistoryEntry":
        return cls.create(
            event="branch_selected",
            node=node,
            step_id=step_id,
            payload=payload,
        )

    @classmethod
    def from_dict(cls, data: object) -> "HistoryEntry":
        payload = _require_top_level_fields(
            data,
            {"timestamp", "event", "node", "step_id", "status", "payload"},
            "HistoryEntry",
        )
        return cls(
            timestamp=_require_non_empty_string(payload["timestamp"], "timestamp"),
            event=_require_non_empty_string(payload["event"], "event"),
            node=str(payload["node"]) if payload["node"] is not None else None,
            step_id=str(payload["step_id"]) if payload["step_id"] is not None else None,
            status=str(payload["status"]) if payload["status"] is not None else None,
            payload=_require_object(payload.get("payload", {}), "payload"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunState:
    run_id: str
    workflow_id: str
    workflow_version: str
    status: str
    current_node: str
    graph_state: JSONValue
    history: list[HistoryEntry] = field(default_factory=list)
    created_at: str = field(default_factory=iso_utc_now)
    updated_at: str = field(default_factory=iso_utc_now)
    state_version: int = CURRENT_RUN_STATE_VERSION
    revision: int = 0
    observation_replays: dict[str, dict] = field(default_factory=dict)
    history_degraded: bool = False
    accepted_steps: int = 0
    max_steps: int | None = None
    terminal_reason: str | None = None
    artifact_refs: list[JSONObject] = field(default_factory=list)
    diagnostic_refs: list[JSONObject] = field(default_factory=list)
    artifacts_degraded: bool = False

    @classmethod
    def from_dict(cls, data: object) -> "RunState":
        payload = _require_top_level_fields(
            data,
            {
                "run_id",
                "workflow_id",
                "workflow_version",
                "status",
                "current_node",
                "graph_state",
                "history",
                "created_at",
                "updated_at",
            },
            "RunState",
            optional_fields={
                "state_version",
                "revision",
                "observation_replays",
                "history_degraded",
                "accepted_steps",
                "max_steps",
                "terminal_reason",
                "artifact_refs",
                "diagnostic_refs",
                "artifacts_degraded",
            },
        )
        status = _require_non_empty_string(payload["status"], "status")
        if status not in RUN_STATUSES:
            raise ValueError(f"unsupported run status: {status}")
        history_payload = payload.get("history", [])
        if not isinstance(history_payload, list):
            raise ValueError("history must be a list")
        state_version = payload.get("state_version", 1)
        if (
            not isinstance(state_version, int)
            or isinstance(state_version, bool)
            or state_version < 1
            or state_version > CURRENT_RUN_STATE_VERSION
        ):
            raise ValueError(f"unsupported run state version: {state_version!r}")
        revision = payload.get("revision", 0)
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
            raise ValueError("run state revision must be a non-negative integer")
        observation_replays = _normalize_observation_replays(
            payload.get("observation_replays", {})
        )
        history_degraded = payload.get("history_degraded", False)
        if not isinstance(history_degraded, bool):
            raise ValueError("history_degraded must be a boolean")
        accepted_steps = payload.get("accepted_steps", 0)
        if (
            not isinstance(accepted_steps, int)
            or isinstance(accepted_steps, bool)
            or accepted_steps < 0
        ):
            raise ValueError("accepted_steps must be a non-negative integer")
        max_steps = payload.get("max_steps")
        if max_steps is not None:
            if (
                not isinstance(max_steps, int)
                or isinstance(max_steps, bool)
                or max_steps < 1
                or max_steps > MAX_RUNTIME_STEPS
            ):
                raise ValueError(
                    f"max_steps must be an integer between 1 and {MAX_RUNTIME_STEPS}"
                )
        terminal_reason = payload.get("terminal_reason")
        if terminal_reason is not None:
            terminal_reason = _require_non_empty_string(terminal_reason, "terminal_reason")
        artifact_refs = _normalize_artifact_references(
            payload.get("artifact_refs", []),
            "artifact_refs",
        )
        diagnostic_refs = _normalize_artifact_references(
            payload.get("diagnostic_refs", []),
            "diagnostic_refs",
        )
        artifacts_degraded = payload.get("artifacts_degraded", False)
        if not isinstance(artifacts_degraded, bool):
            raise ValueError("artifacts_degraded must be a boolean")
        state = cls(
            run_id=_require_non_empty_string(payload["run_id"], "run_id"),
            workflow_id=_require_non_empty_string(payload["workflow_id"], "workflow_id"),
            workflow_version=_require_non_empty_string(
                payload["workflow_version"],
                "workflow_version",
            ),
            status=status,
            current_node=_require_non_empty_string(payload["current_node"], "current_node"),
            graph_state=payload["graph_state"],
            history=[HistoryEntry.from_dict(item) for item in history_payload],
            created_at=_require_non_empty_string(payload["created_at"], "created_at"),
            updated_at=_require_non_empty_string(payload["updated_at"], "updated_at"),
            state_version=CURRENT_RUN_STATE_VERSION,
            revision=revision,
            observation_replays=observation_replays,
            history_degraded=history_degraded,
            accepted_steps=accepted_steps,
            max_steps=max_steps,
            terminal_reason=terminal_reason,
            artifact_refs=artifact_refs,
            diagnostic_refs=diagnostic_refs,
            artifacts_degraded=artifacts_degraded,
        )
        normalized_history: list[HistoryEntry] = []
        for entry in state.history:
            compacted_payload, degraded = compact_history_payload(entry.payload)
            entry.payload = compacted_payload
            state.history_degraded = state.history_degraded or degraded
            normalized_history.append(entry)
        state.history, retained = trim_history(normalized_history)
        state.history_degraded = state.history_degraded or retained
        return state

    def append_history(self, entry: HistoryEntry) -> None:
        compacted_payload, degraded = compact_history_payload(entry.payload)
        entry.payload = compacted_payload
        self.history_degraded = self.history_degraded or degraded
        self.history.append(entry)
        self.history, retained = trim_history(self.history)
        self.history_degraded = self.history_degraded or retained
        self.updated_at = iso_utc_now()

    def add_artifact_reference(self, reference: JSONObject, *, diagnostic: bool = False) -> bool:
        """Retain only routing metadata; duplicate content addresses are ignored."""

        normalized = _normalize_artifact_references([reference], "artifact_ref")[0]
        target = self.diagnostic_refs if diagnostic else self.artifact_refs
        if any(item["artifact_id"] == normalized["artifact_id"] for item in target):
            return False
        if len(target) >= MAX_ARTIFACT_REFERENCE_COUNT:
            self.artifacts_degraded = True
            return False
        target.append(normalized)
        self.updated_at = iso_utc_now()
        return True

    def record_observation_replay(
        self,
        observation_id: str,
        fingerprint: str,
        response: dict,
    ) -> None:
        identifier = _normalize_optional_identifier(observation_id, "observation_id")
        if identifier is None:
            raise ValueError("observation_id must be non-empty")
        if not isinstance(fingerprint, str) or not fingerprint.strip():
            raise ValueError("observation replay fingerprint must be non-empty")
        if not isinstance(response, dict):
            raise ValueError("observation replay response must be an object")
        try:
            validate_json_limits(
                response,
                path=f"observation_replays[{identifier}].response",
                max_bytes=MAX_OBSERVATION_REPLAY_ENTRY_BYTES,
            )
        except ValueError as exc:
            raise ValueError(f"invalid observation replay {identifier}: {exc}") from exc
        self.observation_replays[identifier] = {
            "fingerprint": fingerprint.strip(),
            "response": response,
        }
        _trim_observation_replays(self.observation_replays)
        self.updated_at = iso_utc_now()

    def to_dict(self) -> dict:
        self.observation_replays = _normalize_observation_replays(self.observation_replays)
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "status": self.status,
            "current_node": self.current_node,
            "graph_state": self.graph_state,
            "history": [entry.to_dict() for entry in self.history],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "state_version": CURRENT_RUN_STATE_VERSION,
            "revision": self.revision,
            "observation_replays": self.observation_replays,
            "history_degraded": self.history_degraded,
            "accepted_steps": self.accepted_steps,
            "max_steps": self.max_steps,
            "terminal_reason": self.terminal_reason,
            "artifact_refs": self.artifact_refs,
            "diagnostic_refs": self.diagnostic_refs,
            "artifacts_degraded": self.artifacts_degraded,
        }
