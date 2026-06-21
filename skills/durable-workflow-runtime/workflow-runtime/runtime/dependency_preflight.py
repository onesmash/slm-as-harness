from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path


SUPPORTED_DEPENDENCY_TYPES = {"skill", "cli", "python_package", "mcp"}
SUPPORTED_SCOPES = {"project", "global", "either"}
PROJECT_SKILL_ROOTS = [".agents/skills", ".claude/skills", ".codex/skills"]
GLOBAL_SKILL_ROOTS = ["~/.agents/skills", "~/.claude/skills", "~/.codex/skills"]
GLOBAL_SKILL_RECURSIVE_ROOTS = [
    "~/.claude/skills",
    "~/.codex/plugins/cache/openai-curated",
    "~/.codex/plugins/cache/openai-bundled",
    "~/.codex/plugins/cache/openai-primary-runtime",
]
RECORDED_BY = "bridge.py preflight"


def build_preflight_result(
    *,
    repo_root: str | Path,
    runtime_root: str | Path,
    workflow_id: str,
) -> dict:
    repo_path = Path(repo_root).resolve()
    runtime_path = Path(runtime_root).resolve()
    manifest_path = runtime_path / "workflows" / workflow_id / "manifest.json"
    base_result = {
        "kind": "preflight_result",
        "workflow_id": workflow_id,
        "manifest_path": str(manifest_path),
        "status": "error",
        "message": "",
        "summary": {
            "total": 0,
            "available": 0,
            "missing_required": 0,
            "missing_optional": 0,
        },
        "dependencies": [],
        "install_plan": [],
    }

    if not manifest_path.exists():
        base_result["status"] = "invalid_manifest"
        base_result["message"] = f"missing workflow manifest: {manifest_path}"
        return base_result

    try:
        manifest = _load_manifest(manifest_path)
    except ValueError as exc:
        base_result["status"] = "invalid_manifest"
        base_result["message"] = str(exc)
        return base_result
    except OSError as exc:
        base_result["status"] = "error"
        base_result["message"] = str(exc)
        return base_result

    if manifest["workflow_id"] != workflow_id:
        base_result["status"] = "invalid_manifest"
        base_result["message"] = (
            f"workflow manifest workflow_id mismatch: expected {workflow_id}, "
            f"got {manifest['workflow_id']}"
        )
        return base_result

    try:
        _sync_manifest_start_input_schema(workflow_id, manifest)
        _validate_skill_dependencies_against_workflow_contract(workflow_id, manifest)
    except ValueError as exc:
        base_result["status"] = "invalid_manifest"
        base_result["message"] = str(exc)
        return base_result

    dependency_results: list[dict] = []
    install_plan: list[dict] = []
    installed_snapshot: list[dict] = []
    missing_required = 0
    missing_optional = 0
    manual_checks = 0

    for dependency in manifest["dependencies"]:
        result = _evaluate_dependency(repo_path, dependency)
        dependency_results.append(result)

        if result["status"] == "satisfied":
            installed_snapshot.append(
                {
                    "id": dependency["id"],
                    "type": dependency["type"],
                    "scope": result.get("resolved_scope", dependency["scope"]),
                    "source": dependency["source"],
                    "recorded_at": _iso_utc_now(),
                    "recorded_by": RECORDED_BY,
                }
            )
            continue

        if result["status"] == "manual_check_required":
            manual_checks += 1
        elif dependency["required"]:
            missing_required += 1
        else:
            missing_optional += 1

        install_plan.append(
            {
                "id": dependency["id"],
                "type": dependency["type"],
                "required": dependency["required"],
                "scope": dependency["scope"],
                "source": dependency["source"],
                "reason": result["reason"],
                "suggested_actions": _build_suggested_actions(dependency, result["reason"]),
            }
        )

    manifest["installed"] = installed_snapshot
    _write_manifest(manifest_path, manifest)

    base_result["summary"] = {
        "total": len(manifest["dependencies"]),
        "available": len(installed_snapshot),
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }
    base_result["dependencies"] = dependency_results
    base_result["install_plan"] = install_plan

    if missing_required > 0:
        base_result["status"] = "needs_install"
        base_result["message"] = "Required workflow dependencies are missing."
    elif missing_optional > 0 or manual_checks > 0:
        base_result["status"] = "ready_with_warnings"
        base_result["message"] = "Required dependencies are satisfied, but warnings remain."
    else:
        base_result["status"] = "ready"
        base_result["message"] = "Workflow dependencies are satisfied."

    return base_result


def should_block_start(preflight_result: dict) -> bool:
    return preflight_result.get("status") == "needs_install"


