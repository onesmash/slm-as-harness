"""Typed normalization helpers for the Co-STORM expert fan-out boundary.

The host may report operational trace fields either at the trace-entry top
level or inside ``metadata``. This module turns both forms into one internal
shape and keeps canonical history separate from an in-flight attempt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


EXPERT_FIELDS = frozenset({"id", "role", "brief"})
BINDING_FIELDS = frozenset(
    {
        "expert_id",
        "subagent_run_id",
        "summary",
        "artifact_path",
        "spawn_receipt",
        "completion_receipt",
    }
)
HISTORY_FIELDS = frozenset(
    {"round_index", "expert_id", "subagent_run_id", "artifact_path"}
)
TRACE_METADATA_FIELDS = (
    "phase",
    "expert_id",
    "expert_ids",
    "subagent_run_id",
    "subagent_run_ids",
    "fanout_round_index",
    "receipt_id",
)
TRACE_PHASES = frozenset({"spawn", "wait", "join"})
SUCCESS_STATUSES = frozenset({"success", "succeeded", "completed", "done", "ok", "passed"})
MAX_ARTIFACT_BYTES = 1_048_576
RUNTIME_OWNED_OUTPUT_KEYS = frozenset(
    {"subagent_run_history", "subagent_attempt_history", "current_fanout_attempt"}
)


class FanoutContractError(ValueError):
    """Raised when a workflow-owned fan-out value cannot be normalized."""


@dataclass(frozen=True)
class NormalizedTrace:
    events: list[dict[str, Any]]
    errors: list[str]


def parse_expert_roster(value: object) -> tuple[list[dict[str, str]], list[str]]:
    """Return structured expert records and all roster validation errors."""

    if not isinstance(value, list):
        return [], ["expert_roster must be a list of structured objects"]

    records: list[dict[str, str]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(value):
        label = f"expert_roster[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object with id, role, and brief")
            continue
        if set(item) != EXPERT_FIELDS:
            errors.append(f"{label} must contain exactly id, role, and brief")
        normalized: dict[str, str] = {}
        for key in sorted(EXPERT_FIELDS):
            raw_value = item.get(key)
            if not isinstance(raw_value, str) or not raw_value.strip():
                errors.append(f"{label}.{key} must be a non-empty string")
                continue
            normalized[key] = raw_value.strip()
        expert_id = normalized.get("id")
        if expert_id:
            if expert_id in seen_ids:
                errors.append(f"expert_roster contains duplicate id: {expert_id}")
            seen_ids.add(expert_id)
        if len(normalized) == len(EXPERT_FIELDS):
            records.append(normalized)
    if len(records) < 2:
        errors.append("expert_roster must contain at least two valid expert records")
    return records, errors


def parse_binding_records(value: object) -> tuple[list[dict[str, str]], list[str]]:
    """Normalize binding objects without imposing receipt uniqueness."""

    if not isinstance(value, list):
        return [], ["subagent_binding_records must be a list of objects"]

    records: list[dict[str, str]] = []
    errors: list[str] = []
    for index, item in enumerate(value):
        label = f"subagent_binding_records[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object, not a JSON-encoded string")
            continue
        if set(item) != BINDING_FIELDS:
            errors.append(f"{label} must contain exactly the six binding fields")
        normalized: dict[str, str] = {}
        for key in sorted(BINDING_FIELDS):
            raw_value = item.get(key)
            if not isinstance(raw_value, str) or not raw_value.strip():
                errors.append(f"{label}.{key} must be a non-empty string")
                continue
            normalized[key] = raw_value.strip()
        if len(normalized) == len(BINDING_FIELDS):
            records.append(normalized)
    return records, errors


def normalize_history(value: object) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize canonical history and accept the old exact string format."""

    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], ["subagent_run_history must be a list"]

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, item in enumerate(value):
        label = f"subagent_run_history[{index}]"
        if isinstance(item, str):
            match = re.fullmatch(
                r"round=(\d+);expert=([^;]+);subagent=([^;]+);artifact=(.+)",
                item.strip(),
            )
            if match is None:
                errors.append(f"{label} is not a valid legacy history entry")
                continue
            item = {
                "round_index": int(match.group(1)),
                "expert_id": match.group(2).strip(),
                "subagent_run_id": match.group(3).strip(),
                "artifact_path": match.group(4).strip(),
            }
        if not isinstance(item, dict):
            errors.append(f"{label} must be a structured history object")
            continue
        if not HISTORY_FIELDS.issubset(item):
            errors.append(f"{label} is missing one or more canonical history fields")
            continue
        if not set(item).issubset(HISTORY_FIELDS):
            errors.append(f"{label} contains unknown fields")
        round_index = item.get("round_index")
        if not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1:
            errors.append(f"{label}.round_index must be a positive integer")
            continue
        normalized: dict[str, Any] = {"round_index": round_index}
        valid = True
        for key in ("expert_id", "subagent_run_id", "artifact_path"):
            raw_value = item.get(key)
            if not isinstance(raw_value, str) or not raw_value.strip():
                errors.append(f"{label}.{key} must be a non-empty string")
                valid = False
            else:
                normalized[key] = raw_value.strip()
        if valid:
            records.append(normalized)
    return records, errors


