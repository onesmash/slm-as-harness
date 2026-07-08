from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from pprint import pformat
from typing import Any


WORKFLOW_CREATOR_SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_SKILL_ROOT = WORKFLOW_CREATOR_SKILL_ROOT.parent
_WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DEFAULT_START_INPUT_SCHEMA = {
    "task_input": {
        "goal": "string",
        "deliverable_type": "string?",
    },
    "context": {
        "repo_root": "string",
    },
    "constraints": {
        "max_steps": "integer?",
    },
}
_DEFAULT_FAILURE_SCHEMA = {
    "blocked_reason": "string?",
    "error_message": "string?",
    "missing_inputs": "string[]?",
}
_SUPPORTED_DEPENDENCY_TYPES = {"skill", "cli", "python_package", "mcp"}
_SUPPORTED_DEPENDENCY_SCOPES = {"project", "global", "either"}
_SUPPORTED_REPAIR_OPERATORS = {
    "equals",
    "not_equals",
    "is_true",
    "is_false",
    "truthy",
    "falsey",
    "missing",
    "non_empty",
    "empty",
}
_SUPPORTED_VERIFIER_OPERATORS = _SUPPORTED_REPAIR_OPERATORS | {"one_of", "path_exists"}
_SUPPORTED_VERIFIER_TEMPLATES = {
    "artifact_file_contains_sections",
    "conditional_equals",
    "conditional_required",
    "min_count",
    "repo_path_policy",
    "required_set_members",
}
_SUPPORTED_STAGE_KINDS = {"main", "recovery"}
_SUPPORTED_OUTCOMES = {"blocked", "partial", "failed", "verifier_failed"}
_REPAIR_STAGE_IDS = {"request_unblocking_input", "repair_and_resume"}
_REPAIR_ATTEMPTS_BEFORE_UNBLOCK = 3
_SKILL_CATALOG_SOURCE_PREFIX = "skill-catalog:"
_CUSTOM_VERIFIER_TEMPLATE_VERSION = 1
_DEFAULT_PROMPT_BOUNDARIES = [
    "Do not choose the next workflow stage; runtime policy owns routing.",
    "Do not continue by guessing when required input, approval, or artifacts are missing.",
]
_DEFAULT_PROMPT_BLOCKED_CONDITIONS = [
    "If required input, approval, credentials, files, or decisions are missing, return blocked instead of inventing them.",
]

RUNTIME_SCRIPTS_ROOT = DEFAULT_RUNTIME_SKILL_ROOT / "scripts"

if str(RUNTIME_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_SCRIPTS_ROOT))

from workflow_shortcut_skill import ensure_workflow_shortcut_skill


class WorkflowCreatorError(ValueError):
    pass


def _default_shared_repair_helpers() -> dict[str, dict[str, Any]]:
    return {
        "request_unblocking_input": {
            "intent": "request_unblocking_input",
            "expected_artifact": "user action needed to unblock the workflow",
            "prompt": "Request the exact external input needed to unblock the workflow, then return control to the repair stage when repair still owns the retry.",
            "prompt_sections": {
                "stage_goal": "Identify the exact external input, approval, credential, file, or decision required to unblock the workflow, while preserving whether the next hop should return to repair or directly to the original stage.",
                "context": [
                    "Current step: {{current_step_id}}",
                    "Return stage: {{return_stage_id}}",
                    "Source stage: {{source_stage_id}}",
                    "Repair category: {{repair_category}}",
                    "Repair summary: {{repair_summary}}",
                    "Required external inputs or approvals:",
                    "{{repair_requirements}}",
                    "Relevant evidence:",
                    "{{repair_evidence}}",
                ],
                "boundaries": [
                    "Do not resume the workflow until the exact missing external dependency is identified.",
                    "Do not invent files, credentials, or user decisions that are not already available.",
                    f"Use this helper only after repair has already attempted self-repair {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} times and still requires external help.",
                ],
                "blocked_conditions": [
                    "Stay blocked if the missing external input still cannot be named concretely.",
                ],
            },
            "done_when": [
                "Identify the blocking reason",
                "Ask the user for the input, approval, or resource required to continue",
            ],
            "output_schema": {
                "blocking_reason": "string",
                "user_action_needed": "string",
                "suggested_next_input": "string?",
            },
            "failure_schema": dict(_DEFAULT_FAILURE_SCHEMA),
        },
        "repair_and_resume": {
            "intent": "repair_and_resume",
            "expected_artifact": "repair actions needed before returning to the original stage",
            "prompt": "Repair the previous workflow step using the persisted failure details, and decide whether the workflow can retry directly or must first ask for external unblocking input.",
            "prompt_sections": {
                "stage_goal": "Use the persisted repair context to explain what failed, propose concrete repair actions, and decide whether the workflow can retry the original stage safely or must first request external help.",
                "context": [
                    "Current step: {{current_step_id}}",
                    "Return stage: {{return_stage_id}}",
                    "Source stage: {{source_stage_id}}",
                    "Repair category: {{repair_category}}",
                    "Repair summary: {{repair_summary}}",
                    "Repair requirements:",
                    "{{repair_requirements}}",
                    "Relevant evidence:",
                    "{{repair_evidence}}",
                ],
                "boundaries": [
                    "Keep the retry scoped to the original return stage instead of changing workflow routing.",
                    "Base the repair plan on the persisted repair requirements rather than generic retries.",
                    f"Attempt self-repair up to {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} times before escalating to request_unblocking_input.",
                ],
                "blocked_conditions": [
                    f"Return blocked only when repair still cannot proceed after {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} self-repair attempts and now requires external input or approval.",
                ],
            },
            "done_when": [
                "Explain why the original step needs repair",
                "Return retry_reason, retry_notes, and repair_actions",
            ],
            "output_schema": {
                "retry_reason": "string",
                "retry_notes": "string",
                "repair_actions": "string[]",
            },
            "failure_schema": dict(_DEFAULT_FAILURE_SCHEMA),
        },
    }


