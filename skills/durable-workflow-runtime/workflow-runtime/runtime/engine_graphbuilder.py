from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import time
from pathlib import Path
from uuid import uuid4

from runtime.errors import (
    ArtifactStoreError,
    ObservationValidationError,
    ProtocolError,
    RequestValidationError,
    SchemaValidationError,
    WorkflowExecutionError,
)
from runtime.artifacts import ArtifactStore
from runtime.limits import (
    DEFAULT_RUNTIME_LIMITS,
    PayloadLimitError,
    json_byte_size,
    validate_json_limits,
    validate_observation_payload,
)
from runtime.module_loader import load_workflow_modules
from runtime.models import (
    DoneResponse,
    HistoryEntry,
    Observation,
    PromptEnvelope,
    RunState,
    StartRequest,
    YieldResponse,
    MAX_RUNTIME_STEPS,
)
from runtime.persistence import FileRunStateStore
from runtime.redaction import redact_sensitive_json, redact_sensitive_text
from runtime.telemetry import RuntimeTelemetry
from runtime.validation import validate_observation_against_contract, validate_workflow_input
from runtime.verifier_runner import run_step_verifier
from workflows.common.prompting import build_prompt_envelope


class GraphBuilderRuntimeEngine:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._store = FileRunStateStore(self.repo_root)
        self._artifacts = ArtifactStore(self.repo_root)
        self._telemetry = RuntimeTelemetry(self.repo_root)
        self._runs: dict[str, RunState] = {}

    def start(self, workflow_id: str, request_payload: dict) -> dict:
        try:
            validate_json_limits(
                request_payload,
                path="start_request",
                limits=DEFAULT_RUNTIME_LIMITS,
                max_bytes=DEFAULT_RUNTIME_LIMITS.max_request_bytes,
            )
            request = StartRequest.from_dict(request_payload)
        except PayloadLimitError as exc:
            error = RequestValidationError(str(exc))
            error.code = exc.code
            error.path = exc.path
            raise error from exc
        except ValueError as exc:
            raise RequestValidationError(str(exc)) from exc
        try:
            max_steps = self._normalize_max_steps(request.constraints)
        except ValueError as exc:
            raise RequestValidationError(str(exc)) from exc
        modules = self._load_workflow_modules(workflow_id)
        graph_module = modules["graphbuilder_runtime"]
        try:
            validate_workflow_input(request, modules["contract"].WORKFLOW_INPUT_CONTRACT)
        except SchemaValidationError as exc:
            self._telemetry.record(
                "schema_failure",
                workflow_id=workflow_id,
                labels={"code": exc.code, "source": exc.source},
                metrics={"repairable": exc.repairable},
            )
            raise

        run_id = f"run_{uuid4().hex[:10]}"
        initial_state = modules["state"].make_initial_state(request.to_dict())
        response = graph_module.run_start_preview(
            state=initial_state,
            run_id=run_id,
            workflow_id=workflow_id,
            workflow_version=graph_module.WORKFLOW_VERSION,
        )
        run_state = RunState(
            run_id=run_id,
            workflow_id=workflow_id,
            workflow_version=graph_module.WORKFLOW_VERSION,
            status="waiting_for_host",
            current_node=response.step_id,
            graph_state=modules["state"].serialize_state(initial_state),
            max_steps=max_steps,
        )
        run_state.append_history(
            HistoryEntry.create(
                event="run_started",
                node=response.step_id,
                payload={"workflow_id": workflow_id},
            )
        )
        run_state.append_history(
            HistoryEntry.create(
                event="yield_emitted",
                node=response.step_id,
                step_id=response.step_id,
                payload={"intent": response.prompt_envelope.intent},
            )
        )
        saved_path = self._store.save(run_state)
        self._runs[run_id] = run_state
        self._telemetry.record(
            "run_started",
            run_id=run_id,
            workflow_id=workflow_id,
            step_id=response.step_id,
            metrics={
                "payload_bytes": json_byte_size(request_payload),
                "state_bytes": saved_path.stat().st_size,
                "history_bytes": json_byte_size([entry.to_dict() for entry in run_state.history]),
            },
        )
        return response.to_dict()

    async def start_async(self, workflow_id: str, request_payload: dict) -> dict:
        """Async-compatible wrapper for hosts that already run an event loop."""

        return await asyncio.to_thread(self.start, workflow_id, request_payload)

    def resume(self, run_id: str, observation_payload: dict) -> dict:
        resume_started = time.monotonic()
        try:
            validate_observation_payload(
                observation_payload,
                limits=DEFAULT_RUNTIME_LIMITS,
            )
            observation = Observation.from_dict(observation_payload)
        except PayloadLimitError as exc:
            error = ObservationValidationError(str(exc))
            error.code = exc.code
            error.path = exc.path
            raise error from exc
        except ValueError as exc:
            raise ObservationValidationError(str(exc)) from exc
        observation_fingerprint = self._observation_fingerprint(observation)

        with self._store.lock(run_id) as lock_stats:
            run_state = self._store.load(run_id)
            if run_state is None:
                cached_state = self._runs.get(run_id)
                run_state = copy.deepcopy(cached_state) if cached_state is not None else None
            if run_state is None:
                raise ProtocolError(f"unknown run_id: {run_id}")

            if observation.run_id != run_id:
                raise ProtocolError("observation run_id does not match requested run_id")

            replay = (
                run_state.observation_replays.get(observation.observation_id)
                if observation.observation_id is not None
                else None
            )
            if replay is not None:
                if replay.get("fingerprint") != observation_fingerprint:
                    raise ProtocolError("observation_id conflicts with previously accepted payload")
                response_payload = replay.get("response")
                if not isinstance(response_payload, dict):
                    raise ProtocolError("persisted observation replay response is invalid")
                self._telemetry.record(
                    "duplicate_resume",
                    run_id=run_id,
                    workflow_id=run_state.workflow_id,
                    step_id=observation.step_id,
                    metrics={
                        "latency_ms": round((time.monotonic() - resume_started) * 1000, 3),
                        "duplicate": True,
                        "lock_wait_ms": float(lock_stats["waited_ms"]),
                        "lock_contention": bool(lock_stats["contended"]),
                    },
                )
                return copy.deepcopy(response_payload)

            if run_state.status in {"done", "failed_terminal"}:
                raise ProtocolError(f"cannot resume terminal run: {run_id}")
            if observation.step_id != run_state.current_node:
                raise ProtocolError("observation step_id does not match current node")

            previous_revision = run_state.revision
            modules = self._load_workflow_modules(run_state.workflow_id)
            graph_module = modules["graphbuilder_runtime"]
            step_contract = modules["contract"].get_step_contract(observation.step_id)
            try:
                validate_observation_against_contract(observation, step_contract)
            except SchemaValidationError as exc:
                self._telemetry.record(
                    "schema_failure",
                    run_id=run_id,
                    workflow_id=run_state.workflow_id,
                    step_id=observation.step_id,
                    labels={"code": exc.code, "source": exc.source},
                    metrics={"repairable": exc.repairable},
                )
                raise
            self._persist_observation_artifacts(run_state, observation)
            run_state.append_history(
                HistoryEntry.create(
                    event="observation_received",
                    node=run_state.current_node,
                    step_id=observation.step_id,
                    status=observation.status,
                    payload={"summary": observation.summary},
                )
            )

            verifier_result = run_step_verifier(
                repo_root=self.repo_root,
                modules=modules,
                verifier=step_contract.verifier,
                run_state=run_state,
                observation=observation,
            )
            if verifier_result is not None:
                run_state.append_history(
                    HistoryEntry.create(
                        event="verifier_passed" if verifier_result["passed"] else "verifier_failed",
                        node=run_state.current_node,
                        step_id=observation.step_id,
                        payload={
                            "message": verifier_result["message"],
                            "details": verifier_result["details"],
                        },
                    )
                )

            workflow_state_snapshot = modules["state"].deserialize_state(
                run_state.graph_state if isinstance(run_state.graph_state, dict) else {}
            )
            preview = graph_module.run_transition_preview(
                state=workflow_state_snapshot,
                current_step_id=run_state.current_node,
                observation=observation.to_dict(),
                verifier_result=verifier_result,
            )
            accepted_steps = run_state.accepted_steps + 1
            preview_node_definition = graph_module.get_node_definition(preview.step_id)
            budget_exhausted = (
                run_state.max_steps is not None
                and accepted_steps >= run_state.max_steps
                and not getattr(preview_node_definition, "final", False)
            )
            final_step_id = self._find_final_step_id(graph_module) if budget_exhausted else None
            if budget_exhausted and final_step_id is None:
                raise WorkflowExecutionError(
                    f"workflow {run_state.workflow_id} has no final node for budget exhaustion"
                )
            preview_state_payload = getattr(preview, "state_payload", None)
            if isinstance(preview_state_payload, dict):
                run_state.graph_state = preview_state_payload
            if budget_exhausted:
                run_state.graph_state = self._terminalize_workflow_graph_state(
                    run_state.graph_state,
                    final_step_id,
                )
            run_state.accepted_steps = accepted_steps
            run_state.append_history(preview.history_entry)

            if budget_exhausted:
                assert final_step_id is not None
                run_state.terminal_reason = "max_steps_exceeded"
                run_state.append_history(
                    HistoryEntry.create(
                        event="budget_exhausted",
                        node=run_state.current_node,
                        step_id=preview.step_id,
                        payload={
                            "accepted_steps": accepted_steps,
                            "max_steps": run_state.max_steps,
                            "next_node": preview.step_id,
                        },
                    )
                )
                response = self._emit_step_response(
                    run_state,
                    modules,
                    final_step_id,
                    response_kind="done",
                    workflow_state_snapshot=workflow_state_snapshot,
                    response_metadata={
                        "degraded": True,
                        "terminal_reason": run_state.terminal_reason,
                    },
                )
            else:
                response_kind = "done" if getattr(preview_node_definition, "final", False) else "yield"
                response_metadata = None
                if response_kind == "done" and isinstance(preview.trace_payload, dict):
                    if preview.trace_payload.get("degraded") is True:
                        terminal_reason = preview.trace_payload.get("terminal_reason")
                        response_metadata = {"degraded": True}
                        if isinstance(terminal_reason, str) and terminal_reason.strip():
                            run_state.terminal_reason = terminal_reason.strip()
                            response_metadata["terminal_reason"] = run_state.terminal_reason
                response = self._emit_step_response(
                    run_state,
                    modules,
                    preview.step_id,
                    response_kind=response_kind,
                    workflow_state_snapshot=workflow_state_snapshot,
                    response_metadata=response_metadata,
                )
            response_payload = response.to_dict()
            if observation.observation_id is not None:
                run_state.record_observation_replay(
                    observation.observation_id,
                    observation_fingerprint,
                    response_payload,
                )
            run_state.revision = previous_revision + 1
            saved_path = self._store.save(
                run_state,
                expected_revision=previous_revision,
                _lock_held=True,
            )
            self._runs[run_id] = run_state
            self._telemetry.record(
                "resume_accepted",
                run_id=run_id,
                workflow_id=run_state.workflow_id,
                step_id=observation.step_id,
                labels={"response_kind": response.kind},
                metrics={
                    "latency_ms": round((time.monotonic() - resume_started) * 1000, 3),
                    "accepted_steps": run_state.accepted_steps,
                    "payload_bytes": json_byte_size(observation_payload),
                    "state_bytes": saved_path.stat().st_size,
                    "history_bytes": json_byte_size([entry.to_dict() for entry in run_state.history]),
                    "degraded": run_state.artifacts_degraded or budget_exhausted,
                    "lock_wait_ms": float(lock_stats["waited_ms"]),
                    "lock_contention": bool(lock_stats["contended"]),
                },
            )
            return response_payload

    async def resume_async(self, run_id: str, observation_payload: dict) -> dict:
        """Async-compatible wrapper preserving the synchronous protocol semantics."""

        return await asyncio.to_thread(self.resume, run_id, observation_payload)

    def _emit_step_response(
        self,
        run_state: RunState,
        modules: dict,
        step_id: str,
        *,
        response_kind: str,
        response_metadata: dict | None = None,
        workflow_state_snapshot=None,
    ):
        graph_module = modules["graphbuilder_runtime"]
        node_definition = graph_module.get_node_definition(step_id)
        template_context = None
        template_context_builder = getattr(graph_module, "build_template_context", None)
        if callable(template_context_builder):
            template_context = template_context_builder(step_id=step_id, run_state=run_state)
        if response_kind == "yield":
            contract = modules["contract"].get_step_contract(step_id)
            prompt_envelope = build_prompt_envelope(
                run_id=run_state.run_id,
                step_id=node_definition.step_id,
                prompt_asset_path=node_definition.prompt_asset_path,
                intent=node_definition.intent,
                expected_artifact=node_definition.expected_artifact,
                done_when=contract.done_when,
                output_schema=contract.output_schema,
                failure_schema=contract.failure_schema,
                resume_instructions=node_definition.resume_instructions,
                skill_routing=contract.skill_routing,
                metadata={
                    "workflow_id": run_state.workflow_id,
                    "workflow_version": run_state.workflow_version,
                },
                template_context=template_context,
            )
            run_state.status = "waiting_for_host"
            run_state.current_node = step_id
            run_state.append_history(
                HistoryEntry.create(
                    event="yield_emitted",
                    node=step_id,
                    step_id=step_id,
                    payload={"intent": node_definition.intent},
                )
            )
            return YieldResponse(
                run_id=run_state.run_id,
                step_id=step_id,
                prompt_envelope=prompt_envelope,
                retry_context=self._build_retry_context(
                    modules,
                    run_state,
                    workflow_state_snapshot=workflow_state_snapshot,
                ),
            )

        prompt_envelope = PromptEnvelope(
            run_id=run_state.run_id,
            step_id=node_definition.step_id,
            prompt=graph_module.load_prompt_body(step_id, template_context=template_context),
            intent=node_definition.intent,
            expected_artifact=node_definition.expected_artifact,
            done_when=list(node_definition.done_when),
            output_schema={},
            failure_schema={},
            resume_instructions=node_definition.resume_instructions,
            metadata={
                "workflow_id": run_state.workflow_id,
                "workflow_version": run_state.workflow_version,
                **(response_metadata or {}),
                **(
                    {"diagnostics_degraded": True}
                    if run_state.artifacts_degraded
                    else {}
                ),
            },
        )
        run_state.status = "done"
        run_state.current_node = step_id
        run_state.append_history(
            HistoryEntry.create(
                event="run_done",
                node=step_id,
                step_id=step_id,
                payload={"reason": run_state.terminal_reason or "workflow completed"},
            )
        )
        return DoneResponse(
            run_id=run_state.run_id,
            step_id=step_id,
            final_prompt_envelope=prompt_envelope,
        )

    def _persist_observation_artifacts(self, run_state: RunState, observation: Observation) -> None:
        """Externalize raw/tool artifacts without changing business payloads."""

        candidates: list[tuple[bytes | None, object, str, bool]] = []
        if observation.raw_output:
            candidates.append(
                (
                    redact_sensitive_text(observation.raw_output).encode("utf-8"),
                    None,
                    "text/plain; charset=utf-8",
                    True,
                )
            )
        for artifact in observation.artifacts:
            candidates.append((None, artifact, "application/json", False))
        if not candidates:
            return

        for raw_content, json_value, media_type, diagnostic in candidates:
            try:
                reference = (
                    self._artifacts.put_bytes(
                        run_state.run_id,
                        raw_content,
                        media_type=media_type,
                        kind="observation",
                    )
                    if raw_content is not None
                    else self._artifacts.put_json(
                        run_state.run_id,
                        redact_sensitive_json(json_value),
                        media_type=media_type,
                        kind="observation",
                    )
                )
                run_state.add_artifact_reference(
                    reference.to_dict(),
                    diagnostic=diagnostic,
                )
            except (ArtifactStoreError, OSError, TypeError, ValueError):
                run_state.artifacts_degraded = True
                run_state.append_history(
                    HistoryEntry.create(
                        event="artifact_store_degraded",
                        node=run_state.current_node,
                        step_id=observation.step_id,
                        payload={
                            "artifact_kind": "observation",
                            "artifact_count": len(candidates),
                        },
                    )
                )
                return

    def _load_workflow_modules(self, workflow_id: str) -> dict:
        return load_workflow_modules(workflow_id)

    @staticmethod
    def _normalize_max_steps(constraints: dict) -> int | None:
        value = constraints.get("max_steps")
        if value is None:
            return None
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
            or value > MAX_RUNTIME_STEPS
        ):
            raise ValueError(f"constraints.max_steps must be an integer between 1 and {MAX_RUNTIME_STEPS}")
        return value

    @staticmethod
    def _find_final_step_id(graph_module) -> str | None:
        definitions = getattr(graph_module, "NODE_DEFINITIONS", {})
        if not isinstance(definitions, dict):
            return None
        for key, definition in definitions.items():
            if getattr(definition, "final", False):
                step_id = getattr(definition, "step_id", key)
                return step_id if isinstance(step_id, str) and step_id.strip() else None
        return None

    @staticmethod
    def _terminalize_workflow_graph_state(
        graph_state: object,
        final_step_id: str,
    ) -> object:
        """Synchronize workflow-owned state when the runtime budget hard-stops a run."""

        if not isinstance(graph_state, dict):
            return graph_state
        terminal_state = dict(graph_state)
        if "current_stage_id" in terminal_state:
            terminal_state["current_stage_id"] = final_step_id
        if "terminal_reason" in terminal_state:
            terminal_state["terminal_reason"] = "max_steps_exceeded"
        for key, value in {
            "return_stage_id": None,
            "repair_context": {},
            "repair_category": None,
            "repair_summary": None,
            "repair_requirements": [],
            "repair_evidence": [],
            "repair_transition_reason": None,
            "repair_blocked_attempts": 0,
            "unblocking_blocking_reason": None,
            "unblocking_user_action_needed": None,
            "unblocking_suggested_next_input": None,
        }.items():
            if key in terminal_state:
                terminal_state[key] = value
        return terminal_state

    @staticmethod
    def _observation_fingerprint(observation: Observation) -> str:
        canonical = json.dumps(
            observation.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _build_retry_context(
        self,
        modules: dict,
        run_state: RunState,
        *,
        workflow_state_snapshot=None,
    ) -> dict | None:
        state_module = modules.get("state")
        if state_module is None:
            return None
        deserialize_state = getattr(state_module, "deserialize_state", None)
        if not callable(deserialize_state):
            return None
        if workflow_state_snapshot is not None:
            state = workflow_state_snapshot
        else:
            graph_state_payload = run_state.graph_state if isinstance(run_state.graph_state, dict) else {}
            state = deserialize_state(graph_state_payload)
        repair_context = getattr(state, "repair_context", None)
        if not isinstance(repair_context, dict):
            return None
        repair_payload = repair_context.get("repair_payload")
        if not isinstance(repair_payload, dict):
            return None
        category = str(repair_payload.get("category") or "").strip()
        summary = str(repair_payload.get("summary") or "").strip()
        requirements_raw = repair_payload.get("requirements")
        requirements = []
        if isinstance(requirements_raw, list):
            requirements = [
                str(item).strip()
                for item in requirements_raw
                if isinstance(item, str) and str(item).strip()
            ]
        if not category and not summary and not requirements:
            return None
        return {
            "category": category or "failed",
            "summary": summary or "Repair is required before the workflow can continue.",
            "requirements": requirements,
        }