def canonical_history_errors(
    records: list[dict[str, Any]], expected_expert_ids: list[str] | None = None
) -> list[str]:
    """Check identity, order, and complete expert coverage of persisted history."""

    errors: list[str] = []
    seen_run_ids: set[str] = set()
    seen_artifacts: set[str] = set()
    seen_round_experts: set[tuple[int, str]] = set()
    round_experts: dict[int, set[str]] = {}
    previous_round = 0
    expected = set(expected_expert_ids or [])
    for index, record in enumerate(records):
        round_index = record["round_index"]
        expert_id = record["expert_id"]
        run_id = record["subagent_run_id"]
        artifact_path = record["artifact_path"]
        if round_index < previous_round:
            errors.append("canonical history round indexes must be non-decreasing")
        previous_round = round_index
        if run_id in seen_run_ids:
            errors.append(f"canonical history reuses subagent run id: {run_id}")
        if artifact_path in seen_artifacts:
            errors.append(f"canonical history reuses artifact path: {artifact_path}")
        pair = (round_index, expert_id)
        if pair in seen_round_experts:
            errors.append(
                f"canonical history contains duplicate expert {expert_id!r} in round {round_index}"
            )
        if expected and expert_id not in expected:
            errors.append(
                f"canonical history references expert outside persisted roster: {expert_id}"
            )
        seen_run_ids.add(run_id)
        seen_artifacts.add(artifact_path)
        seen_round_experts.add(pair)
        round_experts.setdefault(round_index, set()).add(expert_id)

    if expected:
        for round_index, experts in round_experts.items():
            if experts != expected:
                errors.append(
                    f"canonical history round {round_index} must cover the persisted roster exactly"
                )
    if round_experts:
        actual_rounds = sorted(round_experts)
        expected_rounds = list(range(1, actual_rounds[-1] + 1))
        if actual_rounds != expected_rounds:
            errors.append(
                "canonical history round indexes must be contiguous from round 1"
            )
    return errors


def serialize_history_entry(entry: dict[str, Any]) -> str:
    """Return the exact legacy representation for diagnostics and compatibility."""

    records, errors = normalize_history([entry])
    if errors or len(records) != 1:
        raise FanoutContractError("cannot serialize an invalid canonical history entry")
    normalized = records[0]
    return (
        f"round={normalized['round_index']};expert={normalized['expert_id']}"
        f";subagent={normalized['subagent_run_id']};artifact={normalized['artifact_path']}"
    )