def create_workflow_scaffold(
    *,
    runtime_skill_root: str | Path,
    workflow_id: str | None = None,
    flow_description: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    runtime_root = _resolve_runtime_skill_root(runtime_skill_root)
    requested_workflow_id = _validate_workflow_id(str(workflow_id or ""))
    binding_path = runtime_root / "workflow-binding.json"
    workflows_root = runtime_root / "workflow-runtime" / "workflows"
    skeleton_dir = runtime_root / "workflow-runtime" / "templates" / "workflow_skeleton"
    target_workflow_dir = workflows_root / requested_workflow_id
    temp_workflow_dir = workflows_root / f".{requested_workflow_id}.creator-tmp"
    backup_workflow_dir = workflows_root / f".{requested_workflow_id}.creator-backup"

    binding_payload = _load_json_object(binding_path, "workflow binding config")
    existing_binding_index = _find_binding_index(binding_payload, requested_workflow_id)
    target_exists = target_workflow_dir.exists()
    if (target_exists or existing_binding_index is not None) and not force:
        raise WorkflowCreatorError(
            f"workflow already exists; pass --force to replace: {requested_workflow_id}"
        )

    workflow_spec = _load_workflow_spec(
        spec_file=(target_workflow_dir / "spec.json") if target_exists else None,
        workflow_id=requested_workflow_id,
        flow_description=flow_description,
    )
    existing_verifiers_text = None
    if target_exists:
        existing_verifiers_path = target_workflow_dir / "verifiers.py"
        if existing_verifiers_path.exists():
            existing_verifiers_text = existing_verifiers_path.read_text(encoding="utf-8")
    resolved_workflow_id = workflow_spec["workflow_id"]
    if resolved_workflow_id != requested_workflow_id:
        raise WorkflowCreatorError(
            "workflow blueprint workflow_id does not match requested workflow_id"
        )
    description = workflow_spec["flow_description"]
    start_input_schema = workflow_spec["start_input_schema"]

    _remove_path(temp_workflow_dir)
    _remove_path(backup_workflow_dir)
    shutil.copytree(skeleton_dir, temp_workflow_dir)
    _rewrite_scaffold_identifiers(temp_workflow_dir, resolved_workflow_id)
    generation_warnings: list[str] = []
    if workflow_spec["stages"]:
        generation_warnings.extend(
            _render_business_workflow(
                temp_workflow_dir,
                workflow_spec,
                existing_verifiers_text=existing_verifiers_text,
            )
        )
    _write_spec_blueprint(temp_workflow_dir, workflow_spec)
    _write_agent_review_file(temp_workflow_dir, workflow_spec)
    _write_manifest(
        temp_workflow_dir / "manifest.json",
        workflow_id=resolved_workflow_id,
        description=description,
        start_input_schema=start_input_schema,
        dependencies=workflow_spec["dependencies"],
    )
    _write_workflow_lockfile(
        temp_workflow_dir / ".workflow-lock.json",
        workflow_id=resolved_workflow_id,
        installed=workflow_spec["installed"],
    )
    created_files = sum(1 for path in temp_workflow_dir.rglob("*") if path.is_file())
    replaced_existing = target_exists or existing_binding_index is not None
    regression_tests_file = (
        target_workflow_dir / "tests" / "test_workflow.py"
        if workflow_spec["regression_tests"]
        else None
    )

    try:
        if target_exists:
            target_workflow_dir.replace(backup_workflow_dir)
        temp_workflow_dir.replace(target_workflow_dir)
        _register_binding_entry(
            binding_path=binding_path,
            binding_payload=binding_payload,
            binding_entry={
                "workflow_id": resolved_workflow_id,
                "flow_description": description,
                "start_input_schema": start_input_schema,
            },
            existing_index=existing_binding_index,
        )
        if regression_tests_file is not None:
            _write_generated_regression_tests(regression_tests_file, workflow_spec)
            created_files += 1
        shortcut_payload = ensure_workflow_shortcut_skill(
            runtime_skill_root=runtime_root,
            workflow_id=resolved_workflow_id,
        )
        _remove_path(backup_workflow_dir)
    except Exception:
        _remove_path(target_workflow_dir)
        if backup_workflow_dir.exists():
            backup_workflow_dir.replace(target_workflow_dir)
        raise
    finally:
        _remove_path(temp_workflow_dir)

    return {
        "kind": "workflow_scaffold",
        "workflow_id": resolved_workflow_id,
        "workflow_dir": str(target_workflow_dir),
        "binding_file": str(binding_path),
        "spec_blueprint_file": str(target_workflow_dir / "spec.json"),
        "agent_review_required": True,
        "agent_review_file": str(target_workflow_dir / "references" / "agent-review.md"),
        "regression_tests_file": str(regression_tests_file) if regression_tests_file else None,
        "next_actions": [
            "Use spec.json as the workflow blueprint before making future workflow changes.",
            f"Edit workflow-runtime/workflows/{resolved_workflow_id}/spec.json, then rerun create_workflow.py with --workflow-id {resolved_workflow_id} --force to regenerate workflow files.",
            "Translate any generated custom verifier scaffolds and domain-specific routing needs into concrete workflow code before review sign-off.",
            "Run the required subagent-backed agent review using references/agent-review.md before treating the workflow as shipped.",
            "Tighten generated verifiers, business repair routing, state promotion, and tests based on that review.",
        ],
        "replaced_existing": replaced_existing,
        "created_files": created_files,
        "warnings": generation_warnings,
        **shortcut_payload,
    }


def migrate_legacy_custom_verifier_metadata(
    *,
    runtime_skill_root: str | Path,
    workflow_id: str | None = None,
) -> dict[str, Any]:
    runtime_root = _resolve_runtime_skill_root(runtime_skill_root)
    workflows_root = runtime_root / "workflow-runtime" / "workflows"
    requested_workflow_ids = (
        [_validate_workflow_id(workflow_id)]
        if workflow_id is not None
        else _discover_migratable_workflow_ids(workflows_root)
    )

    scanned_workflows: list[str] = []
    migrated_workflows: list[str] = []
    workflow_results: list[dict[str, Any]] = []
    all_warnings: list[str] = []

    for current_workflow_id in requested_workflow_ids:
        workflow_dir = workflows_root / current_workflow_id
        if not workflow_dir.exists():
            raise WorkflowCreatorError(f"workflow does not exist: {current_workflow_id}")

        scanned_workflows.append(current_workflow_id)
        spec_path = workflow_dir / "spec.json"
        verifiers_path = workflow_dir / "verifiers.py"
        if not spec_path.exists() or not verifiers_path.exists():
            warning = "Skipped workflow because spec.json or verifiers.py is missing."
            workflow_results.append(
                {
                    "workflow_id": current_workflow_id,
                    "migrated": False,
                    "warnings": [warning],
                }
            )
            all_warnings.append(f"{current_workflow_id}: {warning}")
            continue

        workflow_spec = _load_workflow_spec(
            spec_file=spec_path,
            workflow_id=current_workflow_id,
            flow_description=None,
        )
        existing_verifiers_text = verifiers_path.read_text(encoding="utf-8")
        rendered_verifiers_text, warnings = _render_verifiers_py(
            workflow_spec,
            existing_verifiers_text=existing_verifiers_text,
        )
        migration_warnings = [
            warning
            for warning in warnings
            if warning.startswith(
                "Migrated legacy custom verifier implementation without preservation metadata for "
            )
        ]
        migrated = bool(migration_warnings)
        if migrated and rendered_verifiers_text != existing_verifiers_text:
            verifiers_path.write_text(rendered_verifiers_text, encoding="utf-8")
            migrated_workflows.append(current_workflow_id)

        workflow_results.append(
            {
                "workflow_id": current_workflow_id,
                "migrated": migrated,
                "warnings": warnings,
            }
        )
        all_warnings.extend(f"{current_workflow_id}: {warning}" for warning in warnings)

    return {
        "kind": "legacy_custom_verifier_metadata_migration",
        "runtime_skill_root": str(runtime_root),
        "scanned_workflows": scanned_workflows,
        "migrated_workflows": migrated_workflows,
        "workflow_results": workflow_results,
        "warnings": all_warnings,
    }


def _discover_migratable_workflow_ids(workflows_root: Path) -> list[str]:
    workflow_ids: list[str] = []
    for path in sorted(workflows_root.iterdir(), key=lambda item: item.name):
        if not path.is_dir():
            continue
        if not (path / "spec.json").exists():
            continue
        if not (path / "verifiers.py").exists():
            continue
        workflow_ids.append(path.name)
    return workflow_ids


def _resolve_runtime_skill_root(runtime_skill_root: str | Path) -> Path:
    path = Path(runtime_skill_root).expanduser().resolve()
    required_paths = [
        path / "workflow-binding.json",
        path / "workflow-runtime",
        path / "workflow-runtime" / "templates" / "workflow_skeleton",
        path / "workflow-runtime" / "workflows",
    ]
    missing = [str(item) for item in required_paths if not item.exists()]
    if missing:
        raise WorkflowCreatorError(f"missing durable-workflow-runtime paths: {', '.join(missing)}")
    return path


def _validate_workflow_id(workflow_id: str) -> str:
    if not isinstance(workflow_id, str):
        raise WorkflowCreatorError("workflow_id must be a string")
    resolved = workflow_id.strip()
    if not _WORKFLOW_ID_PATTERN.fullmatch(resolved):
        raise WorkflowCreatorError(
            "workflow_id must be a Python package identifier: [A-Za-z_][A-Za-z0-9_]*"
        )
    if resolved in {"_", "__"}:
        raise WorkflowCreatorError("workflow_id must be descriptive")
    return resolved


def _validate_flow_description(flow_description: str) -> str:
    if not isinstance(flow_description, str) or not flow_description.strip():
        raise WorkflowCreatorError("flow_description must be a non-empty string")
    return flow_description.strip()


def _load_workflow_spec(
    *,
    spec_file: str | Path | None,
    workflow_id: str | None,
    flow_description: str | None,
) -> dict[str, Any]:
    raw_spec: dict[str, Any] = {}
    if spec_file is not None:
        raw_spec = _load_json_object(Path(spec_file).expanduser().resolve(), "workflow spec")

    resolved_workflow_id = _validate_workflow_id(
        str(raw_spec.get("workflow_id") or workflow_id or "")
    )
    description = _validate_flow_description(
        str(raw_spec.get("flow_description") or flow_description or "")
    )
    start_input_schema = _validate_start_input_schema(
        raw_spec.get("start_input_schema") or _DEFAULT_START_INPUT_SCHEMA
    )
    final_step_id = _validate_step_id(str(raw_spec.get("final_step_id") or "finalize_summary"))
    stages = _validate_stages(raw_spec.get("stages") or [])
    _validate_stage_transition_targets(stages, final_step_id)
    shared_repair_helpers = _validate_shared_repair_helpers(
        raw_spec.get("shared_repair_helpers")
    )
    regression_tests = _validate_regression_tests(
        raw_spec.get("regression_tests") or [],
        stages=stages,
        final_step_id=final_step_id,
    )
    dependencies = _validate_dependencies(raw_spec.get("dependencies") or [])
    installed = _validate_installed(raw_spec.get("installed") or [])
    dependencies, installed = _normalize_internal_skill_references(
        stages=stages,
        dependencies=dependencies,
        installed=installed,
    )
    return {
        "workflow_id": resolved_workflow_id,
        "flow_description": description,
        "start_input_schema": start_input_schema,
        "stages": stages,
        "shared_repair_helpers": shared_repair_helpers,
        "final_step_id": final_step_id,
        "final_prompt": _validate_text(
            raw_spec.get("final_prompt")
            or "Summarize the completed workflow for the user. Include completed stages, key artifacts, and any follow-up work.",
            "final_prompt",
        ),
        "dependencies": dependencies,
        "installed": installed,
        "regression_tests": regression_tests,
    }


def _normalize_internal_skill_references(
    *,
    stages: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    installed: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    aliases = _build_internal_skill_aliases(dependencies=dependencies, installed=installed)
    if not aliases:
        return dependencies, installed

    for stage in stages:
        for route in stage["skill_routing"]:
            route["skill"] = aliases.get(route["skill"], route["skill"])

    normalized_dependencies: list[dict[str, Any]] = []
    for dependency in dependencies:
        normalized_dependencies = _append_normalized_dependency(
            normalized_dependencies,
            _normalize_skill_dependency(dependency, aliases),
        )

    normalized_installed: list[dict[str, Any]] = []
    for installed_item in installed:
        normalized_installed = _append_unique_by_id(
            normalized_installed,
            _normalize_installed_skill_item(installed_item, aliases),
        )

    return normalized_dependencies, normalized_installed


def _build_internal_skill_aliases(
    *,
    dependencies: list[dict[str, Any]],
    installed: list[dict[str, Any]],
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item in [*dependencies, *installed]:
        if item["type"] != "skill":
            continue
        parent_skill_id = _skill_catalog_parent_id(item["source"])
        if parent_skill_id is None or parent_skill_id == item["id"]:
            continue
        existing = aliases.get(item["id"])
        if existing is not None and existing != parent_skill_id:
            raise WorkflowCreatorError(
                f"skill dependency {item['id']} maps to conflicting parent skills: {existing}, {parent_skill_id}"
            )
        aliases[item["id"]] = parent_skill_id
    return aliases


def _skill_catalog_parent_id(source: str) -> str | None:
    if not source.startswith(_SKILL_CATALOG_SOURCE_PREFIX):
        return None
    source_ref = source[len(_SKILL_CATALOG_SOURCE_PREFIX) :].strip("/")
    source_parts = [part for part in source_ref.split("/") if part]
    if len(source_parts) < 2:
        return None
    return source_parts[0]


def _normalize_skill_dependency(
    dependency: dict[str, Any],
    aliases: dict[str, str],
) -> dict[str, Any]:
    if dependency["type"] != "skill" or dependency["id"] not in aliases:
        return dependency
    parent_skill_id = aliases[dependency["id"]]
    normalized = dict(dependency)
    normalized["id"] = parent_skill_id
    normalized["source"] = f"{_SKILL_CATALOG_SOURCE_PREFIX}{parent_skill_id}"
    normalized["purpose"] = (
        f"Use `{parent_skill_id}` as the installable parent skill for "
        f"`{dependency['id']}` capabilities"
    )
    return normalized


def _normalize_installed_skill_item(
    installed_item: dict[str, Any],
    aliases: dict[str, str],
) -> dict[str, Any]:
    if installed_item["type"] != "skill" or installed_item["id"] not in aliases:
        return installed_item
    parent_skill_id = aliases[installed_item["id"]]
    normalized = dict(installed_item)
    normalized["id"] = parent_skill_id
    normalized["source"] = f"{_SKILL_CATALOG_SOURCE_PREFIX}{parent_skill_id}"
    return normalized


def _append_normalized_dependency(
    dependencies: list[dict[str, Any]],
    dependency: dict[str, Any],
) -> list[dict[str, Any]]:
    existing = next(
        (
            item
            for item in dependencies
            if item["id"] == dependency["id"] and item["type"] == dependency["type"]
        ),
        None,
    )
    if existing is None:
        return [*dependencies, dependency]
    if dependency.get("required") is True:
        existing["required"] = True
    if existing.get("scope") != dependency.get("scope"):
        existing["scope"] = "either"
    if dependency["purpose"] not in existing["purpose"]:
        existing["purpose"] = f"{existing['purpose']}; {dependency['purpose']}"
    if existing.get("install_command") is None and dependency.get("install_command") is not None:
        existing["install_command"] = dependency["install_command"]
    return dependencies


def _append_unique_by_id(items: list[dict[str, Any]], item: dict[str, Any]) -> list[dict[str, Any]]:
    if any(existing["id"] == item["id"] and existing["type"] == item["type"] for existing in items):
        return items
    return [*items, item]


def _validate_start_input_schema(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowCreatorError("start_input_schema must be a JSON object")
    for key in ("task_input", "context", "constraints"):
        if key not in value or not isinstance(value[key], dict):
            raise WorkflowCreatorError(
                "start_input_schema must contain object fields: task_input, context, constraints"
            )
    return value


def _validate_stages(value: Any) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError("workflow spec field 'stages' must be a list")
    stages: list[dict[str, Any]] = []
    seen_step_ids: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"stage #{index + 1} must be a JSON object")
        step_id = _validate_step_id(str(item.get("step_id") or ""))
        if step_id in seen_step_ids:
            raise WorkflowCreatorError(f"duplicate stage step_id: {step_id}")
        seen_step_ids.add(step_id)
        stages.append(
            {
                "step_id": step_id,
                "stage_kind": _validate_stage_kind(
                    item.get("stage_kind") or "main",
                    f"{step_id}.stage_kind",
                ),
                "recovery_return_node": (
                    _validate_step_id(str(item.get("recovery_return_node") or ""))
                    if item.get("recovery_return_node") is not None
                    else None
                ),
                "intent": _validate_text(item.get("intent") or step_id, f"{step_id}.intent"),
                "expected_artifact": _validate_text(
                    item.get("expected_artifact") or f"{step_id} artifact",
                    f"{step_id}.expected_artifact",
                ),
                "prompt": _validate_text(item.get("prompt"), f"{step_id}.prompt"),
                "prompt_sections": _validate_prompt_sections(
                    item.get("prompt_sections"),
                    fallback_prompt=_validate_text(item.get("prompt"), f"{step_id}.prompt"),
                    label=f"{step_id}.prompt_sections",
                ),
                "done_when": _validate_string_list(item.get("done_when"), f"{step_id}.done_when"),
                "output_schema": _validate_schema_object(
                    item.get("output_schema"),
                    f"{step_id}.output_schema",
                    allow_object=False,
                ),
                "failure_schema": _validate_schema_object(
                    item.get("failure_schema") or _DEFAULT_FAILURE_SCHEMA,
                    f"{step_id}.failure_schema",
                    allow_object=False,
                ),
                "skill_routing": _validate_skill_routing(
                    item.get("skill_routing") or [],
                    f"{step_id}.skill_routing",
                ),
                "state_updates": _validate_state_updates(
                    item.get("state_updates") or [],
                    f"{step_id}.state_updates",
                ),
                "template_context_keys": _validate_template_context_keys(
                    item.get("template_context_keys") or [],
                    f"{step_id}.template_context_keys",
                ),
                "repair_conditions": _validate_repair_conditions(
                    item.get("repair_conditions") or [],
                    f"{step_id}.repair_conditions",
                ),
                "transitions": _validate_transitions(
                    item.get("transitions") or [],
                    f"{step_id}.transitions",
                ),
                "outcome_routes": _validate_outcome_routes(
                    item.get("outcome_routes") or [],
                    f"{step_id}.outcome_routes",
                ),
                "verifier_rules": _validate_verifier_rules(
                    item.get("verifier_rules") or [],
                    f"{step_id}.verifier_rules",
                ),
                "verifier_templates": _validate_verifier_templates(
                    item.get("verifier_templates") or [],
                    f"{step_id}.verifier_templates",
                ),
                "custom_verifier_requirements": _validate_custom_verifier_requirements(
                    item.get("custom_verifier_requirements") or [],
                    f"{step_id}.custom_verifier_requirements",
                ),
            }
        )
    return stages


def _validate_stage_kind(value: Any, label: str) -> str:
    stage_kind = _validate_text(value, label)
    if stage_kind not in _SUPPORTED_STAGE_KINDS:
        raise WorkflowCreatorError(f"{label} is unsupported: {stage_kind}")
    return stage_kind


def _validate_shared_repair_helpers(value: Any) -> dict[str, dict[str, Any]]:
    defaults = _default_shared_repair_helpers()
    if value in (None, {}):
        return defaults
    if not isinstance(value, dict):
        raise WorkflowCreatorError("workflow spec field 'shared_repair_helpers' must be a JSON object")

    unknown = sorted(set(value.keys()) - set(defaults.keys()))
    if unknown:
        raise WorkflowCreatorError(
            "shared_repair_helpers contains unknown helper ids: " + ", ".join(unknown)
        )

    helpers: dict[str, dict[str, Any]] = {}
    for helper_id, default in defaults.items():
        item = value.get(helper_id) or {}
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"shared_repair_helpers.{helper_id} must be a JSON object")
        prompt = _validate_text(
            item.get("prompt") or default["prompt"],
            f"shared_repair_helpers.{helper_id}.prompt",
        )
        helpers[helper_id] = {
            "intent": helper_id,
            "expected_artifact": _validate_text(
                item.get("expected_artifact") or default["expected_artifact"],
                f"shared_repair_helpers.{helper_id}.expected_artifact",
            ),
            "prompt": prompt,
            "prompt_sections": _validate_prompt_sections(
                item.get("prompt_sections") or default["prompt_sections"],
                fallback_prompt=prompt,
                label=f"shared_repair_helpers.{helper_id}.prompt_sections",
            ),
            "skill_routing": _validate_skill_routing(
                item.get("skill_routing") or [],
                f"shared_repair_helpers.{helper_id}.skill_routing",
            ),
            "done_when": _validate_string_list(
                item.get("done_when") or default["done_when"],
                f"shared_repair_helpers.{helper_id}.done_when",
            ),
            "output_schema": _validate_schema_object(
                item.get("output_schema") or default["output_schema"],
                f"shared_repair_helpers.{helper_id}.output_schema",
                allow_object=False,
            ),
            "failure_schema": _validate_schema_object(
                item.get("failure_schema") or default["failure_schema"],
                f"shared_repair_helpers.{helper_id}.failure_schema",
                allow_object=False,
            ),
        }
    return helpers


def _validate_step_id(value: str) -> str:
    step_id = value.strip()
    if not _WORKFLOW_ID_PATTERN.fullmatch(step_id):
        raise WorkflowCreatorError(
            f"step_id must be a Python identifier: {value!r}"
        )
    return step_id


def _validate_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowCreatorError(f"{label} must be a non-empty string")
    return value.strip()


def _validate_install_source(value: Any, label: str) -> str:
    source = _validate_text(value, label)
    local_markers = (
        ".agents/",
        ".claude/",
        ".codex/",
        "agents/",
        "claude/",
        "codex/",
        "~/",
        "/",
        "./",
        "../",
    )
    if source.startswith(local_markers) or "SKILL.md" in source:
        raise WorkflowCreatorError(
            f"{label} must describe the dependency installation source, not a local resolved path"
        )
    return source


def _validate_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise WorkflowCreatorError(f"{label} must be a non-empty string list")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WorkflowCreatorError(f"{label} must contain only non-empty strings")
        result.append(item.strip())
    return result


_FLAT_SCHEMA_TYPES = {
    "string",
    "boolean",
    "integer",
    "number",
    "string[]",
    "boolean[]",
    "integer[]",
    "number[]",
}


def _validate_schema_object(
    value: Any,
    label: str,
    *,
    allow_object: bool = True,
) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise WorkflowCreatorError(f"{label} must be a non-empty JSON object")
    if allow_object:
        return value
    for key, schema_type in value.items():
        if not isinstance(schema_type, str):
            raise WorkflowCreatorError(f"{label}.{key} must use a flat schema type string")
        normalized = schema_type[:-1] if schema_type.endswith("?") else schema_type
        if normalized not in _FLAT_SCHEMA_TYPES:
            raise WorkflowCreatorError(
                f"{label}.{key} uses unsupported return schema type {schema_type!r}; "
                "workflow stage output and failure schemas must stay flat and cannot use object/object[]"
            )
    return value


def _validate_dependencies(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorkflowCreatorError("workflow spec field 'dependencies' must be a list")
    return [_validate_dependency(item, f"dependencies[{index}]") for index, item in enumerate(value)]


def _validate_dependency(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowCreatorError(f"{label} must be a JSON object")
    dependency_id = _validate_text(value.get("id"), f"{label}.id")
    dependency_type = _validate_text(value.get("type"), f"{label}.type")
    required = value.get("required")
    scope = _validate_text(value.get("scope"), f"{label}.scope")
    source = _validate_install_source(value.get("source"), f"{label}.source")
    purpose = _validate_text(value.get("purpose"), f"{label}.purpose")

    if dependency_type not in _SUPPORTED_DEPENDENCY_TYPES:
        raise WorkflowCreatorError(f"{label}.type is unsupported: {dependency_type}")
    if not isinstance(required, bool):
        raise WorkflowCreatorError(f"{label}.required must be boolean")
    if scope not in _SUPPORTED_DEPENDENCY_SCOPES:
        raise WorkflowCreatorError(f"{label}.scope is unsupported: {scope}")
    if dependency_type in {"cli", "python_package"} and scope == "project":
        raise WorkflowCreatorError(f"{label} of type {dependency_type} cannot use project scope")

    result: dict[str, Any] = {
        "id": dependency_id,
        "type": dependency_type,
        "required": required,
        "scope": scope,
        "source": source,
        "purpose": purpose,
    }
    if value.get("install_command") is not None:
        result["install_command"] = _validate_text(
            value.get("install_command"),
            f"{label}.install_command",
        )
    if dependency_type == "cli":
        result["command"] = _validate_text(value.get("command"), f"{label}.command")
    if dependency_type == "python_package":
        result["module"] = _validate_text(value.get("module"), f"{label}.module")
    if dependency_type == "mcp" and value.get("server") is not None:
        result["server"] = _validate_text(value.get("server"), f"{label}.server")
    return result


def _validate_installed(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise WorkflowCreatorError("workflow spec field 'installed' must be a list")
    return [_validate_installed_item(item, f"installed[{index}]") for index, item in enumerate(value)]


def _validate_installed_item(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowCreatorError(f"{label} must be a JSON object")
    result = {
        "id": _validate_text(value.get("id"), f"{label}.id"),
        "type": _validate_text(value.get("type"), f"{label}.type"),
        "scope": _validate_text(value.get("scope"), f"{label}.scope"),
        "source": _validate_install_source(value.get("source"), f"{label}.source"),
        "recorded_at": _validate_text(
            value.get("recorded_at") or _iso_utc_now(),
            f"{label}.recorded_at",
        ),
        "recorded_by": _validate_text(
            value.get("recorded_by") or "workflow-creator",
            f"{label}.recorded_by",
        ),
    }
    return result


def _validate_prompt_sections(value: Any, *, fallback_prompt: str, label: str) -> dict[str, Any]:
    if value in (None, {}):
        return {
            "stage_goal": fallback_prompt,
            "context": [],
            "boundaries": list(_DEFAULT_PROMPT_BOUNDARIES),
            "blocked_conditions": list(_DEFAULT_PROMPT_BLOCKED_CONDITIONS),
        }
    if not isinstance(value, dict):
        raise WorkflowCreatorError(f"{label} must be a JSON object")
    if "tasks" in value:
        raise WorkflowCreatorError(
            f"{label}.tasks is no longer supported; put executable intent in 'prompt' and keep only context, boundaries, and blocked_conditions in prompt_sections"
        )
    return {
        "stage_goal": _validate_text(
            value.get("stage_goal") or fallback_prompt,
            f"{label}.stage_goal",
        ),
        "context": _validate_optional_string_list(value.get("context") or [], f"{label}.context"),
        "boundaries": _validate_optional_string_list(
            value.get("boundaries") or _DEFAULT_PROMPT_BOUNDARIES,
            f"{label}.boundaries",
        ),
        "blocked_conditions": _validate_optional_string_list(
            value.get("blocked_conditions") or _DEFAULT_PROMPT_BLOCKED_CONDITIONS,
            f"{label}.blocked_conditions",
        ),
    }


def _validate_optional_string_list(value: Any, label: str) -> list[str]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a string list")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WorkflowCreatorError(f"{label} must contain only non-empty strings")
        result.append(item.strip())
    return result


def _validate_skill_routing(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    routes: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        use_when = item.get("use_when") if isinstance(item.get("use_when"), dict) else {}
        operations = item.get("operations", use_when.get("operations", []))
        file_patterns = item.get("file_patterns", use_when.get("file_patterns", []))
        routes.append(
            {
                "skill": _validate_text(item.get("skill"), f"{item_label}.skill"),
                "operations": _validate_optional_string_list(
                    operations or [],
                    f"{item_label}.operations",
                ),
                "file_patterns": _validate_optional_string_list(
                    file_patterns or [],
                    f"{item_label}.file_patterns",
                ),
                "usage_notes": _validate_optional_string_list(
                    item.get("usage_notes") or [],
                    f"{item_label}.usage_notes",
                ),
            }
        )
    return routes


def _validate_state_updates(value: Any, label: str) -> list[dict[str, str]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    updates: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        state_key = _validate_step_id(str(item.get("state_key") or ""))
        output_key = _validate_text(item.get("output_key"), f"{item_label}.output_key")
        value_kind = str(item.get("kind") or "scalar").strip()
        if value_kind not in {"scalar", "string", "boolean", "list", "dict", "object"}:
            raise WorkflowCreatorError(f"{item_label}.kind is unsupported: {value_kind}")
        if state_key in seen:
            raise WorkflowCreatorError(f"duplicate state update key in {label}: {state_key}")
        seen.add(state_key)
        updates.append(
            {
                "state_key": state_key,
                "output_key": output_key,
                "kind": value_kind,
            }
        )
    return updates


def _validate_template_context_keys(value: Any, label: str) -> list[str]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a string list")
    return [_validate_step_id(str(item)) for item in value]


def _validate_repair_conditions(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    conditions: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        operator = _validate_text(item.get("operator"), f"{item_label}.operator")
        if operator not in _SUPPORTED_REPAIR_OPERATORS:
            raise WorkflowCreatorError(f"{item_label}.operator is unsupported: {operator}")
        conditions.append(
            {
                "output_key": _validate_text(item.get("output_key"), f"{item_label}.output_key"),
                "operator": operator,
                "value": item.get("value"),
                "reason": _validate_text(item.get("reason"), f"{item_label}.reason"),
                "next_node": str(item.get("next_node") or "repair_and_resume"),
                "branch_kind": str(item.get("branch_kind") or "retry"),
            }
        )
    return conditions


def _validate_transitions(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    transitions: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        operator = _validate_text(item.get("operator"), f"{item_label}.operator")
        if operator not in _SUPPORTED_REPAIR_OPERATORS:
            raise WorkflowCreatorError(f"{item_label}.operator is unsupported: {operator}")
        transitions.append(
            {
                "output_key": _validate_text(item.get("output_key"), f"{item_label}.output_key"),
                "operator": operator,
                "value": item.get("value"),
                "next_node": _validate_step_id(str(item.get("next_node") or "")),
                "branch_kind": _validate_text(
                    item.get("branch_kind") or "continue",
                    f"{item_label}.branch_kind",
                ),
                "reason": _validate_text(item.get("reason"), f"{item_label}.reason"),
            }
        )
    return transitions


def _validate_outcome_routes(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    routes: list[dict[str, Any]] = []
    seen_outcomes: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        outcome = _validate_text(item.get("outcome"), f"{item_label}.outcome")
        if outcome not in _SUPPORTED_OUTCOMES:
            raise WorkflowCreatorError(f"{item_label}.outcome is unsupported: {outcome}")
        if outcome in seen_outcomes:
            raise WorkflowCreatorError(f"duplicate outcome route in {label}: {outcome}")
        seen_outcomes.add(outcome)
        default_branch_kind = "repair" if outcome in {"blocked", "verifier_failed"} else "retry"
        routes.append(
            {
                "outcome": outcome,
                "next_node": _validate_step_id(str(item.get("next_node") or "")),
                "branch_kind": _validate_text(
                    item.get("branch_kind") or default_branch_kind,
                    f"{item_label}.branch_kind",
                ),
                "reason": _validate_text(item.get("reason"), f"{item_label}.reason"),
            }
        )
    return routes


def _validate_verifier_rules(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    rules: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        operator = _validate_text(item.get("operator"), f"{item_label}.operator")
        if operator not in _SUPPORTED_VERIFIER_OPERATORS:
            raise WorkflowCreatorError(f"{item_label}.operator is unsupported: {operator}")
        if operator == "one_of" and not isinstance(item.get("value"), list):
            raise WorkflowCreatorError(f"{item_label}.value must be a list for one_of")
        output_key = _validate_text(item.get("output_key"), f"{item_label}.output_key")
        rules.append(
            {
                "output_key": output_key,
                "operator": operator,
                "value": item.get("value"),
                "message": _validate_text(
                    item.get("message") or f"{output_key} failed verifier rule: {operator}",
                    f"{item_label}.message",
                ),
            }
        )
    return rules


def _validate_verifier_templates(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    templates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        template_id = _validate_step_id(str(item.get("id") or ""))
        if template_id in seen_ids:
            raise WorkflowCreatorError(f"duplicate verifier template id in {label}: {template_id}")
        seen_ids.add(template_id)
        template_name = _validate_text(item.get("template"), f"{item_label}.template")
        if template_name not in _SUPPORTED_VERIFIER_TEMPLATES:
            raise WorkflowCreatorError(f"{item_label}.template is unsupported: {template_name}")
        output_key = _validate_text(item.get("output_key"), f"{item_label}.output_key")
        result: dict[str, Any] = {
            "id": template_id,
            "template": template_name,
            "output_key": output_key,
            "message": _validate_text(
                item.get("message") or f"{template_id} verifier template failed",
                f"{item_label}.message",
            ),
        }
        if template_name == "conditional_required":
            when = item.get("when")
            if not isinstance(when, dict):
                raise WorkflowCreatorError(f"{item_label}.when must be a JSON object")
            operator = _validate_text(when.get("operator"), f"{item_label}.when.operator")
            if operator not in _SUPPORTED_VERIFIER_OPERATORS:
                raise WorkflowCreatorError(f"{item_label}.when.operator is unsupported: {operator}")
            result["when"] = {
                "output_key": _validate_text(
                    when.get("output_key"),
                    f"{item_label}.when.output_key",
                ),
                "operator": operator,
                "value": when.get("value"),
            }
            result["required_key"] = _validate_text(
                item.get("required_key"),
                f"{item_label}.required_key",
            )
        elif template_name == "conditional_equals":
            when = item.get("when")
            if not isinstance(when, dict):
                raise WorkflowCreatorError(f"{item_label}.when must be a JSON object")
            operator = _validate_text(when.get("operator"), f"{item_label}.when.operator")
            if operator not in _SUPPORTED_VERIFIER_OPERATORS:
                raise WorkflowCreatorError(f"{item_label}.when.operator is unsupported: {operator}")
            result["when"] = {
                "output_key": _validate_text(
                    when.get("output_key"),
                    f"{item_label}.when.output_key",
                ),
                "operator": operator,
                "value": when.get("value"),
            }
            if "expected_value" not in item:
                raise WorkflowCreatorError(f"{item_label}.expected_value must be present")
            result["expected_value"] = item.get("expected_value")
        elif template_name == "min_count":
            min_count = item.get("min_count")
            if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 0:
                raise WorkflowCreatorError(f"{item_label}.min_count must be a non-negative integer")
            result["min_count"] = min_count
        elif template_name == "required_set_members":
            result["required_members"] = _validate_optional_string_list(
                item.get("required_members") or [],
                f"{item_label}.required_members",
            )
            if not result["required_members"]:
                raise WorkflowCreatorError(f"{item_label}.required_members must not be empty")
            result["case_sensitive"] = bool(item.get("case_sensitive", False))
        elif template_name == "repo_path_policy":
            required_prefix = item.get("required_prefix")
            if required_prefix is not None:
                result["required_prefix"] = _validate_text(
                    required_prefix,
                    f"{item_label}.required_prefix",
                )
            result["forbidden_prefixes"] = _validate_optional_string_list(
                item.get("forbidden_prefixes") or [],
                f"{item_label}.forbidden_prefixes",
            )
            required_suffix = item.get("required_suffix")
            if required_suffix is not None:
                result["required_suffix"] = _validate_text(
                    required_suffix,
                    f"{item_label}.required_suffix",
                )
            if not (
                result.get("required_prefix")
                or result.get("forbidden_prefixes")
                or result.get("required_suffix")
            ):
                raise WorkflowCreatorError(
                    f"{item_label} must declare at least one repo path policy"
                )
        elif template_name == "artifact_file_contains_sections":
            result["sections"] = _validate_optional_string_list(
                item.get("sections") or [],
                f"{item_label}.sections",
            )
            if not result["sections"]:
                raise WorkflowCreatorError(f"{item_label}.sections must not be empty")
        templates.append(result)
    return templates


def _validate_custom_verifier_requirements(value: Any, label: str) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError(f"{label} must be a list")
    requirements: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        requirement_id = _validate_step_id(str(item.get("id") or ""))
        if requirement_id in seen_ids:
            raise WorkflowCreatorError(
                f"duplicate custom verifier requirement id in {label}: {requirement_id}"
            )
        seen_ids.add(requirement_id)
        result = {
            "id": requirement_id,
            "description": _validate_text(item.get("description"), f"{item_label}.description"),
            "signals": _validate_optional_string_list(
                item.get("signals") or [],
                f"{item_label}.signals",
            ),
        }
        implementation_surface = _validate_optional_string_list(
            item.get("implementation_surface") or [],
            f"{item_label}.implementation_surface",
        )
        if implementation_surface:
            result["implementation_surface"] = implementation_surface
        implementation_notes = item.get("implementation_notes")
        if implementation_notes is not None:
            result["implementation_notes"] = _validate_text(
                implementation_notes,
                f"{item_label}.implementation_notes",
            )
        hint_pseudocode = _validate_optional_string_list(
            item.get("hint_pseudocode") or [],
            f"{item_label}.hint_pseudocode",
        )
        if hint_pseudocode:
            result["hint_pseudocode"] = hint_pseudocode
        test_intent = _validate_optional_string_list(
            item.get("test_intent") or [],
            f"{item_label}.test_intent",
        )
        if test_intent:
            result["test_intent"] = test_intent
        implementation_version = item.get("implementation_version")
        if implementation_version is not None:
            result["implementation_version"] = _validate_implementation_version(
                implementation_version,
                f"{item_label}.implementation_version",
            )
        requirements.append(result)
    return requirements


def _validate_implementation_version(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise WorkflowCreatorError(f"{label} must be a positive integer")
    return value


def _validate_stage_transition_targets(stages: list[dict[str, Any]], final_step_id: str) -> None:
    valid_node_ids = {stage["step_id"] for stage in stages} | {final_step_id} | _REPAIR_STAGE_IDS
    if stages and not any(stage["stage_kind"] == "main" for stage in stages):
        raise WorkflowCreatorError("workflow spec must include at least one main stage")
    for stage in stages:
        if stage["stage_kind"] == "recovery":
            recovery_return_node = stage.get("recovery_return_node")
            if not recovery_return_node:
                raise WorkflowCreatorError(
                    f"{stage['step_id']} recovery stage requires recovery_return_node"
                )
            if recovery_return_node not in valid_node_ids:
                raise WorkflowCreatorError(
                    f"{stage['step_id']}.recovery_return_node is unknown: {recovery_return_node}"
                )
        elif stage.get("recovery_return_node") is not None:
            raise WorkflowCreatorError(
                f"{stage['step_id']}.recovery_return_node is only supported for recovery stages"
            )
        repair_signatures = {
            _condition_signature(condition) for condition in stage["repair_conditions"]
        }
        for condition in stage["repair_conditions"]:
            next_node = condition["next_node"]
            if next_node not in valid_node_ids:
                raise WorkflowCreatorError(
                    f"{stage['step_id']}.repair_conditions next_node is unknown: {next_node}"
                )
        for transition in stage["transitions"]:
            if _condition_signature(transition) in repair_signatures:
                raise WorkflowCreatorError(
                    f"{stage['step_id']} uses the same output condition for repair_conditions and transitions"
                )
            next_node = transition["next_node"]
            if next_node not in valid_node_ids:
                raise WorkflowCreatorError(
                    f"{stage['step_id']}.transitions next_node is unknown: {next_node}"
                )
        for route in stage["outcome_routes"]:
            next_node = route["next_node"]
            if next_node not in valid_node_ids:
                raise WorkflowCreatorError(
                    f"{stage['step_id']}.outcome_routes next_node is unknown: {next_node}"
                )


def _condition_signature(condition: dict[str, Any]) -> tuple[str, str, str]:
    value_json = json.dumps(
        condition.get("value"),
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return (
        str(condition.get("output_key") or ""),
        str(condition.get("operator") or ""),
        value_json,
    )


def _validate_regression_tests(
    value: Any,
    *,
    stages: list[dict[str, Any]],
    final_step_id: str,
) -> list[dict[str, Any]]:
    if value in (None, []):
        return []
    if not isinstance(value, list):
        raise WorkflowCreatorError("workflow spec field 'regression_tests' must be a list")
    stage_ids = {stage["step_id"] for stage in stages}
    valid_node_ids = stage_ids | {final_step_id} | _REPAIR_STAGE_IDS
    tests: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"regression_tests[{index}]"
        if not isinstance(item, dict):
            raise WorkflowCreatorError(f"{item_label} must be a JSON object")
        test_name = _validate_step_id(str(item.get("name") or ""))
        if test_name in seen_names:
            raise WorkflowCreatorError(f"duplicate regression test name: {test_name}")
        seen_names.add(test_name)
        test_type = _validate_text(item.get("type") or "transition", f"{item_label}.type")
        if test_type not in {"transition", "verifier"}:
            raise WorkflowCreatorError(f"{item_label}.type is unsupported: {test_type}")
        if test_type == "transition":
            current_step_id = _validate_step_id(str(item.get("current_step_id") or ""))
            expected_next_node = _validate_step_id(str(item.get("expected_next_node") or ""))
            if current_step_id not in valid_node_ids:
                raise WorkflowCreatorError(
                    f"{item_label}.current_step_id is unknown: {current_step_id}"
                )
            if expected_next_node not in valid_node_ids:
                raise WorkflowCreatorError(
                    f"{item_label}.expected_next_node is unknown: {expected_next_node}"
                )
            observation = item.get("observation") or {
                "status": "succeeded",
                "summary": "generated regression observation",
                "structured_output": {},
            }
            if not isinstance(observation, dict):
                raise WorkflowCreatorError(f"{item_label}.observation must be a JSON object")
            verifier_result = item.get("verifier_result")
            if verifier_result is not None and not isinstance(verifier_result, dict):
                raise WorkflowCreatorError(f"{item_label}.verifier_result must be a JSON object")
            state = item.get("state")
            if state is not None and not isinstance(state, dict):
                raise WorkflowCreatorError(f"{item_label}.state must be a JSON object")
            tests.append(
                {
                    "name": test_name,
                    "type": test_type,
                    "current_step_id": current_step_id,
                    "observation": observation,
                    "verifier_result": verifier_result,
                    "state": state,
                    "expected_next_node": expected_next_node,
                    "expected_branch_kind": _validate_text(
                        item.get("expected_branch_kind") or "continue",
                        f"{item_label}.expected_branch_kind",
                    ),
                }
            )
            continue

        step_id = _validate_step_id(str(item.get("step_id") or ""))
        if step_id not in stage_ids:
            raise WorkflowCreatorError(f"{item_label}.step_id is unknown: {step_id}")
        observation = item.get("observation")
        if not isinstance(observation, dict):
            raise WorkflowCreatorError(f"{item_label}.observation must be a JSON object")
        expected_passed = item.get("expected_passed")
        if not isinstance(expected_passed, bool):
            raise WorkflowCreatorError(f"{item_label}.expected_passed must be boolean")
        state = item.get("state")
        if state is not None and not isinstance(state, dict):
            raise WorkflowCreatorError(f"{item_label}.state must be a JSON object")
        tests.append(
            {
                "name": test_name,
                "type": test_type,
                "step_id": step_id,
                "observation": observation,
                "expected_passed": expected_passed,
                "state": state,
            }
        )
    return tests


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise WorkflowCreatorError(f"missing {label}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowCreatorError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkflowCreatorError(f"{label} must be a JSON object")
    return payload


def _find_binding_index(binding_payload: dict[str, Any], workflow_id: str) -> int | None:
    workflows = binding_payload.get("workflows")
    if not isinstance(workflows, list):
        raise WorkflowCreatorError("workflow binding config field 'workflows' must be a list")
    for index, item in enumerate(workflows):
        if not isinstance(item, dict):
            continue
        item_workflow_id = item.get("workflow_id")
        if isinstance(item_workflow_id, str) and item_workflow_id.strip() == workflow_id:
            return index
    return None


def _rewrite_scaffold_identifiers(workflow_dir: Path, workflow_id: str) -> None:
    class_prefix = _workflow_class_prefix(workflow_id)
    for path in workflow_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = text.replace("example_workflow", workflow_id)
        text = text.replace("ExampleWorkflow", class_prefix)
        text = text.replace("workflow_skeleton", workflow_id)
        path.write_text(text, encoding="utf-8")


def _workflow_class_prefix(workflow_id: str) -> str:
    return "".join(part.capitalize() for part in workflow_id.split("_") if part) + "Workflow"


def _render_business_workflow(
    workflow_dir: Path,
    workflow_spec: dict[str, Any],
    *,
    existing_verifiers_text: str | None = None,
) -> list[str]:
    prompts_dir = workflow_dir / "prompts"
    references_dir = workflow_dir / "references"
    shared_helpers = workflow_spec["shared_repair_helpers"]
    _remove_path(prompts_dir)
    prompts_dir.mkdir(parents=True)
    references_dir.mkdir(parents=True, exist_ok=True)

    for stage in workflow_spec["stages"]:
        (prompts_dir / f"{stage['step_id']}.md").write_text(
            _stage_prompt_text(stage),
            encoding="utf-8",
        )
    (prompts_dir / "request_unblocking_input.md").write_text(
        _stage_prompt_text(shared_helpers["request_unblocking_input"]),
        encoding="utf-8",
    )
    (prompts_dir / "repair_and_resume.md").write_text(
        _stage_prompt_text(shared_helpers["repair_and_resume"]),
        encoding="utf-8",
    )
    (prompts_dir / f"{workflow_spec['final_step_id']}.md").write_text(
        workflow_spec["final_prompt"].strip() + "\n",
        encoding="utf-8",
    )

    (workflow_dir / "contract.py").write_text(
        _render_contract_py(workflow_spec),
        encoding="utf-8",
    )
    (workflow_dir / "state.py").write_text(
        _render_state_py(workflow_spec),
        encoding="utf-8",
    )
    (workflow_dir / "policy.py").write_text(
        _render_policy_py(workflow_spec),
        encoding="utf-8",
    )
    (workflow_dir / "graphbuilder_runtime.py").write_text(
        _render_graphbuilder_runtime_py(workflow_spec),
        encoding="utf-8",
    )
    verifiers_text, warnings = _render_verifiers_py(
        workflow_spec,
        existing_verifiers_text=existing_verifiers_text,
    )
    (workflow_dir / "verifiers.py").write_text(verifiers_text, encoding="utf-8")
    (references_dir / "flowchart.md").write_text(
        _render_flowchart_md(workflow_spec),
        encoding="utf-8",
    )
    return warnings


def _write_agent_review_file(workflow_dir: Path, workflow_spec: dict[str, Any]) -> None:
    references_dir = workflow_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=True)
    (references_dir / "agent-review.md").write_text(
        _render_agent_review_md(workflow_spec),
        encoding="utf-8",
    )


def _write_spec_blueprint(workflow_dir: Path, workflow_spec: dict[str, Any]) -> None:
    _write_json_atomic(workflow_dir / "spec.json", workflow_spec)


def _write_generated_regression_tests(path: Path, workflow_spec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_regression_tests_py(workflow_spec), encoding="utf-8")


def _stage_prompt_text(stage: dict[str, Any]) -> str:
    sections = stage["prompt_sections"]
    action_line = stage["prompt"].strip()
    context_items = _stage_context_items(
        section_context=sections["context"],
    )
    lines = [action_line]
    if context_items:
        lines.extend(["", "Stage Context:", ""])
        lines.extend(f"- {item}" for item in context_items)
    if sections["boundaries"]:
        lines.extend(["", "Stage Boundaries:", ""])
        lines.extend(f"- {item}" for item in sections["boundaries"])
    if sections["blocked_conditions"]:
        lines.extend(["", "Blocked Conditions:", ""])
        lines.extend(f"- {item}" for item in sections["blocked_conditions"])
    return "\n".join(lines).rstrip() + "\n"


def _stage_context_items(
    *,
    section_context: list[str],
) -> list[str]:
    return list(section_context)


def _request_unblocking_prompt() -> str:
    return (
        "Request the exact external input needed to unblock the workflow.\n\n"
        "Current step: {{current_step_id}}\n"
        "Return stage: {{return_stage_id}}\n"
        "Repair category: {{repair_category}}\n"
        "Repair summary: {{repair_summary}}\n"
        "Required external inputs or approvals:\n{{repair_requirements}}\n"
        "Relevant evidence:\n{{repair_evidence}}\n\n"
        "Explain exactly what user input, approval, credential, file, or decision is needed.\n"
    )


def _repair_prompt() -> str:
    return (
        "Repair the previous workflow step and decide whether it can retry directly or must first request external help.\n\n"
        "Current step: {{current_step_id}}\n"
        "Return stage: {{return_stage_id}}\n"
        "Repair category: {{repair_category}}\n"
        "Repair summary: {{repair_summary}}\n"
        "Repair requirements:\n{{repair_requirements}}\n"
        "Relevant evidence:\n{{repair_evidence}}\n\n"
        "Return repair actions and the rationale for retrying the original stage.\n"
    )


def _render_contract_py(workflow_spec: dict[str, Any]) -> str:
    workflow_id = workflow_spec["workflow_id"]
    shared_helpers = workflow_spec["shared_repair_helpers"]
    has_skill_routes = any(stage["skill_routing"] for stage in workflow_spec["stages"]) or any(
        helper["skill_routing"] for helper in shared_helpers.values()
    )
    import_line = (
        "from workflows.common.contracts import (SkillRoute, SkillUseWhen, StepContract, StepVerifier, WorkflowInputContract)"
        if has_skill_routes
        else "from workflows.common.contracts import StepContract, StepVerifier, WorkflowInputContract"
    )
    lines = [
        import_line,
        "",
        "",
        f"WORKFLOW_ID = {workflow_id!r}",
        "",
        "WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(",
        f"    task_input_schema={_python_literal(workflow_spec['start_input_schema']['task_input'])},",
        f"    context_schema={_python_literal(workflow_spec['start_input_schema']['context'])},",
        f"    constraints_schema={_python_literal(workflow_spec['start_input_schema']['constraints'])},",
        ")",
        "",
    ]
    step_contract_ids: list[str] = []
    for stage in workflow_spec["stages"]:
        const_name = _constant_name(stage["step_id"])
        step_contract_ids.append(stage["step_id"])
        route_const_names: list[str] = []
        for index, route in enumerate(stage["skill_routing"], start=1):
            route_const_name = f"{const_name}_ROUTE_{index}"
            route_const_names.append(route_const_name)
            lines.extend(
                [
                    f"{route_const_name} = SkillRoute(",
                    f"    skill={route['skill']!r},",
                    "    use_when=SkillUseWhen(",
                    f"        operations={_python_literal(route['operations'])},",
                    f"        file_patterns={_python_literal(route['file_patterns'])},",
                    "    ),",
                    f"    usage_notes={_python_literal(route['usage_notes'])},",
                    ")",
                    "",
                ]
            )
        lines.extend(
            [
                f"{const_name} = StepContract(",
                f"    done_when={_python_literal(stage['done_when'])},",
                f"    output_schema={_python_literal(stage['output_schema'])},",
                f"    failure_schema={_python_literal(stage['failure_schema'])},",
                *(
                    [f"    skill_routing=[{', '.join(route_const_names)}],"]
                    if route_const_names
                    else []
                ),
                "    verifier=StepVerifier(",
                '        kind="python_callable",',
                f'        ref="workflows.{workflow_id}.verifiers:verify_{stage["step_id"]}",',
                "        timeout_seconds=15,",
                '        run_on_status=["succeeded"],',
                "    ),",
                ")",
                "",
            ]
        )
    for helper_id, const_name in (
        ("request_unblocking_input", "REQUEST_UNBLOCKING_INPUT"),
        ("repair_and_resume", "REPAIR_AND_RESUME"),
    ):
        helper = shared_helpers[helper_id]
        for index, route in enumerate(helper["skill_routing"], start=1):
            route_const_name = f"{const_name}_ROUTE_{index}"
            lines.extend(
                [
                    f"{route_const_name} = SkillRoute(",
                    f"    skill={route['skill']!r},",
                    "    use_when=SkillUseWhen(",
                    f"        operations={_python_literal(route['operations'])},",
                    f"        file_patterns={_python_literal(route['file_patterns'])},",
                    "    ),",
                    f"    usage_notes={_python_literal(route['usage_notes'])},",
                    ")",
                    "",
                ]
            )
    lines.extend(
        [
            "REQUEST_UNBLOCKING_INPUT = StepContract(",
            f"    done_when={_python_literal(shared_helpers['request_unblocking_input']['done_when'])},",
            f"    output_schema={_python_literal(shared_helpers['request_unblocking_input']['output_schema'])},",
            f"    failure_schema={_python_literal(shared_helpers['request_unblocking_input']['failure_schema'])},",
            *(
                [
                    "    skill_routing=["
                    + ", ".join(
                        f"REQUEST_UNBLOCKING_INPUT_ROUTE_{index}"
                        for index, _ in enumerate(
                            shared_helpers["request_unblocking_input"]["skill_routing"],
                            start=1,
                        )
                    )
                    + "],"
                ]
                if shared_helpers["request_unblocking_input"]["skill_routing"]
                else []
            ),
            ")",
            "",
            "REPAIR_AND_RESUME = StepContract(",
            f"    done_when={_python_literal(shared_helpers['repair_and_resume']['done_when'])},",
            f"    output_schema={_python_literal(shared_helpers['repair_and_resume']['output_schema'])},",
            f"    failure_schema={_python_literal(shared_helpers['repair_and_resume']['failure_schema'])},",
            *(
                [
                    "    skill_routing=["
                    + ", ".join(
                        f"REPAIR_AND_RESUME_ROUTE_{index}"
                        for index, _ in enumerate(
                            shared_helpers["repair_and_resume"]["skill_routing"],
                            start=1,
                        )
                    )
                    + "],"
                ]
                if shared_helpers["repair_and_resume"]["skill_routing"]
                else []
            ),
            ")",
            "",
            "STEP_CONTRACTS = {",
        ]
    )
    for stage in workflow_spec["stages"]:
        lines.append(f'    "{stage["step_id"]}": {_constant_name(stage["step_id"])},')
    lines.extend(
        [
            '    "request_unblocking_input": REQUEST_UNBLOCKING_INPUT,',
            '    "repair_and_resume": REPAIR_AND_RESUME,',
            "}",
            "",
            "",
            "def get_step_contract(step_id: str) -> StepContract:",
            "    try:",
            "        return STEP_CONTRACTS[step_id]",
            "    except KeyError as exc:  # pragma: no cover - generated guard",
            '        raise LookupError(f"unknown step contract: {step_id}") from exc',
            "",
            "",
            "def list_step_contract_ids() -> list[str]:",
            "    return list(STEP_CONTRACTS.keys())",
            "",
        ]
    )
    return "\n".join(lines)


def _collect_state_updates(workflow_spec: dict[str, Any]) -> list[dict[str, str]]:
    updates: list[dict[str, str]] = []
    seen: set[str] = set()
    for stage in workflow_spec["stages"]:
        for update in stage["state_updates"]:
            state_key = update["state_key"]
            if state_key in seen:
                continue
            seen.add(state_key)
            updates.append(update)
    return updates


def _state_field_line(update: dict[str, str]) -> str:
    state_key = update["state_key"]
    kind = update["kind"]
    if kind == "list":
        return f"    {state_key}: list = field(default_factory=list)"
    if kind in {"dict", "object"}:
        return f"    {state_key}: dict = field(default_factory=dict)"
    if kind == "boolean":
        return f"    {state_key}: bool | None = None"
    if kind == "string":
        return f"    {state_key}: str | None = None"
    return f"    {state_key}: object | None = None"


def _state_deserialize_line(update: dict[str, str]) -> str:
    state_key = update["state_key"]
    kind = update["kind"]
    if kind == "list":
        return f"        {state_key}=list(payload.get({state_key!r}) or []),"
    if kind in {"dict", "object"}:
        return f"        {state_key}=dict(payload.get({state_key!r}) or {{}}),"
    return f"        {state_key}=payload.get({state_key!r}),"


def _state_record_update_lines(workflow_spec: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for stage in workflow_spec["stages"]:
        if not stage["state_updates"]:
            continue
        branch = "if" if not lines else "elif"
        lines.append(f"            {branch} current_step_id == {stage['step_id']!r}:")
        for update in stage["state_updates"]:
            state_key = update["state_key"]
            output_key = update["output_key"]
            kind = update["kind"]
            if kind == "list":
                expression = f"_list_value(structured_output.get({output_key!r}))"
            elif kind in {"dict", "object"}:
                expression = f"_dict_value(structured_output.get({output_key!r}))"
            else:
                expression = f"structured_output.get({output_key!r})"
            lines.append(f"                state.{state_key} = {expression}")
    if lines:
        lines.append("            else:")
        lines.append("                pass")
    return lines


def _state_repair_condition_lines(workflow_spec: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for stage in workflow_spec["stages"]:
        if not stage["repair_conditions"]:
            continue
        branch = "if" if not lines else "elif"
        lines.append(f"        {branch} current_step_id == {stage['step_id']!r}:")
        for condition in stage["repair_conditions"]:
            lines.append(
                "            if condition_matches("
                f"structured_output.get({condition['output_key']!r}), "
                f"{condition['operator']!r}, "
                f"{_python_literal(condition['value'])}"
                "):"
            )
            lines.append(f"                return {condition['reason']!r}")
    if lines:
        lines.append("        else:")
        lines.append("            pass")
    return lines


def _render_state_py(workflow_spec: dict[str, Any]) -> str:
    class_name = _workflow_class_prefix(workflow_spec["workflow_id"]) + "State"
    main_stage_ids = tuple(stage["step_id"] for stage in workflow_spec["stages"])
    state_updates = _collect_state_updates(workflow_spec)
    state_field_lines = [_state_field_line(update) for update in state_updates]
    deserialize_lines = [_state_deserialize_line(update) for update in state_updates]
    record_update_lines = _state_record_update_lines(workflow_spec)
    repair_condition_lines = _state_repair_condition_lines(workflow_spec)
    return f'''from __future__ import annotations

from dataclasses import asdict, dataclass, field

from workflows.common.policies import condition_matches, max_steps_exceeded_decision
from workflows.common.repair_payloads import build_default_agent_repair_payload, make_agent_repair_payload


MAIN_STAGE_IDS = {_python_literal(main_stage_ids)}
REPAIR_STAGE_IDS = (
    "request_unblocking_input",
    "repair_and_resume",
)


@dataclass
class {class_name}:
    attempt_counts: dict[str, int] = field(default_factory=dict)
    workflow_goal: str | None = None
    task_input: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    current_stage_id: str = MAIN_STAGE_IDS[0]
    completed_stages: list[str] = field(default_factory=list)
    return_stage_id: str | None = None
{chr(10).join(state_field_lines)}
    artifacts_by_stage: dict[str, list[dict]] = field(default_factory=dict)
    repair_context: dict[str, object] = field(default_factory=dict)


def make_initial_state(request: dict) -> {class_name}:
    task_input = dict(request.get("task_input") or {{}})
    return {class_name}(
        workflow_goal=_select_workflow_goal(task_input),
        task_input=task_input,
        context=dict(request.get("context") or {{}}),
        constraints=dict(request.get("constraints") or {{}}),
    )


def _select_workflow_goal(task_input: dict) -> str | None:
    for key in ("goal", "objective", "task", "research_goal", "user_prompt"):
        value = task_input.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def serialize_state(state: {class_name}) -> dict:
    return asdict(state)


def deserialize_state(payload: dict | None) -> {class_name}:
    payload = payload or {{}}
    return {class_name}(
        attempt_counts=dict(payload.get("attempt_counts") or {{}}),
        workflow_goal=payload.get("workflow_goal"),
        task_input=dict(payload.get("task_input") or {{}}),
        context=dict(payload.get("context") or {{}}),
        constraints=dict(payload.get("constraints") or {{}}),
        current_stage_id=payload.get("current_stage_id") or MAIN_STAGE_IDS[0],
        completed_stages=list(payload.get("completed_stages") or []),
        return_stage_id=payload.get("return_stage_id"),
{chr(10).join(deserialize_lines)}
        artifacts_by_stage=dict(payload.get("artifacts_by_stage") or {{}}),
        repair_context=dict(payload.get("repair_context") or {{}}),
    )


def record_observation(
    state: {class_name},
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> None:
    state.attempt_counts[current_step_id] = state.attempt_counts.get(current_step_id, 0) + 1
    structured_output = observation.get("structured_output") or {{}}
    if isinstance(structured_output, dict):
        state.artifacts_by_stage.setdefault(current_step_id, []).append(structured_output)
        if observation.get("status") == "succeeded":
{chr(10).join(record_update_lines) if record_update_lines else "            pass"}

    max_steps_decision = max_steps_exceeded_decision(
        current_step_id=current_step_id,
        state=serialize_state(state),
    )
    if max_steps_decision is not None:
        return_stage_id = determine_return_stage_id(
            current_step_id=current_step_id,
            existing_return_stage_id=state.return_stage_id,
        )
        state.return_stage_id = return_stage_id
        state.repair_context = _build_repair_context(
            current_step_id=current_step_id,
            return_stage_id=return_stage_id,
            transition_reason="max_steps_exceeded",
            repair_payload=make_agent_repair_payload(
                category="blocked",
                summary=max_steps_decision.reason,
                requirements=[],
                evidence=[],
            ),
        )
        return

    transition_reason = determine_transition_reason(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    if transition_reason is None:
        return
    return_stage_id = determine_return_stage_id(
        current_step_id=current_step_id,
        existing_return_stage_id=state.return_stage_id,
    )
    repair_payload = build_default_agent_repair_payload(
        current_step_id=current_step_id,
        observation=observation,
        verifier_result=verifier_result,
    )
    state.return_stage_id = return_stage_id
    state.repair_context = _build_repair_context(
        current_step_id=current_step_id,
        return_stage_id=return_stage_id,
        transition_reason=transition_reason,
        repair_payload=repair_payload or {{}},
    )


def determine_return_stage_id(
    *,
    current_step_id: str,
    existing_return_stage_id: str | None,
) -> str | None:
    if current_step_id in REPAIR_STAGE_IDS:
        return existing_return_stage_id
    return current_step_id


def determine_transition_reason(
    *,
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> str | None:
    status = observation.get("status")
    if status == "blocked":
        return "blocked"
    if status == "partial":
        return "partial"
    if status == "failed":
        return "failed"
    if verifier_result is not None and not verifier_result.get("passed", False):
        return "verifier_failed"
    structured_output = observation.get("structured_output") or {{}}
    if isinstance(structured_output, dict):
{chr(10).join(repair_condition_lines) if repair_condition_lines else "        pass"}
    return None


def apply_transition(state: {class_name}, *, current_step_id: str, next_step_id: str) -> None:
    if _is_forward_completion_transition(current_step_id, next_step_id):
        if current_step_id not in state.completed_stages:
            state.completed_stages.append(current_step_id)

    if current_step_id in REPAIR_STAGE_IDS and next_step_id == state.return_stage_id:
        state.return_stage_id = None
        state.repair_context = {{}}

    state.current_stage_id = next_step_id


def _is_forward_completion_transition(current_step_id: str, next_step_id: str) -> bool:
    if current_step_id not in MAIN_STAGE_IDS:
        return False
    if next_step_id == current_step_id or next_step_id in REPAIR_STAGE_IDS:
        return False
    if next_step_id == "finalize_delivery_summary":
        return True
    if next_step_id not in MAIN_STAGE_IDS:
        return False
    return MAIN_STAGE_IDS.index(next_step_id) > MAIN_STAGE_IDS.index(current_step_id)


def _build_repair_context(
    *,
    current_step_id: str,
    return_stage_id: str | None,
    transition_reason: str,
    repair_payload: dict[str, object],
) -> dict[str, object]:
    return {{
        "source_stage_id": current_step_id,
        "return_stage_id": return_stage_id or "",
        "transition_reason": transition_reason,
        "repair_payload": dict(repair_payload or {{}}),
    }}


def _list_value(value) -> list:
    return list(value) if isinstance(value, list) else []


def _dict_value(value) -> dict:
    return dict(value) if isinstance(value, dict) else {{}}


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            items.append(text)
    return items
'''


def _policy_repair_condition_lines(stage: dict[str, Any]) -> list[str]:
    lines = [
        "        structured_output = observation.get(\"structured_output\") or {}",
        "        if isinstance(structured_output, dict):",
    ]
    for condition in stage["repair_conditions"]:
        lines.extend(
            [
                "            if condition_matches("
                f"structured_output.get({condition['output_key']!r}), "
                f"{condition['operator']!r}, "
                f"{_python_literal(condition['value'])}"
                "):",
                "                return TransitionDecision(",
                f"                    next_node={condition['next_node']!r},",
                f"                    branch_kind={condition['branch_kind']!r},",
                f"                    reason={condition['reason']!r},",
                "                )",
            ]
        )
    return lines


def _policy_transition_lines(stage: dict[str, Any]) -> list[str]:
    lines = [
        "        structured_output = observation.get(\"structured_output\") or {}",
        "        if isinstance(structured_output, dict):",
    ]
    for transition in stage["transitions"]:
        lines.extend(
            [
                "            if condition_matches("
                f"structured_output.get({transition['output_key']!r}), "
                f"{transition['operator']!r}, "
                f"{_python_literal(transition['value'])}"
                "):",
                "                return TransitionDecision(",
                f"                    next_node={transition['next_node']!r},",
                f"                    branch_kind={transition['branch_kind']!r},",
                f"                    reason={transition['reason']!r},",
                "                )",
            ]
        )
    return lines


def _policy_outcome_route_lines(stage: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for route in stage["outcome_routes"]:
        if route["outcome"] == "verifier_failed":
            condition_line = (
                '        if observation["status"] == "succeeded" and verifier_result is not None '
                'and not verifier_result["passed"]:'
            )
        else:
            condition_line = f'        if observation["status"] == "{route["outcome"]}":'
        lines.extend(
            [
                condition_line,
                "            return TransitionDecision(",
                f"                next_node={route['next_node']!r},",
                f"                branch_kind={route['branch_kind']!r},",
                f"                reason={route['reason']!r},",
                "            )",
            ]
        )
    return lines


def _graph_template_context_update_lines(workflow_spec: dict[str, Any]) -> list[str]:
    start_input_schema = workflow_spec.get("start_input_schema") or {}
    lines: list[str] = [
        '        "artifacts_by_stage_json": json.dumps(state.artifacts_by_stage, ensure_ascii=False, indent=2),'
    ]
    seen_keys = {"artifacts_by_stage_json"}
    for update in _collect_state_updates(workflow_spec):
        state_key = update["state_key"]
        if state_key in seen_keys:
            continue
        lines.append(f'        "{state_key}": _format_prompt_value(state.{state_key}),')
        seen_keys.add(state_key)
    input_sources = (
        ("task_input", "task_input_values"),
        ("context", "context_values"),
        ("constraints", "constraint_values"),
    )
    for schema_key, source_name in input_sources:
        schema = start_input_schema.get(schema_key) or {}
        for input_key in schema:
            if input_key in seen_keys:
                continue
            lines.append(
                f'        "{input_key}": _format_prompt_value({source_name}.get("{input_key}")),'
            )
            seen_keys.add(input_key)
    return lines


def _render_policy_py(workflow_spec: dict[str, Any]) -> str:
    stages = workflow_spec["stages"]
    main_stages = [stage for stage in stages if stage["stage_kind"] == "main"]
    final_step_id = workflow_spec["final_step_id"]
    first_main_stage_id = main_stages[0]["step_id"] if main_stages else final_step_id
    lines = [
        "from __future__ import annotations",
        "",
        "from workflows.common.policies import TransitionDecision, condition_matches, max_steps_exceeded_decision",
        "",
        "",
        "def choose_next_node(",
        "    *,",
        "    current_step_id: str,",
        "    state: dict,",
        "    observation: dict,",
        "    verifier_result: dict | None,",
        ") -> TransitionDecision:",
        "    max_steps_decision = max_steps_exceeded_decision(",
        "        current_step_id=current_step_id,",
        "        state=state,",
        "    )",
        "    if max_steps_decision is not None:",
        "        return max_steps_decision",
        "",
    ]
    for stage in stages:
        if stage["stage_kind"] == "main":
            main_index = main_stages.index(stage)
            next_node = (
                final_step_id
                if main_index == len(main_stages) - 1
                else main_stages[main_index + 1]["step_id"]
            )
            branch_kind = "complete" if next_node == final_step_id else "continue"
            reason = (
                f"{stage['step_id']} completed successfully"
                if branch_kind == "complete"
                else f"{stage['step_id']} completed; continue to {next_node}"
            )
            lines.extend(
                [
                    f'    if current_step_id == "{stage["step_id"]}":',
                    *(_policy_outcome_route_lines(stage) if stage["outcome_routes"] else []),
                    "        status_decision = _route_common_failure(",
                    "            current_step_id=current_step_id,",
                    "            observation=observation,",
                    "            verifier_result=verifier_result,",
                    "        )",
                    "        if status_decision is not None:",
                    "            return status_decision",
                    *(_policy_repair_condition_lines(stage) if stage["repair_conditions"] else []),
                    *(_policy_transition_lines(stage) if stage["transitions"] else []),
                    "        return TransitionDecision(",
                    f'            next_node="{next_node}",',
                    f'            branch_kind="{branch_kind}",',
                    f'            reason="{reason}",',
                    "        )",
                    "",
                ]
            )
            continue

        recovery_return_node = stage["recovery_return_node"] or first_main_stage_id
        lines.extend(
            [
                f'    if current_step_id == "{stage["step_id"]}":',
                *(_policy_outcome_route_lines(stage) if stage["outcome_routes"] else []),
                '        if observation["status"] == "blocked":',
                "            return TransitionDecision(",
                '                next_node="repair_and_resume",',
                '                branch_kind="repair",',
                f'                reason="{stage["step_id"]} is blocked and should be triaged by shared repair first",',
                "            )",
                '        if verifier_result is not None and not verifier_result["passed"]:',
                "            return TransitionDecision(",
                f'                next_node="{stage["step_id"]}",',
                '                branch_kind="retry",',
                f'                reason="{stage["step_id"]} repair output did not satisfy verifier checks",',
                "            )",
                '        if observation["status"] in {"partial", "failed"}:',
                "            return TransitionDecision(",
                f'                next_node="{stage["step_id"]}",',
                '                branch_kind="retry",',
                f'                reason="{stage["step_id"]} recovery stage still needs more iteration",',
                "            )",
                '        if observation["status"] == "succeeded":',
                "            return TransitionDecision(",
                f'                next_node="{recovery_return_node}",',
                '                branch_kind="continue",',
                f'                reason="{stage["step_id"]} completed recovery work; return to {recovery_return_node}",',
                "            )",
                "        return TransitionDecision(",
                f'            next_node="{stage["step_id"]}",',
                '            branch_kind="retry",',
                f'            reason="{stage["step_id"]} recovery stage returned an unresolved status",',
                "        )",
                "",
            ]
        )
    lines.extend(
        [
            '    if current_step_id == "request_unblocking_input":',
            '        if observation["status"] == "succeeded":',
            '            return_stage_id = state.get("return_stage_id")',
            '            repair_context = state.get("repair_context") or {}',
            '            source_stage_id = repair_context.get("source_stage_id")',
            '            resume_target = "repair_and_resume" if source_stage_id == "repair_and_resume" else return_stage_id',
            '            if not resume_target:',
            "                return TransitionDecision(",
            '                    next_node="request_unblocking_input",',
            '                    branch_kind="repair",',
            '                    reason="cannot resume because the next recovery target is missing",',
            "                )",
            "            return TransitionDecision(",
            '                next_node=resume_target,',
            '                branch_kind="continue",',
            '                reason="user supplied the missing input and the workflow can return to the recovery owner",',
            "            )",
            "        return TransitionDecision(",
            '            next_node="request_unblocking_input",',
            '            branch_kind="repair",',
            '            reason="blocking details are still unresolved",',
            "        )",
            "",
            '    if current_step_id == "repair_and_resume":',
            '        if observation["status"] == "blocked":',
            '            repair_attempts = int((state.get("attempt_counts") or {}).get("repair_and_resume") or 0)',
            f'            if repair_attempts < {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK}:',
            "                return TransitionDecision(",
            '                    next_node="repair_and_resume",',
            '                    branch_kind="retry",',
            f'                    reason="repair must attempt self-repair at least {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} times before requesting external help",',
            "                )",
            "            return TransitionDecision(",
            '                next_node="request_unblocking_input",',
            '                branch_kind="repair",',
            f'                reason="repair exhausted {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} self-repair attempts and now requires external help before retry",',
            "            )",
            '        if observation["status"] == "succeeded":',
            '            return_stage_id = state.get("return_stage_id")',
            '            if not return_stage_id:',
            "                return TransitionDecision(",
            '                    next_node="repair_and_resume",',
            '                    branch_kind="retry",',
            '                    reason="cannot resume because return_stage_id is missing",',
            "                )",
            "            return TransitionDecision(",
            '                next_node=return_stage_id,',
            '                branch_kind="continue",',
            '                reason="repair work is complete and the original stage can resume",',
            "            )",
            "        return TransitionDecision(",
            '            next_node="repair_and_resume",',
            '            branch_kind="retry",',
            '            reason="repair stage still needs more iteration",',
            "        )",
            "",
            '    raise LookupError(f"no transition policy for step: {current_step_id}")',
            "",
            "",
            "def _route_common_failure(",
            "    *,",
            "    current_step_id: str,",
            "    observation: dict,",
            "    verifier_result: dict | None,",
            ") -> TransitionDecision | None:",
            '    if observation["status"] == "blocked":',
            "        return TransitionDecision(",
            '            next_node="repair_and_resume",',
            '            branch_kind="repair",',
            '            reason=f"{current_step_id} is blocked and should be triaged by shared repair first",',
            "        )",
            '    if observation["status"] == "partial":',
            "        return TransitionDecision(",
            '            next_node="repair_and_resume",',
            '            branch_kind="retry",',
            '            reason=f"{current_step_id} only partially completed",',
            "        )",
            '    if observation["status"] == "failed":',
            "        return TransitionDecision(",
            '            next_node="repair_and_resume",',
            '            branch_kind="retry",',
            '            reason=f"{current_step_id} failed and should be retried",',
            "        )",
            '    if verifier_result is not None and not verifier_result["passed"]:',
            "        return TransitionDecision(",
            '            next_node="repair_and_resume",',
            '            branch_kind="retry",',
            '            reason=f"{current_step_id} did not satisfy verifier checks",',
            "        )",
            "    return None",
            "",
        ]
    )
    return "\n".join(lines)


def _render_graphbuilder_runtime_py(workflow_spec: dict[str, Any]) -> str:
    workflow_id = workflow_spec["workflow_id"]
    class_name = _workflow_class_prefix(workflow_id) + "State"
    main_stages = [stage for stage in workflow_spec["stages"] if stage["stage_kind"] == "main"]
    first_stage = main_stages[0]["step_id"]
    shared_helpers = workflow_spec["shared_repair_helpers"]
    template_context_update_lines = _graph_template_context_update_lines(workflow_spec)
    node_lines: list[str] = []
    for stage in workflow_spec["stages"]:
        node_lines.extend(
            [
                f'    "{stage["step_id"]}": NodeDefinition(',
                f'        step_id="{stage["step_id"]}",',
                f'        prompt_asset_path=PROMPTS_DIR / "{stage["step_id"]}.md",',
                f'        intent="{stage["intent"]}",',
                f'        expected_artifact="{stage["expected_artifact"]}",',
                '        resume_instructions="Return an Observation preserving run_id and step_id.",',
                "    ),",
            ]
        )
    node_lines.extend(
        [
            '    "request_unblocking_input": NodeDefinition(',
            '        step_id="request_unblocking_input",',
            '        prompt_asset_path=PROMPTS_DIR / "request_unblocking_input.md",',
            '        intent="request_unblocking_input",',
            f'        expected_artifact={shared_helpers["request_unblocking_input"]["expected_artifact"]!r},',
            '        resume_instructions="Return an Observation preserving run_id and step_id.",',
            "    ),",
            '    "repair_and_resume": NodeDefinition(',
            '        step_id="repair_and_resume",',
            '        prompt_asset_path=PROMPTS_DIR / "repair_and_resume.md",',
            '        intent="repair_and_resume",',
            f'        expected_artifact={shared_helpers["repair_and_resume"]["expected_artifact"]!r},',
            '        resume_instructions="Return an Observation preserving run_id and step_id.",',
            "    ),",
            f'    "{workflow_spec["final_step_id"]}": NodeDefinition(',
            f'        step_id="{workflow_spec["final_step_id"]}",',
            f'        prompt_asset_path=PROMPTS_DIR / "{workflow_spec["final_step_id"]}.md",',
            '        intent="finalize_summary",',
            '        expected_artifact="final user-facing summary",',
            '        resume_instructions="No further resume.",',
            "        final=True,",
            '        done_when=("Output the final workflow summary",),',
            "    ),",
        ]
    )
    return f'''from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_graph.graph_builder import Graph, GraphBuilder

from runtime.models import HistoryEntry, YieldResponse
from workflows.common.policies import TransitionDecision
from workflows.common.prompting import build_prompt_envelope, resolve_prompt_asset

from . import contract as workflow_contract
from . import policy, state as workflow_state

WORKFLOW_VERSION = "v1"
PROMPTS_DIR = Path(__file__).with_name("prompts")


@dataclass(frozen=True)
class NodeDefinition:
    step_id: str
    prompt_asset_path: Path
    intent: str
    expected_artifact: str
    resume_instructions: str
    final: bool = False
    done_when: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GraphBuilderPreviewInputs:
    current_step_id: str
    observation: dict
    verifier_result: dict | None = None


@dataclass(frozen=True)
class GraphBuilderStartInputs:
    run_id: str
    workflow_id: str
    workflow_version: str


@dataclass(frozen=True)
class GraphBuilderPreviewResult:
    step_id: str
    branch_kind: str
    reason: str
    trace_payload: dict
    history_entry: HistoryEntry
    state_payload: dict


@dataclass(frozen=True)
class GraphBuilderTransition:
    current_step_id: str
    decision: TransitionDecision
    state_payload: dict

    def to_trace_payload(self) -> dict:
        return self.decision.to_trace_payload()


NODE_DEFINITIONS = {{
{chr(10).join(node_lines)}
}}


BUILDER = GraphBuilder(
    name="{workflow_id}_graphbuilder_runtime",
    state_type=workflow_state.{class_name},
    input_type=GraphBuilderPreviewInputs,
    output_type=GraphBuilderPreviewResult,
    auto_instrument=False,
)


@BUILDER.step(node_id="evaluate_transition")
async def evaluate_transition(ctx) -> GraphBuilderTransition:
    workflow_state.record_observation(
        ctx.state,
        current_step_id=ctx.inputs.current_step_id,
        observation=ctx.inputs.observation,
        verifier_result=ctx.inputs.verifier_result,
    )
    decision = policy.choose_next_node(
        current_step_id=ctx.inputs.current_step_id,
        state=workflow_state.serialize_state(ctx.state),
        observation=ctx.inputs.observation,
        verifier_result=ctx.inputs.verifier_result,
    )
    workflow_state.apply_transition(
        ctx.state,
        current_step_id=ctx.inputs.current_step_id,
        next_step_id=decision.next_node,
    )
    return GraphBuilderTransition(
        current_step_id=ctx.inputs.current_step_id,
        decision=decision,
        state_payload=workflow_state.serialize_state(ctx.state),
    )


@BUILDER.step(node_id="emit_preview_result")
async def emit_preview_result(ctx) -> GraphBuilderPreviewResult:
    trace_payload = ctx.inputs.to_trace_payload()
    return GraphBuilderPreviewResult(
        step_id=ctx.inputs.decision.next_node,
        branch_kind=ctx.inputs.decision.branch_kind,
        reason=ctx.inputs.decision.reason,
        trace_payload=trace_payload,
        history_entry=HistoryEntry.branch_selected(
            node=ctx.inputs.current_step_id,
            step_id=ctx.inputs.current_step_id,
            payload=trace_payload,
        ),
        state_payload=ctx.inputs.state_payload,
    )


BUILDER.add_edge(BUILDER.start_node, evaluate_transition)
BUILDER.add_edge(evaluate_transition, emit_preview_result)
BUILDER.add_edge(emit_preview_result, BUILDER.end_node)


WORKFLOW_GRAPH = BUILDER.build()


START_BUILDER = GraphBuilder(
    name="{workflow_id}_graphbuilder_runtime_start",
    state_type=workflow_state.{class_name},
    input_type=GraphBuilderStartInputs,
    output_type=YieldResponse,
    auto_instrument=False,
)


@START_BUILDER.step(node_id="emit_{first_stage}")
async def emit_{first_stage}(ctx) -> YieldResponse:
    node_definition = get_node_definition("{first_stage}")
    contract = workflow_contract.get_step_contract("{first_stage}")
    prompt_envelope = build_prompt_envelope(
        run_id=ctx.inputs.run_id,
        step_id=node_definition.step_id,
        prompt_asset_path=node_definition.prompt_asset_path,
        intent=node_definition.intent,
        expected_artifact=node_definition.expected_artifact,
        done_when=contract.done_when,
        output_schema=contract.output_schema,
        failure_schema=contract.failure_schema,
        resume_instructions=node_definition.resume_instructions,
        skill_routing=contract.skill_routing,
        metadata={{
            "workflow_id": ctx.inputs.workflow_id,
            "workflow_version": ctx.inputs.workflow_version,
        }},
        template_context=_template_context_from_state(ctx.state),
    )
    return YieldResponse(
        run_id=ctx.inputs.run_id,
        step_id=node_definition.step_id,
        prompt_envelope=prompt_envelope,
    )


START_BUILDER.add_edge(START_BUILDER.start_node, emit_{first_stage})
START_BUILDER.add_edge(emit_{first_stage}, START_BUILDER.end_node)


START_GRAPH = START_BUILDER.build()


def build_graph() -> Graph:
    return WORKFLOW_GRAPH


def build_start_graph() -> Graph:
    return START_GRAPH


def get_node_definition(node_key: str) -> NodeDefinition:
    try:
        return NODE_DEFINITIONS[node_key]
    except KeyError as exc:  # pragma: no cover - generated guard
        raise LookupError(f"unknown node definition: {{node_key}}") from exc


def load_prompt_body(node_key: str, template_context: dict | None = None) -> str:
    return resolve_prompt_asset(
        get_node_definition(node_key).prompt_asset_path,
        template_context=template_context,
    )


def build_template_context(*, step_id: str, run_state) -> dict:
    state = workflow_state.deserialize_state(
        run_state.graph_state if isinstance(run_state.graph_state, dict) else {{}}
    )
    repair_context = state.repair_context if isinstance(state.repair_context, dict) else {{}}
    repair_payload = repair_context.get("repair_payload")
    if not isinstance(repair_payload, dict):
        repair_payload = {{}}
    context = _template_context_from_state(state)
    context.update(
        {{
            "current_step_id": step_id,
            "return_stage_id": state.return_stage_id or "",
            "source_stage_id": str(repair_context.get("source_stage_id") or ""),
            "repair_category": str(repair_payload.get("category") or ""),
            "repair_summary": str(repair_payload.get("summary") or ""),
            "repair_requirements": _format_prompt_list(repair_payload.get("requirements")),
            "repair_evidence": _format_prompt_list(repair_payload.get("evidence")),
        }}
    )
    return context


def _template_context_from_state(state: workflow_state.{class_name}) -> dict:
    task_input_values = state.task_input if isinstance(state.task_input, dict) else {{}}
    context_values = state.context if isinstance(state.context, dict) else {{}}
    constraint_values = state.constraints if isinstance(state.constraints, dict) else {{}}
    context = {{
        "workflow_goal": state.workflow_goal or "",
        "task_input_json": json.dumps(state.task_input, ensure_ascii=False, indent=2),
        "context_json": json.dumps(state.context, ensure_ascii=False, indent=2),
        "constraints_json": json.dumps(state.constraints, ensure_ascii=False, indent=2),
    }}
    context.update(
        {{
{chr(10).join(template_context_update_lines)}
        }}
    )
    return context


def _format_prompt_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _format_prompt_list(value) -> str:
    if not isinstance(value, list):
        return "- none"
    items = [str(item).strip() for item in value if str(item).strip()]
    if not items:
        return "- none"
    return "\\n".join(f"- {{item}}" for item in items)


def run_transition_preview(
    *,
    state: workflow_state.{class_name},
    current_step_id: str,
    observation: dict,
    verifier_result: dict | None,
) -> GraphBuilderPreviewResult:
    return asyncio.run(
        WORKFLOW_GRAPH.run(
            state=state,
            inputs=GraphBuilderPreviewInputs(
                current_step_id=current_step_id,
                observation=observation,
                verifier_result=verifier_result,
            ),
        )
    )


def run_start_preview(
    *,
    state: workflow_state.{class_name},
    run_id: str,
    workflow_id: str,
    workflow_version: str,
) -> YieldResponse:
    return asyncio.run(
        START_GRAPH.run(
            state=state,
            inputs=GraphBuilderStartInputs(
                run_id=run_id,
                workflow_id=workflow_id,
                workflow_version=workflow_version,
            ),
        )
    )
'''


def _render_verifiers_py(
    workflow_spec: dict[str, Any],
    *,
    existing_verifiers_text: str | None = None,
) -> tuple[str, list[str]]:
    preserved_blocks, preservation_warnings = _extract_preservable_custom_verifier_blocks(
        existing_verifiers_text,
        workflow_spec=workflow_spec,
    )
    lines = [
        "from __future__ import annotations",
        "",
        "from pathlib import Path",
        "",
        "from workflows.common.contracts import VerifierResult, make_verifier_result",
        "from workflows.common.policies import condition_matches",
        "",
    ]
    for stage in workflow_spec["stages"]:
        required_schema, optional_schema = _split_required_optional_schema(stage["output_schema"])
        custom_requirements = stage.get("custom_verifier_requirements") or []
        lines.extend(
            [
                f"def verify_{stage['step_id']}(",
                "    *,",
                "    repo_root: str,",
                "    run_id: str,",
                "    step_id: str,",
                "    observation: dict,",
                "    state: dict | None = None,",
                ") -> VerifierResult:",
                "    result = _verify_structured_output_schema(",
                "        run_id=run_id,",
                "        step_id=step_id,",
                f"        required_schema={_python_literal(required_schema)},",
                f"        optional_schema={_python_literal(optional_schema)},",
                f"        verifier_rules={_python_literal(stage['verifier_rules'])},",
                f"        verifier_templates={_python_literal(stage['verifier_templates'])},",
                "        observation=observation,",
                "        repo_root=repo_root,",
                "        state=state,",
                "    )",
                '    if not result["passed"]:',
                "        return result",
            ]
        )
        if custom_requirements:
            runner_name = _custom_verifier_runner_name(stage["step_id"])
            lines.extend(
                [
                    '    output = observation.get("structured_output") or {}',
                    f"    custom_error = {runner_name}(",
                    "        output=output,",
                    "        state=state,",
                    "        repo_root=repo_root,",
                    "    )",
                    "    if custom_error is not None:",
                    "        return _fail(custom_error, run_id, step_id, state)",
                ]
            )
        lines.extend(
            [
                "    return result",
                "",
            ]
        )
    custom_verifier_lines, custom_warnings = _render_custom_verifier_requirement_helpers(
        workflow_spec,
        preserved_blocks=preserved_blocks,
    )
    if custom_verifier_lines:
        lines.extend(custom_verifier_lines)
    lines.extend(
        [
            "def _verify_structured_output_schema(",
            "    *,",
            "    run_id: str,",
            "    step_id: str,",
            "    required_schema: dict[str, str],",
            "    optional_schema: dict[str, str],",
            "    verifier_rules: list[dict],",
            "    verifier_templates: list[dict],",
            "    observation: dict,",
            "    repo_root: str,",
            "    state: dict | None,",
            ") -> VerifierResult:",
            "    output = observation.get(\"structured_output\")",
            "    if output is None:",
            "        output = {}",
            "    if not isinstance(output, dict):",
            "        return _fail(\"structured_output must be an object\", run_id, step_id, state)",
            "    missing = [key for key in required_schema if key not in output]",
            "    if missing:",
            "        return _fail(f\"missing required structured_output keys: {missing}\", run_id, step_id, state)",
            "    schema_errors = []",
            "    for key, schema_type in required_schema.items():",
            "        message = _schema_type_error(key, output.get(key), schema_type, required=True)",
            "        if message:",
            "            schema_errors.append(message)",
            "    for key, schema_type in optional_schema.items():",
            "        if key in output:",
            "            message = _schema_type_error(key, output.get(key), schema_type, required=False)",
            "            if message:",
            "                schema_errors.append(message)",
            "    if schema_errors:",
            "        return _fail(\"; \".join(schema_errors), run_id, step_id, state)",
            "    rule_errors = []",
            "    for rule in verifier_rules:",
            "        message = _verifier_rule_error(rule, output, repo_root)",
            "        if message:",
            "            rule_errors.append(message)",
            "    if rule_errors:",
            "        return _fail(\"; \".join(rule_errors), run_id, step_id, state)",
            "    template_errors = []",
            "    for template in verifier_templates:",
            "        message = _verifier_template_error(template, output, repo_root)",
            "        if message:",
            "            template_errors.append(message)",
            "    if template_errors:",
            "        return _fail(\"; \".join(template_errors), run_id, step_id, state)",
            "    return make_verifier_result(",
            "        passed=True,",
            "        message=\"structured_output schema, verifier rules, and verifier templates are satisfied\",",
            "        details={",
            "            \"run_id\": run_id,",
            "            \"step_id\": step_id,",
            "            \"checked_required_keys\": sorted(required_schema),",
            "            \"checked_optional_keys\": sorted(optional_schema),",
            "        },",
            "    )",
            "",
            "",
            "def _schema_type_error(",
            "    key: str,",
            "    value: object,",
            "    schema_type: str,",
            "    *,",
            "    required: bool,",
            ") -> str | None:",
            "    normalized = schema_type.rstrip(\"?\")",
            "    if value is None and not required:",
            "        return None",
            "    if normalized == \"string\":",
            "        if not isinstance(value, str):",
            "            return f\"{key} must be a string\"",
            "        if required and not value.strip():",
            "            return f\"{key} must be a non-empty string\"",
            "        return None",
            "    if normalized == \"boolean\":",
            "        if not isinstance(value, bool):",
            "            return f\"{key} must be a boolean\"",
            "        return None",
            "    if normalized == \"integer\":",
            "        if not isinstance(value, int) or isinstance(value, bool):",
            "            return f\"{key} must be an integer\"",
            "        return None",
            "    if normalized == \"number\":",
            "        if not isinstance(value, (int, float)) or isinstance(value, bool):",
            "            return f\"{key} must be a number\"",
            "        return None",
            "    if normalized == \"object\":",
            "        if not isinstance(value, dict):",
            "            return f\"{key} must be an object\"",
            "        return None",
            "    if normalized.endswith(\"[]\"):",
            "        if not isinstance(value, list):",
            "            return f\"{key} must be a list\"",
            "        item_type = normalized[:-2]",
            "        for index, item in enumerate(value):",
            "            message = _schema_type_error(f\"{key}[{index}]\", item, item_type, required=False)",
            "            if message:",
            "                return message",
            "        return None",
            "    return None",
            "",
            "",
            "def _verifier_rule_error(rule: dict, output: dict, repo_root: str) -> str | None:",
            "    key = str(rule.get(\"output_key\") or \"\")",
            "    operator = str(rule.get(\"operator\") or \"\")",
            "    expected = rule.get(\"value\")",
            "    message = str(rule.get(\"message\") or f\"{key} failed verifier rule: {operator}\")",
            "    actual = output.get(key)",
            "    if operator == \"one_of\":",
            "        allowed = expected if isinstance(expected, list) else []",
            "        return None if actual in allowed else message",
            "    if operator == \"path_exists\":",
            "        if not isinstance(actual, str) or not actual.strip():",
            "            return message",
            "        candidate = Path(actual)",
            "        if not candidate.is_absolute():",
            "            candidate = Path(repo_root) / candidate",
            "        return None if candidate.exists() else message",
            "    return None if condition_matches(actual, operator, expected) else message",
            "",
            "",
            "def _verifier_template_error(template: dict, output: dict, repo_root: str) -> str | None:",
            "    template_name = str(template.get(\"template\") or \"\")",
            "    message = str(template.get(\"message\") or f\"{template.get('id') or template_name} failed\")",
            "    key = str(template.get(\"output_key\") or \"\")",
            "    actual = output.get(key)",
            "    if template_name == \"conditional_equals\":",
            "        return _conditional_equals_error(actual, output, template, message)",
            "    if template_name == \"conditional_required\":",
            "        return _conditional_required_error(output, template, message)",
            "    if template_name == \"min_count\":",
            "        return _min_count_error(actual, template, message)",
            "    if template_name == \"required_set_members\":",
            "        return _required_set_members_error(actual, template, message)",
            "    if template_name == \"repo_path_policy\":",
            "        return _repo_path_policy_error(actual, template, repo_root, message)",
            "    if template_name == \"artifact_file_contains_sections\":",
            "        return _artifact_file_contains_sections_error(actual, template, repo_root, message)",
            "    return message",
            "",
            "",
            "def _conditional_required_error(output: dict, template: dict, message: str) -> str | None:",
            "    when = template.get(\"when\") or {}",
            "    if not isinstance(when, dict):",
            "        return message",
            "    when_key = str(when.get(\"output_key\") or \"\")",
            "    if not condition_matches(output.get(when_key), str(when.get(\"operator\") or \"\"), when.get(\"value\")):",
            "        return None",
            "    required_key = str(template.get(\"required_key\") or \"\")",
            "    return None if output.get(required_key) else message",
            "",
            "",
            "def _conditional_equals_error(actual, output: dict, template: dict, message: str) -> str | None:",
            "    when = template.get(\"when\") or {}",
            "    if not isinstance(when, dict):",
            "        return message",
            "    when_key = str(when.get(\"output_key\") or \"\")",
            "    if not condition_matches(output.get(when_key), str(when.get(\"operator\") or \"\"), when.get(\"value\")):",
            "        return None",
            "    return None if actual == template.get(\"expected_value\") else message",
            "",
            "",
            "def _min_count_error(actual, template: dict, message: str) -> str | None:",
            "    if not isinstance(actual, list):",
            "        return message",
            "    min_count = template.get(\"min_count\")",
            "    if not isinstance(min_count, int) or isinstance(min_count, bool):",
            "        return message",
            "    return None if len(actual) >= min_count else message",
            "",
            "",
            "def _required_set_members_error(actual, template: dict, message: str) -> str | None:",
            "    if not isinstance(actual, list):",
            "        return message",
            "    required = template.get(\"required_members\")",
            "    if not isinstance(required, list):",
            "        return message",
            "    case_sensitive = bool(template.get(\"case_sensitive\", False))",
            "    if case_sensitive:",
            "        normalized = {str(item).strip() for item in actual if str(item).strip()}",
            "        required_members = {str(item).strip() for item in required if str(item).strip()}",
            "    else:",
            "        normalized = {str(item).strip().lower() for item in actual if str(item).strip()}",
            "        required_members = {str(item).strip().lower() for item in required if str(item).strip()}",
            "    missing = sorted(required_members - normalized)",
            "    return None if not missing else f\"{message}: missing members {missing}\"",
            "",
            "",
            "def _repo_path_policy_error(actual, template: dict, repo_root: str, message: str) -> str | None:",
            "    if not isinstance(actual, str) or not actual.strip():",
            "        return message",
            "    repo = Path(repo_root).resolve()",
            "    candidate = Path(actual)",
            "    if not candidate.is_absolute():",
            "        candidate = repo / candidate",
            "    try:",
            "        relative_path = candidate.resolve().relative_to(repo)",
            "    except ValueError:",
            "        return message",
            "    relative_posix = relative_path.as_posix()",
            "    required_prefix = str(template.get(\"required_prefix\") or \"\")",
            "    if required_prefix and not relative_posix.startswith(required_prefix):",
            "        return message",
            "    forbidden_prefixes = [str(prefix) for prefix in template.get(\"forbidden_prefixes\") or []]",
            "    if any(relative_posix.startswith(prefix) for prefix in forbidden_prefixes):",
            "        return message",
            "    suffix = template.get(\"required_suffix\")",
            "    if isinstance(suffix, str) and suffix and not relative_posix.endswith(suffix):",
            "        return message",
            "    return None",
            "",
            "",
            "def _artifact_file_contains_sections_error(actual, template: dict, repo_root: str, message: str) -> str | None:",
            "    if not isinstance(actual, str) or not actual.strip():",
            "        return message",
            "    candidate = Path(actual)",
            "    if not candidate.is_absolute():",
            "        candidate = Path(repo_root) / candidate",
            "    try:",
            "        text = candidate.read_text(encoding=\"utf-8\")",
            "    except OSError:",
            "        return message",
            "    sections = [str(section) for section in template.get(\"sections\") or []]",
            "    missing = [section for section in sections if section not in text]",
            "    return None if not missing else f\"{message}: missing sections {missing}\"",
            "",
            "",
            "def _meaningful_entries(value) -> list[str]:",
            "    if not isinstance(value, list):",
            "        return []",
            "    entries: list[str] = []",
            "    for item in value:",
            "        if not isinstance(item, str):",
            "            continue",
            "        text = item.strip()",
            "        if text:",
            "            entries.append(text)",
            "    return entries",
            "",
            "",
            "def _path_has_prefix(path: Path, prefix: Path) -> bool:",
            "    try:",
            "        normalized_path = path.as_posix().strip(\"/\")",
            "        normalized_prefix = prefix.as_posix().strip(\"/\")",
            "    except Exception:",
            "        return False",
            "    return normalized_path == normalized_prefix or normalized_path.startswith(normalized_prefix + \"/\")",
            "",
            "",
            "def _extract_single_review_perspective(text: str) -> str | None:",
            "    lowered = str(text).lower()",
            "    matched = [label for label in (\"development\", \"design\", \"testing\") if label in lowered]",
            "    if len(matched) != 1:",
            "        return None",
            "    return matched[0]",
            "",
            "",
            "def _looks_like_visual_evidence(text: str) -> bool:",
            "    lowered = str(text).lower()",
            "    markers = (",
            "        \"visual diff\",",
            "        \"screenshot diff\",",
            "        \"screenshot comparison\",",
            "        \"design comparison\",",
            "        \"figma\",",
            "        \"pixel diff\",",
            "        \"visual qa\",",
            "        \"mock comparison\",",
            "    )",
            "    return any(marker in lowered for marker in markers)",
            "",
            "",
            "def _has_explicit_severity_prefix(text: str) -> bool:",
            "    return _extract_severity_prefix(text) is not None",
            "",
            "",
            "def _extract_severity_prefix(text: str) -> str | None:",
            "    normalized = str(text).strip().lower()",
            "    for prefix in (\"critical\", \"blocker\", \"p0\", \"important\", \"high\", \"p1\", \"major\", \"medium\", \"minor\", \"low\"):",
            "        if normalized.startswith(prefix + \":\"):",
            "            return prefix",
            "    return None",
            "",
            "",
            "def _severity_rank(severity: str) -> int:",
            "    ranks = {",
            "        \"critical\": 0,",
            "        \"blocker\": 0,",
            "        \"p0\": 0,",
            "        \"important\": 1,",
            "        \"high\": 1,",
            "        \"p1\": 1,",
            "        \"major\": 2,",
            "        \"medium\": 3,",
            "        \"minor\": 4,",
            "        \"low\": 5,",
            "    }",
            "    return ranks.get(severity, 999)",
            "",
            "",
            "def _fail(message: str, run_id: str, step_id: str, state: dict | None) -> VerifierResult:",
            "    return make_verifier_result(",
            "        passed=False,",
            "        message=message,",
            "        details={\"run_id\": run_id, \"step_id\": step_id, \"state\": state or {}},",
            "    )",
            "",
        ]
    )
    return "\n".join(lines), preservation_warnings + custom_warnings


def _render_custom_verifier_requirement_helpers(
    workflow_spec: dict[str, Any],
    *,
    preserved_blocks: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    warnings: list[str] = []
    current_requirement_keys: set[tuple[str, str]] = set()
    for stage in workflow_spec["stages"]:
        requirements = stage.get("custom_verifier_requirements") or []
        if not requirements:
            continue
        stage_requirement_names: set[str] = set()
        runner_name = _custom_verifier_runner_name(stage["step_id"])
        lines.extend(
            [
                f"def {runner_name}(",
                "    *,",
                "    output: dict,",
                "    state: dict | None,",
                "    repo_root: str,",
                ") -> str | None:",
                "    errors: list[str] = []",
            ]
        )
        for requirement in requirements:
            requirement_key = (stage["step_id"], requirement["id"])
            current_requirement_keys.add(requirement_key)
            function_name = _custom_verifier_requirement_function_name(
                stage["step_id"], requirement["id"]
            )
            if function_name in stage_requirement_names:
                raise WorkflowCreatorError(
                    "generated helper naming collision for custom verifier requirement "
                    f"{stage['step_id']}.{requirement['id']}"
                )
            stage_requirement_names.add(function_name)
            lines.extend(
                [
                    f"    message = {function_name}(",
                    "        output=output,",
                    "        state=state,",
                    "        repo_root=repo_root,",
                    "    )",
                    "    if message:",
                    "        errors.append(message)",
                ]
            )
        lines.extend(
            [
                '    return "; ".join(errors) if errors else None',
                "",
            ]
        )
        for requirement in requirements:
            requirement_key = (stage["step_id"], requirement["id"])
            function_name = _custom_verifier_requirement_function_name(
                stage["step_id"], requirement["id"]
            )
            metadata = _custom_verifier_requirement_metadata(stage, requirement)
            preserved = preserved_blocks.get(requirement_key)
            if (
                preserved is not None
                and preserved["template_version"] == metadata["template_version"]
                and preserved["spec_fingerprint"] == metadata["spec_fingerprint"]
                and preserved["implementation_version"] == metadata["implementation_version"]
            ):
                lines.extend(preserved["source_lines"])
                lines.append("")
                continue
            lines.extend(_render_custom_requirement_scaffold(stage, requirement, metadata))
    for stale_key in sorted(set(preserved_blocks) - current_requirement_keys):
        warnings.append(
            "Removed preserved custom verifier implementation because the requirement no longer "
            f"exists in spec.json: {stale_key[0]}.{stale_key[1]}"
        )
    return lines, warnings


def _custom_verifier_runner_name(step_id: str) -> str:
    return f"_run_custom_verifier_requirements_{step_id}"


def _custom_verifier_requirement_function_name(step_id: str, requirement_id: str) -> str:
    return f"_custom_verifier_requirement_{step_id}_{requirement_id}"


def _custom_requirement_doc_lines(requirement: dict[str, Any]) -> list[str]:
    doc_lines = [
        "Custom verifier scaffold generated from stages[].custom_verifier_requirements.",
        "Self-contained contract: keep this requirement-scoped verifier self-contained when practical.",
        "If reuse is needed, import stable helpers from shared modules outside verifiers.py.",
        "Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.",
        "",
        f"Requirement: {requirement['description']}",
    ]
    signals = requirement.get("signals") or []
    if signals:
        doc_lines.append(f"Signals: {', '.join(signals)}")
    implementation_surface = requirement.get("implementation_surface") or []
    if implementation_surface:
        doc_lines.append(f"Implementation surfaces: {', '.join(implementation_surface)}")
    implementation_notes = requirement.get("implementation_notes")
    if implementation_notes:
        doc_lines.append(f"Implementation notes: {implementation_notes}")
    hint_pseudocode = requirement.get("hint_pseudocode") or []
    if hint_pseudocode:
        doc_lines.append("Hint pseudocode:")
        doc_lines.extend(f"- {step}" for step in hint_pseudocode)
    test_intent = requirement.get("test_intent") or []
    if test_intent:
        doc_lines.append("Test intent:")
        doc_lines.extend(f"- {item}" for item in test_intent)
    return doc_lines


def _render_custom_requirement_scaffold(
    stage: dict[str, Any],
    requirement: dict[str, Any],
    metadata: dict[str, Any],
) -> list[str]:
    function_name = _custom_verifier_requirement_function_name(
        stage["step_id"],
        requirement["id"],
    )
    doc_lines = _custom_requirement_doc_lines(requirement)
    implementation_surface = requirement.get("implementation_surface") or []
    hint_pseudocode = requirement.get("hint_pseudocode") or []
    test_intent = requirement.get("test_intent") or []
    lines = [
        f"# custom_verifier_stage_id: {metadata['stage_id']}",
        f"# custom_verifier_requirement_id: {metadata['requirement_id']}",
        f"# template_version: {metadata['template_version']}",
        f"# spec_fingerprint: {metadata['spec_fingerprint']}",
        f"# implementation_version: {_implementation_version_marker(metadata['implementation_version'])}",
        f"def {function_name}(",
        "    *,",
        "    output: dict,",
        "    state: dict | None,",
        "    repo_root: str,",
        ") -> str | None:",
        f'    """{chr(10).join(doc_lines)}"""',
        "    _ = output, state, repo_root",
        f"    # TODO(custom_verifier_requirement): Implement `{requirement['id']}`.",
    ]
    if implementation_surface:
        lines.append(f"    # Intended implementation surfaces: {', '.join(implementation_surface)}.")
        if "verifier" not in implementation_surface:
            lines.append("    # Verifier scaffolding is provided as context only; implement the")
            lines.append(
                "    # primary logic in the declared non-verifier surfaces as well."
            )
    if hint_pseudocode:
        lines.extend(
            [
                "    # Hint pseudocode:",
                *[f"    # - {step}" for step in hint_pseudocode],
            ]
        )
    if test_intent:
        lines.extend(
            [
                "    # Test intent:",
                *[f"    # - {item}" for item in test_intent],
            ]
        )
    lines.extend(
        [
            "    # This scaffold is generated during initial workflow authoring so the",
            "    # review pass can validate or refine concrete verifier logic instead",
            "    # of creating it from scratch.",
            "    return None",
            "",
        ]
    )
    return lines


def _custom_verifier_requirement_metadata(
    stage: dict[str, Any],
    requirement: dict[str, Any],
) -> dict[str, Any]:
    return {
        "stage_id": stage["step_id"],
        "requirement_id": requirement["id"],
        "template_version": _CUSTOM_VERIFIER_TEMPLATE_VERSION,
        "spec_fingerprint": _custom_requirement_spec_fingerprint(stage, requirement),
        "implementation_version": requirement.get("implementation_version"),
    }


def _custom_requirement_spec_fingerprint(stage: dict[str, Any], requirement: dict[str, Any]) -> str:
    payload = {
        "id": requirement["id"],
        "description": requirement["description"],
        "signals": requirement.get("signals"),
        "implementation_surface": requirement.get("implementation_surface"),
        "implementation_notes": requirement.get("implementation_notes"),
        "hint_pseudocode": requirement.get("hint_pseudocode"),
        "test_intent": requirement.get("test_intent"),
        "stage_contract_context": {
            "step_id": stage["step_id"],
            "output_schema": stage["output_schema"],
            "custom_verifier_helper_signature": {
                "parameters": ["output", "state", "repo_root"],
                "return_type": "str | None",
            },
            "custom_verifier_runner_contract": {
                "passes": ["output", "state", "repo_root"],
                "aggregates": "join_non_empty_error_messages",
            },
        },
    }
    normalized = _normalize_for_custom_verifier_fingerprint(payload)
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_for_custom_verifier_fingerprint(value: Any) -> Any:
    if isinstance(value, dict):
        normalized_items: dict[str, Any] = {}
        for key in sorted(value):
            normalized_value = _normalize_for_custom_verifier_fingerprint(value[key])
            if normalized_value is not None:
                normalized_items[key] = normalized_value
        return normalized_items or None
    if isinstance(value, list):
        return [_normalize_for_custom_verifier_fingerprint(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return None
    return value


def _extract_preservable_custom_verifier_blocks(
    existing_verifiers_text: str | None,
    *,
    workflow_spec: dict[str, Any],
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[str]]:
    if not existing_verifiers_text:
        return {}, []

    try:
        module = ast.parse(existing_verifiers_text)
    except SyntaxError as exc:
        return {}, [f"Could not parse existing verifiers.py for preservation: {exc.msg}"]

    lines = existing_verifiers_text.splitlines()
    blocks: dict[tuple[str, str], dict[str, Any]] = {}
    warnings: list[str] = []
    legacy_function_metadata = _legacy_custom_verifier_function_metadata(workflow_spec)
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("_custom_verifier_requirement_"):
            continue
        if node.decorator_list:
            warnings.append(
                "Skipped preserved custom verifier implementation with unsupported decorators: "
                f"{node.name}"
            )
            continue
        leading_comment_lines, _ = _leading_comment_lines_for_node(lines, node)
        metadata = _parse_custom_verifier_metadata(lines, node)
        source_lines = lines[metadata["start_lineno"] - 1 : node.end_lineno] if metadata is not None else None
        if metadata is None:
            if leading_comment_lines:
                warnings.append(
                    "Regenerated custom verifier scaffold because preservation metadata was missing "
                    f"or malformed for {node.name}"
                )
                continue
            legacy_metadata = legacy_function_metadata.get(node.name)
            if legacy_metadata is None:
                warnings.append(
                    "Regenerated custom verifier scaffold because preservation metadata was missing "
                    f"or malformed for {node.name}"
                )
                continue
            metadata = dict(legacy_metadata)
            source_lines = _custom_verifier_metadata_comment_lines(metadata) + lines[
                node.lineno - 1 : node.end_lineno
            ]
            warnings.append(
                "Migrated legacy custom verifier implementation without preservation metadata for "
                f"{metadata['stage_id']}.{metadata['requirement_id']}"
            )
        block_key = (metadata["stage_id"], metadata["requirement_id"])
        if block_key in blocks:
            warnings.append(
                "Regenerated duplicate preserved custom verifier implementation mapping for "
                f"{metadata['stage_id']}.{metadata['requirement_id']}"
            )
            continue
        blocks[block_key] = {
            **metadata,
            "source_lines": source_lines,
        }
    return blocks, warnings


def _legacy_custom_verifier_function_metadata(
    workflow_spec: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    metadata_by_name: dict[str, dict[str, Any]] = {}
    for stage in workflow_spec["stages"]:
        for requirement in stage.get("custom_verifier_requirements") or []:
            function_name = _custom_verifier_requirement_function_name(
                stage["step_id"],
                requirement["id"],
            )
            metadata_by_name[function_name] = {
                **_custom_verifier_requirement_metadata(stage, requirement),
                "start_lineno": 0,
            }
    return metadata_by_name


def _custom_verifier_metadata_comment_lines(metadata: dict[str, Any]) -> list[str]:
    return [
        f"# custom_verifier_stage_id: {metadata['stage_id']}",
        f"# custom_verifier_requirement_id: {metadata['requirement_id']}",
        f"# template_version: {metadata['template_version']}",
        f"# spec_fingerprint: {metadata['spec_fingerprint']}",
        f"# implementation_version: {_implementation_version_marker(metadata['implementation_version'])}",
    ]


def _parse_custom_verifier_metadata(lines: list[str], node: ast.FunctionDef) -> dict[str, Any] | None:
    comment_lines, metadata_start_lineno = _leading_comment_lines_for_node(lines, node)
    if not comment_lines:
        return None
    comment_lines.reverse()
    metadata: dict[str, str] = {}
    for comment_line in comment_lines:
        match = re.fullmatch(r"#\s*([a-z_]+):\s*(.+)", comment_line)
        if match is None:
            return None
        metadata[match.group(1)] = match.group(2).strip()
    required_keys = {
        "custom_verifier_stage_id",
        "custom_verifier_requirement_id",
        "template_version",
        "spec_fingerprint",
        "implementation_version",
    }
    if set(metadata) != required_keys:
        return None
    try:
        template_version = int(metadata["template_version"])
    except ValueError:
        return None
    implementation_version = _parse_implementation_version_marker(
        metadata["implementation_version"]
    )
    if implementation_version is _INVALID_IMPLEMENTATION_VERSION:
        return None
    return {
        "start_lineno": metadata_start_lineno,
        "stage_id": metadata["custom_verifier_stage_id"],
        "requirement_id": metadata["custom_verifier_requirement_id"],
        "template_version": template_version,
        "spec_fingerprint": metadata["spec_fingerprint"],
        "implementation_version": implementation_version,
    }


def _leading_comment_lines_for_node(
    lines: list[str],
    node: ast.FunctionDef,
) -> tuple[list[str], int]:
    comment_lines: list[str] = []
    line_index = node.lineno - 2
    while line_index >= 0:
        stripped = lines[line_index].strip()
        if not stripped.startswith("#"):
            break
        comment_lines.append(stripped)
        line_index -= 1
    return comment_lines, line_index + 2


_INVALID_IMPLEMENTATION_VERSION = object()


def _parse_implementation_version_marker(value: str) -> int | None | object:
    if value == "none":
        return None
    try:
        parsed = int(value)
    except ValueError:
        return _INVALID_IMPLEMENTATION_VERSION
    if parsed < 1:
        return _INVALID_IMPLEMENTATION_VERSION
    return parsed


def _implementation_version_marker(value: int | None) -> str:
    return "none" if value is None else str(value)


def _split_required_optional_schema(output_schema: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    required: dict[str, str] = {}
    optional: dict[str, str] = {}
    for key, value in output_schema.items():
        if isinstance(value, str) and value.endswith("?"):
            optional[key] = value[:-1]
        else:
            optional_or_required_value = value if isinstance(value, str) else str(value)
            required[key] = optional_or_required_value
    return required, optional


def _stage_role(stage: dict[str, Any]) -> str:
    prompt_sections = stage.get("prompt_sections")
    if isinstance(prompt_sections, dict):
        stage_goal = prompt_sections.get("stage_goal")
        if isinstance(stage_goal, str) and stage_goal.strip():
            return stage_goal.strip()
    for key in ("prompt", "expected_artifact", "intent"):
        value = stage.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Complete the workflow stage."


def _stage_output(stage: dict[str, Any]) -> str:
    expected_artifact = stage.get("expected_artifact")
    if isinstance(expected_artifact, str) and expected_artifact.strip():
        return expected_artifact.strip()
    output_schema = stage.get("output_schema")
    if isinstance(output_schema, dict) and output_schema:
        return ", ".join(f"`{key}`" for key in output_schema)
    return "Stage output matching the step contract."


def _stage_completion(stage: dict[str, Any]) -> str:
    done_when = stage.get("done_when")
    if isinstance(done_when, list):
        items = [str(item).strip() for item in done_when if str(item).strip()]
        if items:
            return "<br>".join(items)
    return "The stage verifier and policy gates pass."


def _escape_markdown_table_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", r"\|")


def _render_stage_node(stage: dict[str, Any]) -> str:
    step_id = stage["step_id"]
    return f"{step_id}[{step_id}]"


def _render_flowchart_md(workflow_spec: dict[str, Any]) -> str:
    workflow_id = workflow_spec["workflow_id"]
    stages = workflow_spec["stages"]
    main_stages = [stage for stage in stages if stage["stage_kind"] == "main"]
    lines = [
        f"# {workflow_id} Flowchart",
        "",
        f"Developer-facing overview for `{workflow_id}`.",
        "",
        "The Mermaid diagram shows the durable route; the table below explains what each stage does.",
        "",
        "```mermaid",
        "flowchart TD",
    ]
    if main_stages:
        lines.append(f"    start([start {workflow_id}]) --> {_render_stage_node(main_stages[0])}")
    else:
        lines.append(f"    start([start {workflow_id}]) --> {workflow_spec['final_step_id']}([{workflow_spec['final_step_id']}])")
    for previous, next_stage in zip(main_stages, main_stages[1:]):
        lines.append(
            f"    {previous['step_id']} -->|success| {_render_stage_node(next_stage)}"
        )
    if main_stages:
        lines.append(
            f"    {main_stages[-1]['step_id']} -->|success| {workflow_spec['final_step_id']}([{workflow_spec['final_step_id']}])"
        )
    for stage in stages:
        for route in stage["outcome_routes"]:
            target = _render_transition_target(route["next_node"], workflow_spec)
            label = _escape_mermaid_label(route["outcome"])
            lines.append(f"    {stage['step_id']} -->|{label}| {target}")
        for transition in stage["transitions"]:
            target = _render_transition_target(transition["next_node"], workflow_spec)
            transition_label = f"{transition['output_key']} {transition['operator']}"
            if transition.get("value") is not None:
                transition_label += f" {transition['value']}"
            label = _escape_mermaid_label(transition_label)
            lines.append(f"    {stage['step_id']} -->|{label}| {target}")
        if stage["stage_kind"] == "recovery":
            target = _render_transition_target(stage["recovery_return_node"], workflow_spec)
            lines.append(f"    {stage['step_id']} -->|recovery complete| {target}")
            lines.append(f"    {stage['step_id']} -.->|partial / failed / verifier| {stage['step_id']}")
            lines.append(f"    {stage['step_id']} -.->|blocked| repair_loop")
    lines.append("    unblock_loop[[request_unblocking_input]]")
    lines.append("    repair_loop[[repair_and_resume]]")
    lines.append("    resume_target[[return_stage_id / originating stage]]")
    for stage in main_stages:
        lines.append(f"    {stage['step_id']} -.->|blocked| repair_loop")
        lines.append(
            f"    {stage['step_id']} -.->|{_main_stage_repair_loop_label(stage)}| repair_loop"
        )
    lines.extend(
        [
            "    unblock_loop -.->|resume via repair owner or return_stage_id| resume_target",
            "    unblock_loop -.->|stay when return_stage_id missing| unblock_loop",
            f"    repair_loop -.->|blocked after {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} tries| unblock_loop",
            "    repair_loop -.->|retry via return_stage_id when repair succeeds| resume_target",
            f"    repair_loop -.->|blocked before {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} tries / partial / failed / missing return_stage_id| repair_loop",
            "```",
            "",
            f"Global note: if `max_steps` is exceeded, runtime policy preempts normal business routing and sends the workflow to `repair_and_resume`; that shared repair stage may escalate to `request_unblocking_input` only after {_REPAIR_ATTEMPTS_BEFORE_UNBLOCK} blocked self-repair attempts while preserving `return_stage_id`.",
            "",
        ]
    )
    lines.extend(["## Stage Responsibilities", ""])
    if stages:
        lines.extend(["| Stage | Does | Produces | Done when |", "|---|---|---|---|"])
        for stage in stages:
            lines.append(
                "| "
                f"`{stage['step_id']}` | "
                f"{_escape_markdown_table_cell(_stage_role(stage))} | "
                f"{_escape_markdown_table_cell(_stage_output(stage))} | "
                f"{_escape_markdown_table_cell(_stage_completion(stage))} |"
            )
        final_prompt = workflow_spec.get("final_prompt") or "Prepare the final workflow summary."
        lines.append(
            "| "
            f"`{workflow_spec['final_step_id']}` | "
            f"{_escape_markdown_table_cell(str(final_prompt))} | "
            "Final workflow summary or handoff artifact. | "
            "Previous business stage completed successfully. |"
        )
    else:
        lines.append("No business stages were supplied; this scaffold routes directly to the final summary.")
    lines.extend(
        [
            "",
            "## Maintenance Notes",
            "",
            "- Keep this diagram aligned with `policy.py` and `graphbuilder_runtime.py`.",
            "- If you add non-linear business gates, update `policy.py` and this diagram together.",
            "- Keep repetitive repair edges summarized unless repair policy is the workflow's core behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def _main_stage_repair_loop_label(stage: dict[str, Any]) -> str:
    handled_outcomes = {
        str(route.get("outcome"))
        for route in stage.get("outcome_routes") or []
        if route.get("outcome")
    }
    labels = ["partial", "failed"]
    if "verifier_failed" not in handled_outcomes:
        labels.append("verifier")
    return " / ".join(labels)


def _render_transition_target(next_node: str, workflow_spec: dict[str, Any]) -> str:
    if next_node == workflow_spec["final_step_id"]:
        return f"{next_node}([{next_node}])"
    stage_by_id = {stage["step_id"]: stage for stage in workflow_spec["stages"]}
    if next_node in stage_by_id:
        return _render_stage_node(stage_by_id[next_node])
    return next_node


def _escape_mermaid_label(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ")


def _render_agent_review_md(workflow_spec: dict[str, Any]) -> str:
    workflow_id = workflow_spec["workflow_id"]
    stages = workflow_spec["stages"]
    stage_ids = [stage["step_id"] for stage in stages]
    if stage_ids:
        stage_list = "\n".join(f"- `{stage_id}`" for stage_id in stage_ids)
    else:
        stage_list = "- No business stages were supplied; this is a blank scaffold."

    custom_verifier_lines: list[str] = []
    for stage in stages:
        requirements = stage.get("custom_verifier_requirements") or []
        if not requirements:
            continue
        if not custom_verifier_lines:
            custom_verifier_lines.extend(["## Declared Custom Verifier Requirements", ""])
        custom_verifier_lines.append(f"### `{stage['step_id']}`")
        custom_verifier_lines.append("")
        for requirement in requirements:
            custom_verifier_lines.append(
                f"- `{requirement['id']}`: {requirement['description']}"
            )
            signals = requirement.get("signals") or []
            if signals:
                signal_text = ", ".join(f"`{signal}`" for signal in signals)
                custom_verifier_lines.append(f"  Signals: {signal_text}")
            implementation_surface = requirement.get("implementation_surface") or []
            if implementation_surface:
                surface_text = ", ".join(f"`{surface}`" for surface in implementation_surface)
                custom_verifier_lines.append(
                    f"  Implementation surfaces: {surface_text}"
                )
            custom_verifier_lines.append(
                "  Self-contained contract: keep this requirement-scoped verifier self-contained when practical."
            )
            custom_verifier_lines.append(
                "  If reuse is needed, import stable helpers from shared modules outside verifiers.py."
            )
            custom_verifier_lines.append(
                "  same-file helper dependencies as a blocking review issue."
            )
            implementation_notes = requirement.get("implementation_notes")
            if implementation_notes:
                custom_verifier_lines.append(
                    f"  Implementation notes: {implementation_notes}"
                )
            hint_pseudocode = requirement.get("hint_pseudocode") or []
            if hint_pseudocode:
                custom_verifier_lines.append("  Hint pseudocode:")
                for step in hint_pseudocode:
                    custom_verifier_lines.append(f"    - {step}")
            test_intent = requirement.get("test_intent") or []
            if test_intent:
                custom_verifier_lines.append("  Test intent:")
                for item in test_intent:
                    custom_verifier_lines.append(f"    - {item}")
        custom_verifier_lines.append("")
    custom_verifier_block = "\n".join(custom_verifier_lines)

    return f"""# Agent Review for `{workflow_id}`

This workflow was generated from `spec.json` by `workflow-creator`. Treat
`spec.json` as the source of truth for the review. The generated files prove the
spec can become importable runtime surfaces; they do not prove the spec describes
the right workflow.

## Generated Stage Path

{stage_list}

{custom_verifier_block}

## What The Script Generated

- `contract.py`: input contract, step contracts, skill routes, and verifier refs.
- `state.py`: durable state fields, serialization, basic state promotion, and repair bookkeeping.
- `policy.py`: declared transitions, default happy path, and shared blocked / partial / failed / verifier repair routing.
- `graphbuilder_runtime.py`: node definitions, start preview, transition preview, and prompt rendering.
- `verifiers.py`: baseline structured-output checks plus declared rule/template verifier plumbing.
- `prompts/*.md`: stage prompt assets.
- `references/flowchart.md`: linear flowchart and summarized repair loop.
- `manifest.json` and the `workflow-binding.json` entry.

## Agent-Owned Review Checklist

1. Before starting agent review, explicitly ask the user for permission to use
   review subagents and wait for consent. This workflow is not review-complete
   until that subagent-backed pass runs. Once authorized, use multiple review
   subagents to inspect the spec, generated code, or tests from different
   angles. Typical angles include prompt review (`prompts/*.md`), verifier
   review (`verifiers.py` and verifier declarations), contract review
   (`contract.py` and output schemas), and graph/runtime-flow review
   (`graphbuilder_runtime.py`, `policy.py`, and `references/flowchart.md`). If
   authorization is still missing, stop and report the workflow as blocked
   instead of falling back to a one-thread review. If the user explicitly
   denies authorization, review the authorization gate as a normal business
   completion branch that should close the workflow before implementation
   planning, not as an error-state block.
2. Review `spec.json` first. Check whether it fully describes the intended
   workflow boundary, stage order, stage kinds, prompts, outputs, dependencies,
   state promotion, outcome routes, repair gates, shared repair helpers,
   recovery return points, business transitions, verifier rules, verifier
   templates, final prompt, and regression tests. Do not start by patching
   generated Python files.
3. Compare the spec against the closest mature workflow in
   `workflow-runtime/workflows/` to catch missing durable control surfaces:
   approvals, user input gates, repair return points, final-stage gates, and
   state carried into later prompts.
4. Verify stage boundaries in the spec: each stage should have one durable
   responsibility, clear blocked conditions, and no hidden implementation step.
   For skill-owned stages, require exactly one primary owner. If a stage needs
   multiple primary skills or none at all, split or redefine the stage.
5. Verify prompt-contract intent in the spec before reading generated prompts:
   each stage `prompt` should describe the stage goal, intended primary skill,
   execution object or artifact, and minimum workflow inputs. It should not
   teach the routed skill how to run its internal checklist. Multi-route stages
   should keep the primary route first and any others in supporting-only roles,
   `prompt_sections` should match `done_when`, and placeholders should come
   from start input or declared state promotion. When a placeholder name exists
   in both start input and promoted state, later prompts should prefer the
   promoted state value. Generated prompt assets do not need to render a
   separate `Stage Goal:` heading; review the action line and prompt body
   against `prompt_sections.stage_goal` in `spec.json` instead of expecting that
   heading to appear verbatim in `prompts/*.md`.
6. Verify output semantics in the spec: boolean fields must be booleans,
   enum-like fields should have `verifier_rules`, path fields should use
   `path_exists` when existence matters, common DSL-expressible invariants
   should use `verifier_templates`, and any remaining domain-specific verifier
   logic should be declared in `custom_verifier_requirements` with enough detail
   for generated custom verifier scaffolds to be completed before review.
7. Verify state promotion in the spec: every output needed by later prompts,
   final summary, repair logic, or tests should appear in `state_updates` and
   `template_context_keys` where appropriate.
8. Verify outcome and recovery routing in the spec: `outcome_routes` should
   cover business-specific `blocked`, `partial`, `failed`, or `verifier_failed`
   recovery paths; `stage_kind: "recovery"` stages should have the right
   `recovery_return_node`. Shared recovery helpers should never silently fall
   back to the first main stage when `return_stage_id` is missing.
9. Verify business repair routing and transitions in the spec:
   `repair_conditions` should mean repair/unblock behavior, `transitions` should
   mean normal business routing, and each target should be the right return
   point.
10. Verify final routing in the spec: the last main stage should only complete
   when declared verifier rules, verifier templates, any generated or completed
   custom verifier code required by `custom_verifier_requirements`, and business gates prove the
   workflow is ready for the final prompt.
11. Verify `regression_tests` in the spec cover start, resume, repair, verifier
   failure, business gates, final completion, prompt placeholder coverage, and
   recovery helper semantics such as returning to `return_stage_id`.
12. After the spec review, verify generated files faithfully implement the spec:
    `contract.py`, `state.py`, `policy.py`, `verifiers.py`, `prompts/*.md`,
    `references/flowchart.md`, `manifest.json`, and generated workflow tests
    should match the normalized blueprint. If semantics need to change, update
    `spec.json` first, then regenerate or make matching code edits.

## Common Generated Skeleton Gaps

- Baseline verifiers check required keys and flat schema types such as
  `boolean`, `string`, and `string[]`; stage return schemas must not use
  `object` or `object[]` because agents would have to infer hidden structure.
  Declared `verifier_rules` add simple deterministic checks such as enum
  membership, path existence, and non-empty fields.
- Output fields with stricter cross-field consistency or domain meaning should
  first be added to `spec.json` when expressible. Use `verifier_templates` for
  whitelistable flat checks such as conditional required fields, uniqueness,
  minimum counts, and artifact section checks when the DSL expresses the
  invariant cleanly; otherwise declare the requirement in
  `custom_verifier_requirements` instead of weakening the acceptance contract.
- Declared `custom_verifier_requirements` now generate requirement-scoped
  scaffolds in `verifiers.py`. Treat those functions as authoring-time work:
  finish or tighten them before review sign-off, then use agent review to
  validate/refine the resulting verifier logic and regression coverage.
- A generated `outcome_route`, `repair_condition`, `transition`, or recovery
  return follows the declared target; it does not know whether that target is
  the best business return point.
- Prompt placeholders are mechanically exposed from declared state updates, so
  missing prompt context is usually a spec gap in `state_updates` or
  `template_context_keys`. When a placeholder name exists in both start input
  and promoted state, generated prompt context now prefers the promoted state
  value; review workflows that rely on a stale start-input copy of the same key.
- Prompt assets are generated from declared prompt sections; they still need a
  human/agent pass to catch action lines that are vague or overly procedural,
  stale placeholders, missing blocked conditions, or drift between prompt text
  and step contracts. `prompt_sections.stage_goal` stays in `spec.json` as the
  review source of truth and is not required to appear as a separate `Stage
  Goal:` block in generated prompt assets.
- Shared recovery helpers should now be described in `spec.json` and stay on
  the recovery node when `return_stage_id` is missing. If review finds a
  workflow that still depends on a silent fallback, fix the workflow state
  bookkeeping instead of loosening policy.

## Review Output

Write findings first, ordered by severity. Prefer citing `spec.json` when the
source of the issue is an incomplete or ambiguous workflow declaration. Cite
generated files when they drift from the spec. If edits are needed, update
`spec.json` first, then regenerate or make matching workflow-file and test edits
before calling the workflow shipped.
"""


def _render_regression_tests_py(workflow_spec: dict[str, Any]) -> str:
    workflow_id = workflow_spec["workflow_id"]
    class_name = _workflow_class_prefix(workflow_id) + "GeneratedTests"
    lines = [
        "import sys",
        "import unittest",
        "from pathlib import Path",
        "",
        "",
        "RUNTIME_ROOT = Path(__file__).resolve().parents[3]",
        "SKILL_ROOT = RUNTIME_ROOT.parent",
        "REPO_ROOT = SKILL_ROOT.parents[1]",
        "for _lib_root in (REPO_ROOT / '.venv' / 'lib', SKILL_ROOT / '.venv' / 'lib', REPO_ROOT.parent / '.venv' / 'lib'):",
        "    _site_packages = next(_lib_root.glob('python*/site-packages'), None)",
        "    if _site_packages is not None and str(_site_packages) not in sys.path:",
        "        sys.path.insert(0, str(_site_packages))",
        "if str(RUNTIME_ROOT) not in sys.path:",
        "    sys.path.insert(0, str(RUNTIME_ROOT))",
        "",
        f"from workflows.{workflow_id} import graphbuilder_runtime, state as workflow_state, verifiers",
        "",
        "",
        f"class {class_name}(unittest.TestCase):",
        "    def _make_state(self, payload=None):",
        "        if payload is not None:",
        "            return workflow_state.deserialize_state(payload)",
        "        return workflow_state.make_initial_state(",
        "            {",
        '                "task_input": {"goal": "generated workflow regression"},',
        '                "context": {},',
        '                "constraints": {},',
        "            }",
        "        )",
        "",
    ]
    for case in workflow_spec["regression_tests"]:
        if case["type"] == "transition":
            lines.extend(
                [
                    f"    def test_{case['name']}(self):",
                    "        result = graphbuilder_runtime.run_transition_preview(",
                    f"            state=self._make_state({_python_literal(case['state'])}),",
                    f"            current_step_id={case['current_step_id']!r},",
                    f"            observation={_python_literal(case['observation'])},",
                    f"            verifier_result={_python_literal(case['verifier_result'])},",
                    "        )",
                    f"        self.assertEqual(result.step_id, {case['expected_next_node']!r})",
                    f"        self.assertEqual(result.branch_kind, {case['expected_branch_kind']!r})",
                    "",
                ]
            )
            continue
        lines.extend(
                [
                    f"    def test_{case['name']}(self):",
                    f"        result = verifiers.verify_{case['step_id']}(",
                    "            repo_root=str(REPO_ROOT),",
                    '            run_id="generated-test-run",',
                    f"            step_id={case['step_id']!r},",
                    f"            observation={_python_literal(case['observation'])},",
                    f"            state={_python_literal(case['state'] or {})},",
                    "        )",
                    f"        self.assertIs(result['passed'], {case['expected_passed']!r})",
                    "",
                ]
            )
    lines.extend(_render_default_structural_regression_tests(workflow_spec))
    lines.extend(
        [
            "",
            'if __name__ == "__main__":',
            "    unittest.main()",
            "",
        ]
    )
    return "\n".join(lines)


def _render_default_structural_regression_tests(workflow_spec: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    main_stages = [stage for stage in workflow_spec["stages"] if stage["stage_kind"] == "main"]
    if main_stages:
        resume_target = main_stages[0]["step_id"]
        preserved_return_stage = main_stages[-1]["step_id"]
        lines.extend(
            [
                "    def test_generated_request_unblocking_input_resumes_to_return_stage(self):",
                "        state = self._make_state(None)",
                f"        state.return_stage_id = {resume_target!r}",
                "        state.repair_context = {'source_stage_id': 'request_unblocking_input'}",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=state,",
                '            current_step_id="request_unblocking_input",',
                "            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},",
                "            verifier_result=None,",
                "        )",
                f"        self.assertEqual(result.step_id, {resume_target!r})",
                '        self.assertEqual(result.branch_kind, "continue")',
                "",
                "    def test_generated_request_unblocking_input_without_return_stage_stays_put(self):",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=self._make_state(None),",
                '            current_step_id="request_unblocking_input",',
                "            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},",
                "            verifier_result=None,",
                "        )",
                '        self.assertEqual(result.step_id, "request_unblocking_input")',
                '        self.assertEqual(result.branch_kind, "repair")',
                "",
                "    def test_generated_request_unblocking_input_returns_to_repair_owner(self):",
                "        state = self._make_state(None)",
                f"        state.return_stage_id = {resume_target!r}",
                "        state.repair_context = {'source_stage_id': 'repair_and_resume'}",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=state,",
                '            current_step_id="request_unblocking_input",',
                "            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},",
                "            verifier_result=None,",
                "        )",
                '        self.assertEqual(result.step_id, "repair_and_resume")',
                '        self.assertEqual(result.branch_kind, "continue")',
                "",
                "    def test_generated_repair_and_resume_resumes_to_return_stage(self):",
                "        state = self._make_state(None)",
                f"        state.return_stage_id = {resume_target!r}",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=state,",
                '            current_step_id="repair_and_resume",',
                "            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {}},",
                "            verifier_result=None,",
                "        )",
                f"        self.assertEqual(result.step_id, {resume_target!r})",
                '        self.assertEqual(result.branch_kind, "continue")',
                "",
                "    def test_generated_repair_and_resume_without_return_stage_stays_put(self):",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=self._make_state(None),",
                '            current_step_id="repair_and_resume",',
                "            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {}},",
                "            verifier_result=None,",
                "        )",
                '        self.assertEqual(result.step_id, "repair_and_resume")',
                '        self.assertEqual(result.branch_kind, "retry")',
                "",
                "    def test_generated_repair_and_resume_blocked_before_threshold_retries_locally(self):",
                "        state = self._make_state(None)",
                f"        state.return_stage_id = {preserved_return_stage!r}",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=state,",
                '            current_step_id="repair_and_resume",',
                "            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},",
                "            verifier_result=None,",
                "        )",
                '        self.assertEqual(result.step_id, "repair_and_resume")',
                '        self.assertEqual(result.branch_kind, "retry")',
                f"        self.assertEqual(state.return_stage_id, {preserved_return_stage!r})",
                "",
                "    def test_generated_repair_and_resume_blocked_after_threshold_requests_unblocking(self):",
                "        state = self._make_state({'attempt_counts': {'repair_and_resume': 2}})",
                f"        state.return_stage_id = {preserved_return_stage!r}",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=state,",
                '            current_step_id="repair_and_resume",',
                "            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},",
                "            verifier_result=None,",
                "        )",
                '        self.assertEqual(result.step_id, "request_unblocking_input")',
                '        self.assertEqual(result.branch_kind, "repair")',
                f"        self.assertEqual(state.return_stage_id, {preserved_return_stage!r})",
                "",
                "    def test_generated_blocked_repair_context_preserves_host_visible_summary(self):",
                "        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine",
                "",
                "        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))",
                f"        response = engine.start({workflow_spec['workflow_id']!r}, {{",
                '            "task_input": {"goal": "generated workflow regression"},',
                '            "context": {"repo_root": str(REPO_ROOT)},',
                '            "constraints": {"max_steps": 5},',
                "        })",
                "        run_id = response['run_id']",
                f"        response = engine.resume(run_id, {{",
                "            'run_id': run_id,",
                f"            'step_id': {resume_target!r},",
                "            'status': 'blocked',",
                "            'summary': 'Need external approval before continuing.',",
                "            'structured_output': {'blocked_reason': 'awaiting approval', 'missing_inputs': ['approval']},",
                "            'artifacts': [],",
                "            'error': None,",
                "            'tool_trace': [],",
                "            'raw_output': '',",
                "        })",
                "        self.assertEqual(response['kind'], 'yield')",
                "        self.assertEqual(response['retry_context']['category'], 'blocked')",
                "        self.assertEqual(response['retry_context']['summary'], 'awaiting approval')",
                "        self.assertEqual(response['retry_context']['requirements'], ['approval'])",
                "",
                "    def test_generated_max_steps_preserves_return_stage_for_repair(self):",
                "        state = self._make_state({'constraints': {'max_steps': 1}, 'attempt_counts': {}})",
                f"        expected_return_stage = {preserved_return_stage!r}",
                "        result = graphbuilder_runtime.run_transition_preview(",
                "            state=state,",
                "            current_step_id=expected_return_stage,",
                "            observation={'status': 'succeeded', 'summary': 'Workflow hit max steps.', 'structured_output': {}},",
                "            verifier_result={'passed': True, 'checks': []},",
                "        )",
                '        self.assertEqual(result.step_id, "repair_and_resume")',
                '        self.assertEqual(result.branch_kind, "repair")',
                "        self.assertEqual(state.return_stage_id, expected_return_stage)",
                "",
            ]
        )
    for key, sources in _overlapping_start_input_state_keys(workflow_spec):
        lines.extend(
            [
                f"    def test_generated_template_context_prefers_state_for_{key}(self):",
                "        state = self._make_state(None)",
                *[
                    f"        state.{source}[{key!r}] = 'stale-input-value'"
                    for source in sources
                ],
                f"        state.{key} = 'state-preferred-value'",
                "        context = graphbuilder_runtime._template_context_from_state(state)",
                f"        self.assertEqual(context[{key!r}], 'state-preferred-value')",
                "",
            ]
        )
    return lines


def _overlapping_start_input_state_keys(workflow_spec: dict[str, Any]) -> list[tuple[str, list[str]]]:
    start_input_schema = workflow_spec.get("start_input_schema") or {}
    source_to_keys: dict[str, set[str]] = {
        "task_input": set((start_input_schema.get("task_input") or {}).keys()),
        "context": set((start_input_schema.get("context") or {}).keys()),
        "constraints": set((start_input_schema.get("constraints") or {}).keys()),
    }
    promoted_state_keys = {update["state_key"] for update in _collect_state_updates(workflow_spec)}
    overlaps: list[tuple[str, list[str]]] = []
    for key in sorted(promoted_state_keys):
        sources = [source for source, keys in source_to_keys.items() if key in keys]
        if sources:
            overlaps.append((key, sources))
    return overlaps


def _constant_name(step_id: str) -> str:
    return step_id.upper()


def _python_literal(value: Any) -> str:
    return pformat(value, width=100, sort_dicts=False)


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_manifest(
    path: Path,
    *,
    workflow_id: str,
    description: str,
    start_input_schema: dict[str, Any],
    dependencies: list[Any],
) -> None:
    payload = {
        "schema_version": 1,
        "workflow_id": workflow_id,
        "description": description,
        "start_input_schema": start_input_schema,
        "dependencies": dependencies,
    }
    _write_json_atomic(path, payload)


def _write_workflow_lockfile(
    path: Path,
    *,
    workflow_id: str,
    installed: list[Any],
) -> None:
    payload = {
        "schema_version": 1,
        "workflow_id": workflow_id,
        "installed": installed,
    }
    _write_json_atomic(path, payload)


def _register_binding_entry(
    *,
    binding_path: Path,
    binding_payload: dict[str, Any],
    binding_entry: dict[str, Any],
    existing_index: int | None,
) -> None:
    workflows = binding_payload["workflows"]
    if existing_index is None:
        workflows.append(binding_entry)
    else:
        workflows[existing_index] = binding_entry
    _write_json_atomic(binding_path, binding_payload)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.exists():
        shutil.rmtree(path)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.migrate_legacy_custom_verifier_metadata:
            payload = migrate_legacy_custom_verifier_metadata(
                runtime_skill_root=args.runtime_skill_root,
                workflow_id=args.workflow_id,
            )
        else:
            payload = create_workflow_scaffold(
                runtime_skill_root=args.runtime_skill_root,
                workflow_id=args.workflow_id,
                flow_description=args.flow_description,
                force=args.force,
            )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a durable-workflow-runtime workflow scaffold"
    )
    parser.add_argument("--runtime-skill-root", default=str(DEFAULT_RUNTIME_SKILL_ROOT))
    parser.add_argument("--workflow-id")
    parser.add_argument(
        "--flow-description",
        help="Required when creating a new scaffold. Existing workflows regenerate from workflow-runtime/workflows/<workflow_id>/spec.json.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--migrate-legacy-custom-verifier-metadata",
        action="store_true",
        help="Scan existing workflows and backfill preservation metadata for legacy custom verifier helpers that predate spec_fingerprint comments.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