def is_invalid_manifest(preflight_result: dict) -> bool:
    return preflight_result.get("status") == "invalid_manifest"


def is_preflight_error(preflight_result: dict) -> bool:
    return preflight_result.get("status") == "error"


def _load_manifest(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid workflow manifest JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("workflow manifest must be a JSON object")

    schema_version = payload.get("schema_version")
    workflow_id = payload.get("workflow_id")
    description = payload.get("description")
    start_input_schema = payload.get("start_input_schema")
    dependencies = payload.get("dependencies")
    installed = payload.get("installed", [])

    if schema_version != 1:
        raise ValueError("workflow manifest schema_version must be 1")
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        raise ValueError("workflow manifest must define non-empty workflow_id")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("workflow manifest must define non-empty description")
    if not isinstance(dependencies, list):
        raise ValueError("workflow manifest field 'dependencies' must be a list")
    if not isinstance(installed, list):
        raise ValueError("workflow manifest field 'installed' must be a list")

    normalized_start_input_schema = None
    if start_input_schema is not None:
        normalized_start_input_schema = _normalize_start_input_schema(start_input_schema)

    normalized_dependencies = [_normalize_dependency(item) for item in dependencies]
    seen_dependency_keys: set[tuple[str, str]] = set()
    for dependency in normalized_dependencies:
        key = (dependency["id"], dependency["type"])
        if key in seen_dependency_keys:
            raise ValueError(
                f"duplicate dependency declaration: {dependency['id']} ({dependency['type']})"
            )
        seen_dependency_keys.add(key)
    normalized_installed = [_normalize_installed(item) for item in installed]
    normalized_manifest = {
        "schema_version": 1,
        "workflow_id": workflow_id.strip(),
        "description": description.strip(),
    }
    if normalized_start_input_schema is not None:
        normalized_manifest["start_input_schema"] = normalized_start_input_schema
    normalized_manifest["dependencies"] = normalized_dependencies
    normalized_manifest["installed"] = normalized_installed
    return normalized_manifest


def _normalize_start_input_schema(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("workflow manifest field 'start_input_schema' must be an object")
    normalized: dict[str, dict] = {}
    for field_name in ("task_input", "context", "constraints"):
        value = item.get(field_name)
        if not isinstance(value, dict):
            raise ValueError(f"start_input_schema.{field_name} must be an object")
        normalized[field_name] = value
    return normalized


def _normalize_dependency(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("each dependency must be an object")

    dependency_id = _require_non_empty_string(item.get("id"), "dependency.id")
    dependency_type = _require_non_empty_string(item.get("type"), "dependency.type")
    required = item.get("required")
    scope = _require_non_empty_string(item.get("scope"), "dependency.scope")
    source = _require_non_empty_string(item.get("source"), "dependency.source")
    purpose = _require_non_empty_string(item.get("purpose"), "dependency.purpose")

    if dependency_type not in SUPPORTED_DEPENDENCY_TYPES:
        raise ValueError(f"unsupported dependency type: {dependency_type}")
    if not isinstance(required, bool):
        raise ValueError(f"dependency.required must be boolean for {dependency_id}")
    if scope not in SUPPORTED_SCOPES:
        raise ValueError(f"unsupported dependency scope: {scope}")
    if dependency_type in {"cli", "python_package"} and scope == "project":
        raise ValueError(
            f"dependency {dependency_id} of type {dependency_type} does not support project scope"
        )

    normalized = {
        "id": dependency_id,
        "type": dependency_type,
        "required": required,
        "scope": scope,
        "source": source,
        "purpose": purpose,
    }
    install_command = item.get("install_command")
    if install_command is not None:
        normalized["install_command"] = _require_non_empty_string(
            install_command,
            "dependency.install_command",
        )
    if dependency_type == "cli":
        normalized["command"] = _require_non_empty_string(item.get("command"), "dependency.command")
    if dependency_type == "python_package":
        normalized["module"] = _require_non_empty_string(item.get("module"), "dependency.module")
    return normalized


def _normalize_installed(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("each installed entry must be an object")
    return {
        "id": _require_non_empty_string(item.get("id"), "installed.id"),
        "type": _require_non_empty_string(item.get("type"), "installed.type"),
        "scope": _require_non_empty_string(item.get("scope"), "installed.scope"),
        "source": _require_non_empty_string(item.get("source"), "installed.source"),
        "recorded_at": _require_non_empty_string(item.get("recorded_at"), "installed.recorded_at"),
        "recorded_by": _require_non_empty_string(item.get("recorded_by"), "installed.recorded_by"),
    }


def _validate_skill_dependencies_against_workflow_contract(workflow_id: str, manifest: dict) -> None:
    from runtime.module_loader import load_workflow_modules

    workflow_modules = load_workflow_modules(workflow_id)
    contract_module = workflow_modules["contract"]
    declared_skill_ids = {
        dependency["id"]
        for dependency in manifest["dependencies"]
        if dependency["type"] in {"skill", "mcp"}
    }
    missing_skills_by_stage: dict[str, list[str]] = {}

    for step_id in contract_module.list_step_contract_ids():
        step_contract = contract_module.get_step_contract(step_id)
        missing_skill_ids = sorted(
            {
                route.skill
                for route in step_contract.skill_routing
                if route.skill not in declared_skill_ids
            }
        )
        if missing_skill_ids:
            missing_skills_by_stage[step_id] = missing_skill_ids

    if not missing_skills_by_stage:
        return

    missing_parts = [
        f"{step_id}: {', '.join(skill_ids)}"
        for step_id, skill_ids in sorted(missing_skills_by_stage.items())
    ]
    raise ValueError(
        "workflow manifest is missing skill dependencies required by stage skill_routing: "
        + "; ".join(missing_parts)
    )


def _sync_manifest_start_input_schema(workflow_id: str, manifest: dict) -> None:
    from runtime.module_loader import load_workflow_modules

    workflow_modules = load_workflow_modules(workflow_id)
    input_contract = workflow_modules["contract"].WORKFLOW_INPUT_CONTRACT
    expected_schema = input_contract.to_start_input_schema()
    current_schema = manifest.get("start_input_schema")
    if current_schema is None:
        manifest["start_input_schema"] = expected_schema
        return
    if current_schema != expected_schema:
        raise ValueError(
            "workflow manifest start_input_schema does not match "
            f"WORKFLOW_INPUT_CONTRACT for {workflow_id}"
        )


def _evaluate_dependency(repo_root: Path, dependency: dict) -> dict:
    dependency_type = dependency["type"]
    if dependency_type == "skill":
        return _evaluate_skill_dependency(repo_root, dependency)
    if dependency_type == "cli":
        return _evaluate_cli_dependency(dependency)
    if dependency_type == "python_package":
        return _evaluate_python_package_dependency(dependency)
    return {
        "id": dependency["id"],
        "type": dependency["type"],
        "required": dependency["required"],
        "scope": dependency["scope"],
        "source": dependency["source"],
        "purpose": dependency["purpose"],
        "status": "manual_check_required",
        "reason": "MCP dependencies require manual verification in v1.",
    }


def _evaluate_skill_dependency(repo_root: Path, dependency: dict) -> dict:
    project_path = _find_project_skill(repo_root, dependency["id"])
    global_path = _find_global_skill(dependency["id"])
    scope = dependency["scope"]

    status = "missing"
    reason = f"skill `{dependency['id']}` was not found."
    resolved_scope = None
    location = None

    if scope == "project":
        if project_path is not None:
            status = "satisfied"
            reason = f"project skill `{dependency['id']}` is available."
            resolved_scope = "project"
            location = str(project_path)
        elif global_path is not None:
            status = "scope_mismatch"
            reason = f"skill `{dependency['id']}` is available globally but project scope is required."
    elif scope == "global":
        if global_path is not None:
            status = "satisfied"
            reason = f"global skill `{dependency['id']}` is available."
            resolved_scope = "global"
            location = str(global_path)
        elif project_path is not None:
            status = "scope_mismatch"
            reason = f"skill `{dependency['id']}` is available in the project, but global scope is required."
    else:
        if project_path is not None:
            status = "satisfied"
            reason = f"project skill `{dependency['id']}` is available."
            resolved_scope = "project"
            location = str(project_path)
        elif global_path is not None:
            status = "satisfied"
            reason = f"global skill `{dependency['id']}` is available."
            resolved_scope = "global"
            location = str(global_path)

    result = _base_dependency_result(dependency, status=status, reason=reason)
    if resolved_scope is not None:
        result["resolved_scope"] = resolved_scope
    if location is not None:
        result["location"] = location
    return result


def _evaluate_cli_dependency(dependency: dict) -> dict:
    command = dependency["command"]
    location = shutil.which(command)
    if location is None:
        return _base_dependency_result(
            dependency,
            status="missing",
            reason=f"command `{command}` was not found on PATH.",
        )
    result = _base_dependency_result(
        dependency,
        status="satisfied",
        reason=f"command `{command}` is available on PATH.",
    )
    result["resolved_scope"] = "global"
    result["location"] = location
    return result


def _evaluate_python_package_dependency(dependency: dict) -> dict:
    module_name = dependency["module"]
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return _base_dependency_result(
            dependency,
            status="missing",
            reason=f"python module `{module_name}` could not be imported.",
        )
    result = _base_dependency_result(
        dependency,
        status="satisfied",
        reason=f"python module `{module_name}` can be imported.",
    )
    result["resolved_scope"] = "global"
    result["location"] = str(getattr(spec, "origin", "") or module_name)
    return result


def _base_dependency_result(dependency: dict, *, status: str, reason: str) -> dict:
    return {
        "id": dependency["id"],
        "type": dependency["type"],
        "required": dependency["required"],
        "scope": dependency["scope"],
        "source": dependency["source"],
        "purpose": dependency["purpose"],
        "status": status,
        "reason": reason,
    }


def _build_suggested_actions(dependency: dict, reason: str) -> list[str]:
    actions = [f"Install or make available `{dependency['id']}` from `{dependency['source']}`."]
    install_command = dependency.get("install_command")
    if isinstance(install_command, str) and install_command.strip():
        actions.append(f"Run `{install_command}`.")
    if dependency["type"] == "skill":
        if dependency["scope"] == "project":
            actions.append(
                f"Place the skill under `.agents/skills/{dependency['id']}/`, `.claude/skills/{dependency['id']}/`, or `.codex/skills/{dependency['id']}/`."
            )
        elif dependency["scope"] == "global":
            actions.append("Install the skill into a global skill root.")
        else:
            actions.append("Install the skill into either a project or global skill root.")
    elif dependency["type"] == "cli":
        actions.append(f"Ensure the command `{dependency['command']}` is available on PATH.")
    elif dependency["type"] == "python_package":
        actions.append(
            f"Install the package that provides Python module `{dependency['module']}` into the bridge Python environment."
        )
    else:
        actions.append("Verify MCP availability manually in the host environment.")
    actions.append(reason)
    actions.append("Restart the session if the host does not hot-load newly installed dependencies.")
    actions.append("Run `start` again after installation.")
    return actions


def _find_project_skill(repo_root: Path, skill_name: str) -> Path | None:
    candidate_names = _skill_name_candidates(skill_name)
    for relative_root in PROJECT_SKILL_ROOTS:
        root_path = repo_root / relative_root
        for candidate_name in candidate_names:
            candidate = root_path / candidate_name / "SKILL.md"
            if candidate.is_file():
                return candidate
        matched = _find_skill_by_frontmatter_name(root_path, candidate_names)
        if matched is not None:
            return matched
    return None


def _find_global_skill(skill_name: str) -> Path | None:
    candidate_names = _skill_name_candidates(skill_name)

    for root in GLOBAL_SKILL_ROOTS:
        root_path = Path(root).expanduser().resolve()
        for candidate_name in candidate_names:
            candidate = root_path / candidate_name / "SKILL.md"
            if candidate.is_file():
                return candidate
        matched = _find_skill_by_frontmatter_name(root_path, candidate_names)
        if matched is not None:
            return matched

    for root in GLOBAL_SKILL_RECURSIVE_ROOTS:
        root_path = Path(root).expanduser().resolve()
        if not root_path.exists():
            continue
        for candidate_name in candidate_names:
            matches = sorted(root_path.rglob(f"{candidate_name}/SKILL.md"))
            if matches:
                return matches[0]
        matched = _find_skill_by_frontmatter_name(root_path, candidate_names)
        if matched is not None:
            return matched
    return None


def _skill_name_candidates(skill_name: str) -> list[str]:
    names = [skill_name]
    if ":" in skill_name:
        names.append(skill_name.split(":", 1)[1])
    deduped: list[str] = []
    for name in names:
        if name not in deduped:
            deduped.append(name)
    return deduped


def _find_skill_by_frontmatter_name(root_path: Path, candidate_names: list[str]) -> Path | None:
    if not root_path.exists():
        return None
    wanted_names = set(candidate_names)
    for candidate in sorted(root_path.rglob("SKILL.md")):
        frontmatter_name = _read_skill_frontmatter_name(candidate)
        if frontmatter_name in wanted_names:
            return candidate
    return None


def _read_skill_frontmatter_name(skill_path: Path) -> str | None:
    try:
        lines = skill_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:40]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip()
            return value or None
    return None


def _write_manifest(path: Path, payload: dict) -> None:
    ordered_payload = {
        "schema_version": payload["schema_version"],
        "workflow_id": payload["workflow_id"],
        "description": payload["description"],
    }
    if "start_input_schema" in payload:
        ordered_payload["start_input_schema"] = payload["start_input_schema"]
    ordered_payload["dependencies"] = payload["dependencies"]
    ordered_payload["installed"] = payload["installed"]
    path.write_text(
        json.dumps(ordered_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


def _iso_utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