def build_history_tail(
    *,
    round_index: object,
    expert_ids: object,
    run_ids: object,
    artifact_paths: object,
) -> list[dict[str, Any]]:
    """Build the current canonical tail from the accepted batch arrays."""

    if not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1:
        raise FanoutContractError("fanout_round_index must be a positive integer")
    values = (expert_ids, run_ids, artifact_paths)
    if any(not isinstance(value, list) for value in values):
        raise FanoutContractError("fan-out history inputs must be lists")
    if not (len(expert_ids) == len(run_ids) == len(artifact_paths)):
        raise FanoutContractError("fan-out history arrays must have equal lengths")
    tail: list[dict[str, Any]] = []
    for index, (expert_id, run_id, artifact_path) in enumerate(
        zip(expert_ids, run_ids, artifact_paths)
    ):
        values_by_name = {
            "expert_id": expert_id,
            "subagent_run_id": run_id,
            "artifact_path": artifact_path,
        }
        if any(not isinstance(value, str) or not value.strip() for value in values_by_name.values()):
            raise FanoutContractError(f"fan-out history item {index} contains an empty value")
        tail.append(
            {
                "round_index": round_index,
                "expert_id": expert_id.strip(),
                "subagent_run_id": run_id.strip(),
                "artifact_path": artifact_path.strip(),
            }
        )
    return tail


def build_canonical_history(
    *,
    previous_history: object,
    round_index: object,
    expert_ids: object,
    run_ids: object,
    artifact_paths: object,
) -> list[dict[str, Any]]:
    """Append an accepted batch to canonical history without model replay."""

    previous, errors = normalize_history(previous_history)
    if errors:
        raise FanoutContractError("; ".join(errors))
    history_errors = canonical_history_errors(previous)
    if history_errors:
        raise FanoutContractError("; ".join(history_errors))
    tail = build_history_tail(
        round_index=round_index,
        expert_ids=expert_ids,
        run_ids=run_ids,
        artifact_paths=artifact_paths,
    )
    previous_run_ids = {entry["subagent_run_id"] for entry in previous}
    if previous_run_ids.intersection(entry["subagent_run_id"] for entry in tail):
        raise FanoutContractError("canonical history cannot reuse a prior subagent run id")
    combined = previous + tail
    combined_errors = canonical_history_errors(combined)
    if combined_errors:
        raise FanoutContractError("; ".join(combined_errors))
    return combined


def normalize_tool_trace(value: object) -> NormalizedTrace:
    """Normalize flat host traces and canonical metadata traces together."""

    if not isinstance(value, list):
        return NormalizedTrace([], ["tool_trace must be a list"])

    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, raw_entry in enumerate(value):
        label = f"tool_trace[{index}]"
        if not isinstance(raw_entry, dict):
            errors.append(f"{label} must be an object")
            continue
        raw_metadata = raw_entry.get("metadata", {})
        if raw_metadata is None:
            raw_metadata = {}
        if not isinstance(raw_metadata, dict):
            errors.append(f"{label}.metadata must be an object")
            raw_metadata = {}
        metadata = dict(raw_metadata)
        for key in TRACE_METADATA_FIELDS:
            if key in raw_entry:
                if key in metadata and metadata[key] != raw_entry[key]:
                    errors.append(f"{label} has conflicting flat and nested {key}")
                else:
                    metadata.setdefault(key, raw_entry[key])

        phase = metadata.get("phase")
        if not isinstance(phase, str) or phase.strip().lower() not in TRACE_PHASES:
            errors.append(f"{label}.phase must be spawn, wait, or join")
            continue
        phase = phase.strip().lower()
        expert_ids, expert_errors = _trace_id_list(metadata, "expert_ids", "expert_id", label)
        run_ids, run_errors = _trace_id_list(
            metadata,
            "subagent_run_ids",
            "subagent_run_id",
            label,
        )
        errors.extend(expert_errors)
        errors.extend(run_errors)
        round_index = metadata.get("fanout_round_index")
        if not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1:
            errors.append(f"{label}.fanout_round_index must be a positive integer")
            continue
        receipt_id = metadata.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.strip():
            errors.append(f"{label}.receipt_id must be a non-empty string")
            continue
        tool_name = raw_entry.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            errors.append(f"{label}.tool_name must be a non-empty string")
        status = raw_entry.get("status")
        if not isinstance(status, str) or not status.strip():
            errors.append(f"{label}.status must be a non-empty string")
            continue
        if expert_ids and run_ids and len(expert_ids) != len(run_ids):
            errors.append(f"{label} expert_ids and subagent_run_ids must have equal lengths")
            continue
        events.append(
            {
                "tool_name": tool_name.strip() if isinstance(tool_name, str) else "",
                "status": status.strip().lower(),
                "phase": phase,
                "expert_ids": expert_ids,
                "subagent_run_ids": run_ids,
                "fanout_round_index": round_index,
                "receipt_id": receipt_id.strip(),
            }
        )
    return NormalizedTrace(events, errors)


