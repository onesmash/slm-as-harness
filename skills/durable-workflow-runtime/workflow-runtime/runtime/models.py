from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TypeAlias


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]

OBSERVATION_STATUSES = {"succeeded", "failed", "blocked", "partial"}
RUN_STATUSES = {"running", "waiting_for_host", "blocked", "done", "failed_terminal"}
WORKFLOW_RESPONSE_KINDS = {"yield", "done"}


def iso_utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


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


def _require_top_level_fields(data: object, field_names: set[str], model_name: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError(f"{model_name} must be an object")
    actual = set(data.keys())
    missing = sorted(field_names - actual)
    if missing:
        raise ValueError(f"{model_name} missing required fields: {', '.join(missing)}")
    allowed = field_names | {"caller"}
    extras = sorted(actual - allowed)
    if model_name != "StartRequest":
        allowed = field_names
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

    @classmethod
    def from_dict(cls, data: object) -> "Observation":
        if not isinstance(data, dict):
            raise ValueError("Observation must be an object")
        missing = sorted(
            {"run_id", "step_id", "status", "summary", "structured_output"} - set(data.keys())
        )
        if missing:
            raise ValueError(f"Observation missing required fields: {', '.join(missing)}")
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
            raw_output=str(data.get("raw_output", "")),
        )

    def to_dict(self) -> dict:
        result = asdict(self)
        if self.error is None:
            result["error"] = None
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
        )
        status = _require_non_empty_string(payload["status"], "status")
        if status not in RUN_STATUSES:
            raise ValueError(f"unsupported run status: {status}")
        history_payload = payload.get("history", [])
        if not isinstance(history_payload, list):
            raise ValueError("history must be a list")
        return cls(
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
        )

    def append_history(self, entry: HistoryEntry) -> None:
        self.history.append(entry)
        self.updated_at = iso_utc_now()

    def to_dict(self) -> dict:
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
        }
