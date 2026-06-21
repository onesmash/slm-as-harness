from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from runtime.errors import ObservationValidationError, ProtocolError
from runtime.module_loader import load_workflow_modules
from runtime.models import (
    DoneResponse,
    HistoryEntry,
    Observation,
    PromptEnvelope,
    RunState,
    StartRequest,
    YieldResponse,
)
from runtime.persistence import FileRunStateStore
from runtime.validation import validate_observation_against_contract, validate_workflow_input
from runtime.verifier_runner import run_step_verifier
from workflows.common.prompting import build_prompt_envelope


class GraphBuilderRuntimeEngine:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._store = FileRunStateStore(self.repo_root)
        self._runs: dict[str, RunState] = {}

    def start(self, workflow_id: str, request_payload: dict) -> dict:
        request = StartRequest.from_dict(request_payload)
        modules = self._load_workflow_modules(workflow_id)
        graph_module = modules["graphbuilder_runtime"]
        validate_workflow_input(request, modules["contract"].WORKFLOW_INPUT_CONTRACT)

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
        self._runs[run_id] = run_state
        self._store.save(run_state)
        return response.to_dict()

    def resume(self, run_id: str, observation_payload: dict) -> dict:
        run_state = self._runs.get(run_id)
        if run_state is None:
            run_state = self._store.load(run_id)
            if run_state is not None:
                self._runs[run_id] = run_state
        if run_state is None:
            raise ProtocolError(f"unknown run_id: {run_id}")
        if run_state.status == "done":
            raise ProtocolError(f"cannot resume terminal run: {run_id}")

        try:
            observation = Observation.from_dict(observation_payload)
        except ValueError as exc:
            raise ObservationValidationError(str(exc)) from exc
        if observation.run_id != run_id:
            raise ProtocolError("observation run_id does not match requested run_id")
        if observation.step_id != run_state.current_node:
            raise ProtocolError("observation step_id does not match current node")

        modules = self._load_workflow_modules(run_state.workflow_id)
        graph_module = modules["graphbuilder_runtime"]
        step_contract = modules["contract"].get_step_contract(observation.step_id)
        validate_observation_against_contract(observation, step_contract)
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

        preview = graph_module.run_transition_preview(
            state=modules["state"].deserialize_state(
                run_state.graph_state if isinstance(run_state.graph_state, dict) else {}
            ),
            current_step_id=run_state.current_node,
            observation=observation.to_dict(),
            verifier_result=verifier_result,
        )
        preview_state_payload = getattr(preview, "state_payload", None)
        if isinstance(preview_state_payload, dict):
            run_state.graph_state = preview_state_payload
        run_state.append_history(preview.history_entry)

        node_definition = modules["graphbuilder_runtime"].get_node_definition(preview.step_id)
        response_kind = "done" if getattr(node_definition, "final", False) else "yield"
        response = self._emit_step_response(run_state, modules, preview.step_id, response_kind=response_kind)
        self._runs[run_id] = run_state
        self._store.save(run_state)
        return response.to_dict()

    def _emit_step_response(self, run_state: RunState, modules: dict, step_id: str, *, response_kind: str):
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
            },
        )
        run_state.status = "done"
        run_state.current_node = step_id
        run_state.append_history(
            HistoryEntry.create(
                event="run_done",
                node=step_id,
                step_id=step_id,
                payload={"reason": "workflow completed"},
            )
        )
        return DoneResponse(
            run_id=run_state.run_id,
            step_id=step_id,
            final_prompt_envelope=prompt_envelope,
        )

    def _load_workflow_modules(self, workflow_id: str) -> dict:
        return load_workflow_modules(workflow_id)