def _trace_id_list(
    metadata: dict[str, Any], plural_key: str, singular_key: str, label: str
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    plural = metadata.get(plural_key)
    singular = metadata.get(singular_key)
    if plural is not None:
        if not isinstance(plural, list):
            return [], [f"{label}.{plural_key} must be a list"]
        values: list[str] = []
        for item in plural:
            if not isinstance(item, str) or not item.strip():
                errors.append(f"{label}.{plural_key} entries must be non-empty strings")
            else:
                values.append(item.strip())
        if len(set(values)) != len(values):
            errors.append(f"{label}.{plural_key} entries must be unique")
        if singular is not None and (not isinstance(singular, str) or singular.strip() not in values):
            errors.append(f"{label}.{singular_key} must agree with {plural_key}")
        return values, errors
    if singular is None:
        return [], []
    if not isinstance(singular, str) or not singular.strip():
        return [], [f"{label}.{singular_key} must be a non-empty string"]
    return [singular.strip()], []


def build_attempt_snapshot(
    *, output: dict[str, Any], status: object, verifier_result: dict[str, Any] | None
) -> dict[str, Any]:
    """Keep a compact non-canonical record for retry diagnostics."""

    snapshot: dict[str, Any] = {
        "status": str(status or ""),
        "fanout_round_index": output.get("fanout_round_index"),
        "expert_ids": list(output.get("subagent_expert_ids") or [])
        if isinstance(output.get("subagent_expert_ids"), list)
        else [],
        "subagent_run_ids": list(output.get("subagent_run_ids") or [])
        if isinstance(output.get("subagent_run_ids"), list)
        else [],
        "artifact_paths": list(output.get("subagent_artifact_paths") or [])
        if isinstance(output.get("subagent_artifact_paths"), list)
        else [],
    }
    if verifier_result is not None and isinstance(verifier_result.get("passed"), bool):
        snapshot["verifier_passed"] = verifier_result["passed"]
    return snapshot


def history_run_ids(value: object) -> set[str]:
    records, _ = normalize_history(value)
    return {entry["subagent_run_id"] for entry in records}


def fanout_contract_errors(
    *,
    output: dict[str, Any],
    state: dict[str, Any] | None,
    repo_root: str,
    tool_trace: object,
) -> list[str]:
    """Return all deterministic fan-out mismatches for one observation.

    The returned list is intentionally diagnostic: a repair prompt should see
    every independent mismatch from one attempt rather than discovering them
    one by one across repeated subagent launches.
    """

    errors: list[str] = []
    persisted = state if isinstance(state, dict) else {}

    for key in sorted(RUNTIME_OWNED_OUTPUT_KEYS):
        if key in output:
            errors.append(f"{key} is runtime-owned and must not be returned by the model")

    roster, roster_errors = parse_expert_roster(persisted.get("expert_roster"))
    errors.extend(roster_errors)
    roster_ids = [record["id"] for record in roster]

    if output.get("execution_mode") != "parallel_fanout":
        errors.append("execution_mode must equal parallel_fanout")
    if output.get("fanout_complete") is not True:
        errors.append("fanout_complete must be true")

    previous_round = persisted.get("round_index")
    fanout_round = output.get("fanout_round_index")
    if not isinstance(previous_round, int) or isinstance(previous_round, bool) or previous_round < 0:
        errors.append("persisted state.round_index must be a non-negative integer")
    if not isinstance(fanout_round, int) or isinstance(fanout_round, bool) or fanout_round < 1:
        errors.append("fanout_round_index must be a positive integer")
    elif isinstance(previous_round, int) and not isinstance(previous_round, bool) and fanout_round != previous_round + 1:
        errors.append(
            f"fanout_round_index expected {previous_round + 1}, actual {fanout_round}"
        )
    constraints = persisted.get("constraints")
    constraints = constraints if isinstance(constraints, dict) else {}
    max_rounds = constraints.get("max_rounds")
    if not isinstance(max_rounds, int) or isinstance(max_rounds, bool) or max_rounds <= 0:
        errors.append("constraints.max_rounds must be a positive integer")
    elif isinstance(fanout_round, int) and not isinstance(fanout_round, bool) and fanout_round > max_rounds:
        errors.append(f"fanout_round_index {fanout_round} exceeds max_rounds {max_rounds}")

    expert_ids = output.get("subagent_expert_ids")
    run_ids = output.get("subagent_run_ids")
    summaries = output.get("subagent_result_summaries")
    artifact_paths = output.get("subagent_artifact_paths")
    arrays = {
        "subagent_expert_ids": expert_ids,
        "subagent_run_ids": run_ids,
        "subagent_result_summaries": summaries,
        "subagent_artifact_paths": artifact_paths,
    }
    for label, value in arrays.items():
        if not isinstance(value, list):
            errors.append(f"{label} must be a list")
            continue
        if len(value) > 128:
            errors.append(f"{label} exceeds the maximum supported fan-out size of 128")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"{label} entries must be non-empty strings")
        if len({item for item in value if isinstance(item, str)}) != len(value):
            errors.append(f"{label} entries must be unique")

    expected_count = len(roster_ids)
    if expected_count and any(isinstance(value, list) and len(value) != expected_count for value in arrays.values()):
        errors.append(
            f"fan-out arrays must each contain exactly {expected_count} items, with one item per expert"
        )
    if isinstance(expert_ids, list) and expert_ids != roster_ids:
        errors.append(f"subagent_expert_ids expected {roster_ids!r}, actual {expert_ids!r}")

    bindings, binding_errors = parse_binding_records(output.get("subagent_binding_records"))
    errors.extend(binding_errors)
    if expected_count and len(bindings) != expected_count:
        errors.append(
            f"subagent_binding_records must contain exactly {expected_count} objects"
        )
    if all(isinstance(value, list) for value in (expert_ids, run_ids, summaries, artifact_paths)):
        for index, binding in enumerate(bindings):
            if index >= expected_count:
                break
            expected_fields = {
                "expert_id": expert_ids[index],
                "subagent_run_id": run_ids[index],
                "summary": summaries[index],
                "artifact_path": artifact_paths[index],
            }
            for key, expected in expected_fields.items():
                actual = binding.get(key)
                if actual != expected:
                    errors.append(
                        f"binding[{index}].{key} expected {expected!r}, actual {actual!r}"
                    )

    spawn_receipts: list[str] = []
    completion_receipts: list[str] = []
    for index, binding in enumerate(bindings):
        spawn_receipts.append(binding.get("spawn_receipt", ""))
        completion_receipts.append(binding.get("completion_receipt", ""))
        if binding.get("spawn_receipt") in completion_receipts[:index]:
            errors.append(f"binding[{index}] reuses a receipt across spawn and join")
        if binding.get("spawn_receipt") == binding.get("completion_receipt"):
            errors.append(f"binding[{index}] cannot reuse one receipt for spawn and join")
    if len(set(spawn_receipts)) != len(spawn_receipts):
        errors.append("spawn_receipt must be unique for every expert")
    cross_phase_receipts = set(spawn_receipts).intersection(completion_receipts)
    if cross_phase_receipts:
        errors.append(
            "spawn and completion receipts share forbidden identifiers: "
            + repr(sorted(cross_phase_receipts))
        )

    previous_history, history_errors = normalize_history(persisted.get("subagent_run_history"))
    errors.extend(history_errors)
    errors.extend(canonical_history_errors(previous_history, roster_ids or None))
    previous_run_ids = {entry["subagent_run_id"] for entry in previous_history}
    if isinstance(run_ids, list):
        reused = sorted(previous_run_ids.intersection(item for item in run_ids if isinstance(item, str)))
        if reused:
            errors.append(f"subagent_run_ids reuse canonical history entries: {reused}")

    if all(isinstance(value, list) for value in (expert_ids, run_ids, artifact_paths)) and isinstance(fanout_round, int) and not isinstance(fanout_round, bool):
        try:
            tail = build_history_tail(
                round_index=fanout_round,
                expert_ids=expert_ids,
                run_ids=run_ids,
                artifact_paths=artifact_paths,
            )
            expected_history = previous_history + tail
            supplied_history = output.get("subagent_run_history")
            if supplied_history is not None:
                supplied_records, supplied_errors = normalize_history(supplied_history)
                errors.extend(supplied_errors)
                if not supplied_errors and supplied_records != expected_history:
                    errors.append(
                        "model-supplied subagent_run_history conflicts with runtime-derived canonical history"
                    )
        except FanoutContractError as exc:
            errors.append(str(exc))

    _append_artifact_errors(errors, artifact_paths, repo_root)

    normalized_trace = normalize_tool_trace(tool_trace)
    errors.extend(normalized_trace.errors)
    _append_trace_errors(
        errors=errors,
        events=normalized_trace.events,
        bindings=bindings,
        fanout_round=fanout_round,
    )
    return _deduplicate_errors(errors)


