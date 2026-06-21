from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SKILL_RUNTIME_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BINDING_CONFIG_PATH = SKILL_ROOT / "workflow-binding.json"
BINDING_CONFIG_ENV_VAR = "DURABLE_WORKFLOW_RUNTIME_BINDING_CONFIG_PATH"
if str(SKILL_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_RUNTIME_ROOT))

from runtime.errors import (
    BootstrapError,
    ObservationValidationError,
    ProtocolError,
    RequestValidationError,
    WorkflowExecutionError,
)


def _binding_config_path() -> Path:
    override = os.environ.get(BINDING_CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_BINDING_CONFIG_PATH

def preflight(repo_root: str, workflow_id: str) -> dict:
    repo_path = _resolve_repo_root(repo_root)
    runtime_root = _resolve_runtime_root()
    _bootstrap_runtime_imports(runtime_root)
    resolved_workflow_id = _resolve_start_workflow_id(runtime_root, workflow_id=workflow_id)
    return _run_dependency_preflight(repo_path, runtime_root, resolved_workflow_id)


def start(repo_root: str, request: dict, workflow_id: str | None = None) -> dict:
    repo_path = _resolve_repo_root(repo_root)
    runtime_root = _resolve_runtime_root()
    _validate_start_request(request)
    _bootstrap_runtime_imports(runtime_root)
    workflow_id = _resolve_start_workflow_id(runtime_root, workflow_id=workflow_id)
    preflight_result = _run_dependency_preflight(repo_path, runtime_root, workflow_id)
    if preflight_result.get("status") == "invalid_manifest":
        raise BootstrapError(preflight_result.get("message") or "workflow manifest is invalid")
    if preflight_result.get("status") == "error":
        raise WorkflowExecutionError(preflight_result.get("message") or "workflow dependency preflight failed")
    if preflight_result.get("status") == "needs_install":
        return {
            "kind": "blocked",
            "blocked_reason": "dependency_install_required",
            "workflow_id": workflow_id,
            "message": "Required workflow dependencies are missing.",
            "preflight_result": preflight_result,
            "install_plan": preflight_result.get("install_plan", []),
        }
    engine = _load_engine(repo_path)
    return _attach_next_step_recommendations(engine.start(workflow_id, request))


def resume(repo_root: str, run_id: str, observation: dict) -> dict:
    repo_path = _resolve_repo_root(repo_root)
    runtime_root = _resolve_runtime_root()
    _validate_observation(run_id, observation)
    _bootstrap_runtime_imports(runtime_root)
    engine = _load_engine(repo_path)
    return _attach_next_step_recommendations(engine.resume(run_id, observation))


def _resolve_repo_root(repo_root: str) -> Path:
    path = Path(repo_root).expanduser().resolve()
    if not path.exists():
        raise BootstrapError(f"repo root does not exist: {path}")
    return path


def _resolve_runtime_root() -> Path:
    runtime_root = SKILL_RUNTIME_ROOT
    required_paths = [
        runtime_root,
        runtime_root / "runtime",
        runtime_root / "workflows",
        runtime_root / "adapters" / "skill_host.py",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise BootstrapError(f"skill-bundled runtime is missing required paths: {', '.join(missing)}")
    return runtime_root


def _load_binding_config() -> dict:
    binding_config_path = _binding_config_path()
    if not binding_config_path.exists():
        raise BootstrapError(f"missing workflow binding config: {binding_config_path}")
    try:
        payload = json.loads(binding_config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BootstrapError(f"invalid workflow binding config JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise BootstrapError("workflow binding config must be a JSON object")
    return payload


def _load_default_workflow_id(runtime_root: Path) -> str:
    payload = _load_binding_config()

    workflow_id = payload.get("default_workflow_id")
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise BootstrapError("workflow binding config must define non-empty default_workflow_id")

    workflow_id = workflow_id.strip()
    _validate_workflow_is_available(runtime_root, workflow_id=workflow_id, payload=payload)
    return workflow_id


def _resolve_start_workflow_id(runtime_root: Path, workflow_id: str | None) -> str:
    if workflow_id is None:
        return _load_default_workflow_id(runtime_root)
    resolved_workflow_id = workflow_id.strip()
    if not resolved_workflow_id:
        raise BootstrapError("workflow_id must be non-empty when provided")
    payload = _load_binding_config()
    _validate_workflow_is_available(runtime_root, workflow_id=resolved_workflow_id, payload=payload)
    return resolved_workflow_id


def _validate_workflow_is_available(runtime_root: Path, *, workflow_id: str, payload: dict) -> None:
    catalog = payload.get("workflows", [])
    if not isinstance(catalog, list):
        raise BootstrapError("workflow binding config field 'workflows' must be a list")
    selected_entry = None
    published_ids = {
        item.get("workflow_id", "").strip()
        for item in catalog
        if isinstance(item, dict) and isinstance(item.get("workflow_id"), str)
    }
    for item in catalog:
        if (
            isinstance(item, dict)
            and isinstance(item.get("workflow_id"), str)
            and item["workflow_id"].strip() == workflow_id
        ):
            selected_entry = item
            break
    if workflow_id not in published_ids:
        raise BootstrapError(f"workflow is not published in binding catalog: {workflow_id}")

    workflow_dir = runtime_root / "workflows" / workflow_id
    if not workflow_dir.is_dir():
        raise BootstrapError(f"configured workflow does not exist: {workflow_id}")

    _bootstrap_runtime_imports(runtime_root)
    try:
        from runtime.module_loader import load_workflow_modules

        modules = load_workflow_modules(workflow_id)
    except Exception as exc:
        raise BootstrapError(f"failed to load workflow modules for {workflow_id}: {exc}") from exc
    if selected_entry is None:
        raise BootstrapError(f"workflow catalog entry is invalid: {workflow_id}")
    if _sync_binding_start_input_schema(payload, selected_entry, modules["contract"].WORKFLOW_INPUT_CONTRACT):
        _write_binding_config(payload)


def _bootstrap_runtime_imports(runtime_root: Path) -> None:
    runtime_root_text = str(runtime_root)
    if runtime_root_text not in sys.path:
        sys.path.insert(0, runtime_root_text)


def _sync_binding_start_input_schema(payload: dict, workflow_entry: dict, input_contract) -> bool:
    expected_schema = input_contract.to_start_input_schema()
    current_schema = workflow_entry.get("start_input_schema")
    if current_schema is None:
        workflow_entry["start_input_schema"] = expected_schema
        return True
    if current_schema != expected_schema:
        workflow_id = workflow_entry.get("workflow_id", "<unknown>")
        raise BootstrapError(
            "workflow binding start_input_schema does not match "
            f"WORKFLOW_INPUT_CONTRACT for {workflow_id}"
        )
    return False


def _write_binding_config(payload: dict) -> None:
    binding_config_path = _binding_config_path()
    binding_config_path.parent.mkdir(parents=True, exist_ok=True)
    binding_config_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _attach_next_step_recommendations(response: dict) -> dict:
    if response.get("kind") != "done":
        return response

    workflow_id = _response_workflow_id(response)
    if workflow_id is None:
        return response

    response["next_step_recommendations"] = {
        "kind": "workflow_catalog_lookup",
        "source_workflow_id": workflow_id,
        "instructions": [
            "Read workflow-binding.json from the durable-workflow-runtime skill root before recommending the next workflow.",
            "Use catalog entry flow_description and start_input_schema to select a suitable workflow_id.",
            "Do not recommend the source_workflow_id unless the user explicitly wants to rerun it.",
            "If no workflow clearly fits, ask the user which workflow to start next.",
            "Start the selected workflow as a new run; do not call resume on the completed run.",
        ],
    }
    return response


def _response_workflow_id(response: dict) -> str | None:
    envelope = response.get("final_prompt_envelope")
    if not isinstance(envelope, dict):
        return None
    metadata = envelope.get("metadata")
    if not isinstance(metadata, dict):
        return None
    workflow_id = metadata.get("workflow_id")
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        return None
    return workflow_id.strip()


def _load_engine(repo_root: Path):
    try:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine
    except Exception as exc:  # pragma: no cover - bootstrapping failure path
        raise BootstrapError(f"failed to import runtime engine: {exc}") from exc
    return GraphBuilderRuntimeEngine(repo_root)


def _run_dependency_preflight(repo_root: Path, runtime_root: Path, workflow_id: str) -> dict:
    from runtime.dependency_preflight import build_preflight_result

    return build_preflight_result(
        repo_root=repo_root,
        runtime_root=runtime_root,
        workflow_id=workflow_id,
    )


def _validate_start_request(request: dict) -> None:
    if not isinstance(request, dict):
        raise RequestValidationError("start request must be a JSON object")
    for field_name in ("task_input", "context", "constraints"):
        if field_name not in request:
            raise RequestValidationError(f"start request missing field: {field_name}")


def _validate_observation(run_id: str, observation: dict) -> None:
    if not isinstance(observation, dict):
        raise ObservationValidationError("observation must be a JSON object")
    for field_name in ("run_id", "step_id", "status", "summary", "structured_output"):
        if field_name not in observation:
            raise ObservationValidationError(f"observation missing field: {field_name}")
    if observation.get("run_id") != run_id:
        raise ObservationValidationError("observation run_id does not match CLI run_id")