def _append_artifact_errors(errors: list[str], artifact_paths: object, repo_root: str) -> None:
    if not isinstance(artifact_paths, list):
        return
    repo = _resolve_repo(repo_root)
    resolved_paths: set[object] = set()
    resolved_inodes: set[tuple[int, int]] = set()
    for index, raw_path in enumerate(artifact_paths):
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        candidate = Path(raw_path)
        if candidate.is_absolute():
            errors.append(f"artifact[{index}] must be repository-relative")
            continue
        try:
            resolved = (repo / candidate).resolve()
            resolved.relative_to(repo)
        except (OSError, ValueError):
            errors.append(f"artifact[{index}] must resolve inside repo_root")
            continue
        if resolved in resolved_paths:
            errors.append(f"artifact[{index}] aliases another artifact path")
            continue
        try:
            if not resolved.is_file():
                errors.append(f"artifact[{index}] must point to a regular file")
                continue
            stat_result = resolved.stat()
            if stat_result.st_size > MAX_ARTIFACT_BYTES:
                errors.append(
                    f"artifact[{index}] exceeds the {MAX_ARTIFACT_BYTES}-byte size limit"
                )
                continue
            with resolved.open("rb") as handle:
                content = handle.read(MAX_ARTIFACT_BYTES + 1)
            if len(content) > MAX_ARTIFACT_BYTES:
                errors.append(
                    f"artifact[{index}] exceeds the {MAX_ARTIFACT_BYTES}-byte size limit"
                )
                continue
            text = content.decode("utf-8")
        except (OSError, ValueError, UnicodeError):
            errors.append(f"artifact[{index}] must be a readable UTF-8 file")
            continue
        inode = (stat_result.st_dev, stat_result.st_ino)
        if inode[1] and inode in resolved_inodes:
            errors.append(f"artifact[{index}] aliases the same underlying file")
        if not text.strip():
            errors.append(f"artifact[{index}] must contain non-empty grounded content")
        resolved_paths.add(resolved)
        if inode[1]:
            resolved_inodes.add(inode)


def _append_trace_errors(
    *,
    errors: list[str],
    events: list[dict[str, Any]],
    bindings: list[dict[str, str]],
    fanout_round: object,
) -> None:
    if not isinstance(fanout_round, int) or isinstance(fanout_round, bool):
        return
    for index, event in enumerate(events):
        if not event.get("tool_name"):
            errors.append(f"tool_trace[{index}].tool_name must be non-empty")
        if event.get("status") not in SUCCESS_STATUSES:
            errors.append(f"tool_trace[{index}] must report a successful status")
        expected_suffix = {
            "spawn": ".spawn",
            "wait": ".wait",
            "join": ".join",
        }.get(event.get("phase"))
        if expected_suffix and not event.get("tool_name", "").endswith(expected_suffix):
            errors.append(
                f"tool_trace[{index}] tool_name must end with {expected_suffix!r} for phase {event.get('phase')!r}"
            )

    spawn_event_indexes: dict[tuple[str, str], list[int]] = {}
    wait_event_indexes: dict[tuple[str, str], list[int]] = {}
    join_event_indexes: dict[tuple[str, str], list[int]] = {}
    join_receipt_event_indexes: dict[str, set[int]] = {}
    expected_pairs = {
        (binding.get("expert_id", ""), binding.get("subagent_run_id", ""))
        for binding in bindings
    }
    for index, event in enumerate(events):
        if event.get("fanout_round_index") != fanout_round:
            continue
        pairs = list(zip(event.get("expert_ids", []), event.get("subagent_run_ids", [])))
        phase = event.get("phase")
        if not pairs:
            errors.append(f"tool_trace[{index}] must cover at least one expert/run pair")
            continue
        if phase == "spawn":
            target = spawn_event_indexes
        elif phase == "wait":
            target = wait_event_indexes
        elif phase == "join":
            target = join_event_indexes
            receipt_id = event.get("receipt_id")
            if isinstance(receipt_id, str) and receipt_id:
                join_receipt_event_indexes.setdefault(receipt_id, set()).add(index)
        else:
            continue
        for pair in pairs:
            if pair not in expected_pairs:
                errors.append(
                    f"tool_trace[{index}] references an expert/run pair outside the binding records: {pair!r}"
                )
            target.setdefault(pair, []).append(index)

    for receipt_id, event_indexes in join_receipt_event_indexes.items():
        if len(event_indexes) > 1:
            errors.append(
                f"completion receipt {receipt_id!r} must identify one real join event"
            )

    for binding_index, binding in enumerate(bindings):
        pair = (binding.get("expert_id", ""), binding.get("subagent_run_id", ""))
        spawn_matches = spawn_event_indexes.get(pair, [])
        if len(spawn_matches) != 1:
            errors.append(
                f"binding[{binding_index}] requires exactly one spawn trace for {pair!r}; matched {len(spawn_matches)}"
            )
        elif events[spawn_matches[0]].get("receipt_id") != binding.get("spawn_receipt"):
            errors.append(
                f"binding[{binding_index}].spawn_receipt does not match the actual spawn trace receipt"
            )

        wait_matches = wait_event_indexes.get(pair, [])
        if len(wait_matches) != 1:
            errors.append(
                f"binding[{binding_index}] requires exactly one wait trace for {pair!r}; matched {len(wait_matches)}"
            )

        join_matches = join_event_indexes.get(pair, [])
        if len(join_matches) != 1:
            errors.append(
                f"binding[{binding_index}] requires exactly one join coverage for {pair!r}; matched {len(join_matches)}"
            )
        elif events[join_matches[0]].get("receipt_id") != binding.get("completion_receipt"):
            errors.append(
                f"binding[{binding_index}].completion_receipt does not match the actual batch join receipt"
            )
        if len(spawn_matches) == 1 and len(wait_matches) == 1 and len(join_matches) == 1:
            spawn_index = spawn_matches[0]
            wait_index = wait_matches[0]
            join_index = join_matches[0]
            if not spawn_index < wait_index < join_index:
                errors.append(
                    f"binding[{binding_index}] trace order must be spawn -> wait -> join for {pair!r}"
                )


def _resolve_repo(repo_root: str) -> Path:
    return Path(repo_root).resolve()


def _deduplicate_errors(errors: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for error in errors:
        if error not in seen:
            seen.add(error)
            deduplicated.append(error)
    return deduplicated[:128]
