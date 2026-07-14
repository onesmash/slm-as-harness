from __future__ import annotations

from pathlib import Path

from workflows.common.contracts import VerifierResult, make_verifier_result
from workflows.common.policies import condition_matches

def verify_diagnose_performance(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'baseline_metrics': 'string',
 'bottleneck_summary': 'string',
 'performance_report_path': 'string',
 'ready_for_brainstorm': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'baseline_metrics',
  'operator': 'truthy',
  'value': None,
  'message': 'performance diagnosis must record baseline metrics'},
 {'output_key': 'bottleneck_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'performance diagnosis must identify a bottleneck'},
 {'output_key': 'performance_report_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'performance diagnosis must return an existing report path'},
 {'output_key': 'ready_for_brainstorm',
  'operator': 'is_true',
  'value': None,
  'message': 'performance diagnosis must declare brainstorming readiness'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_brainstorm_optimization(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'optimization_hypotheses': 'string[]',
 'success_criteria': 'string',
 'brainstorm_artifact_path': 'string',
 'ready_for_research': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'optimization_hypotheses',
  'operator': 'non_empty',
  'value': None,
  'message': 'brainstorming must record at least one optimization hypothesis'},
 {'output_key': 'success_criteria',
  'operator': 'truthy',
  'value': None,
  'message': 'brainstorming must state measurable success criteria'},
 {'output_key': 'brainstorm_artifact_path',
  'operator': 'truthy',
  'value': None,
  'message': 'brainstorming must return an ideation artifact path'},
 {'output_key': 'ready_for_research',
  'operator': 'is_true',
  'value': None,
  'message': 'brainstorming must be ready for research'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_research_optimization(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'research_brief_path': 'string',
 'evidence_summary': 'string',
 'open_risks': 'string[]',
 'ready_for_plan': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'research_brief_path',
  'operator': 'truthy',
  'value': None,
  'message': 'research must return a brief path'},
 {'output_key': 'evidence_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'research must return an evidence summary'},
 {'output_key': 'ready_for_plan',
  'operator': 'is_true',
  'value': None,
  'message': 'research must declare plan readiness'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_plan_optimization(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'implementation_plan_path': 'string',
 'planned_change_summary': 'string',
 'verification_plan': 'string[]',
 'ready_for_implementation': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'implementation_plan_path',
  'operator': 'truthy',
  'value': None,
  'message': 'planning must return an implementation plan path'},
 {'output_key': 'verification_plan',
  'operator': 'non_empty',
  'value': None,
  'message': 'planning must name verification commands'},
 {'output_key': 'ready_for_implementation',
  'operator': 'is_true',
  'value': None,
  'message': 'planning must declare implementation readiness'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_implement_optimization(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'implementation_summary': 'string',
 'changed_paths': 'string[]',
 'submission_test_command': 'string',
 'submission_test_output': 'string',
 'submission_test_exit_code': 'integer',
 'submission_tests_passed': 'boolean',
 'ready_for_review': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'implementation_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'implementation must report its change'},
 {'output_key': 'submission_test_command',
  'operator': 'equals',
  'value': 'python tests/submission_tests.py',
  'message': 'implementation must report the required submission-test command'},
 {'output_key': 'submission_test_exit_code',
  'operator': 'equals',
  'value': 0,
  'message': 'the required submission-test command must exit with status 0'},
 {'output_key': 'submission_tests_passed',
  'operator': 'is_true',
  'value': None,
  'message': 'python tests/submission_tests.py must pass before review'},
 {'output_key': 'ready_for_review',
  'operator': 'is_true',
  'value': None,
  'message': 'implementation must be ready for review'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_implement_optimization(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_review_optimization(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'review_summary': 'string', 'review_findings': 'string[]', 'ready_for_knowledge_base': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'review_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'review must provide a summary'},
 {'output_key': 'ready_for_knowledge_base',
  'operator': 'is_true',
  'value': None,
  'message': 'review must approve knowledge-base maintenance'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_update_optimization_knowledge_base(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'knowledge_base_update_summary': 'string',
 'knowledge_base_artifacts': 'string[]',
 'continue_optimization': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'knowledge_base_update_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'knowledge-base maintenance must report its update'},
 {'output_key': 'knowledge_base_artifacts',
  'operator': 'non_empty',
  'value': None,
  'message': 'knowledge-base maintenance must record durable artifacts'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_capture_blocked_cycle_knowledge(
    *,
    repo_root: str,
    run_id: str,
    step_id: str,
    observation: dict,
    state: dict | None = None,
) -> VerifierResult:
    result = _verify_structured_output_schema(
        run_id=run_id,
        step_id=step_id,
        required_schema={'knowledge_base_update_summary': 'string',
 'knowledge_base_artifacts': 'string[]',
 'next_cycle_lead': 'string'},
        optional_schema={},
        verifier_rules=[{'output_key': 'knowledge_base_update_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'blocked-cycle capture must summarize the knowledge-base record'},
 {'output_key': 'knowledge_base_artifacts',
  'operator': 'non_empty',
  'value': None,
  'message': 'blocked-cycle capture must record at least one knowledge-base artifact'},
 {'output_key': 'next_cycle_lead',
  'operator': 'truthy',
  'value': None,
  'message': 'blocked-cycle capture must identify a next-cycle lead'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def _run_custom_verifier_requirements_implement_optimization(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_implement_optimization_enforce_submission_constraints(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: implement_optimization
# custom_verifier_requirement_id: enforce_submission_constraints
# template_version: 1
# spec_fingerprint: 61435df281a47d3af1e7dc4edbb28ca39d80b5831158f654373564da54c81a87
# implementation_version: none
def _custom_verifier_requirement_implement_optimization_enforce_submission_constraints(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: Verify directly that tests/ is unchanged from origin/main, problem.py assigns N_CORES = 1, and python tests/submission_tests.py succeeds from repo_root.
Signals: changed_paths, submission_test_command, submission_test_exit_code, submission_tests_passed
Implementation surfaces: verifiers.py, tests/test_workflow.py
Hint pseudocode:
- Reject changed_paths containing tests or tests/.
- Run git diff --quiet origin/main -- tests/.
- Parse problem.py and require literal N_CORES = 1.
- Run python tests/submission_tests.py in repo_root and require exit code 0.
Test intent:
- Reject a changed tests/ path.
- Reject N_CORES other than 1.
- Reject a failing submission command."""
    import ast
    import subprocess

    _ = state
    changed_paths = output.get("changed_paths")
    if not isinstance(changed_paths, list):
        return "changed_paths must be a list"
    if any(str(path).replace("\\", "/").strip("/") == "tests" or str(path).replace("\\", "/").strip("/").startswith("tests/") for path in changed_paths):
        return "changed_paths must not include tests/"
    repo = Path(repo_root)
    try:
        diff = subprocess.run(
            ["git", "diff", "--quiet", "origin/main", "--", "tests/"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return f"cannot check tests/ diff: {exc}"
    if diff.returncode != 0:
        return "tests/ differs from origin/main"
    try:
        module = ast.parse((repo / "problem.py").read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return f"cannot inspect problem.py: {exc}"
    assignments = [node for node in ast.walk(module) if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "N_CORES" for target in node.targets)]
    module_assignments = [node for node in module.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "N_CORES" for target in node.targets)]
    if len(assignments) != 1 or len(module_assignments) != 1 or not isinstance(module_assignments[0].value, ast.Constant) or module_assignments[0].value.value != 1:
        return "problem.py must assign N_CORES = 1"
    run = subprocess.run(
        ["python", "tests/submission_tests.py"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        return "python tests/submission_tests.py did not pass"
    return None

def _verify_structured_output_schema(
    *,
    run_id: str,
    step_id: str,
    required_schema: dict[str, str],
    optional_schema: dict[str, str],
    verifier_rules: list[dict],
    verifier_templates: list[dict],
    observation: dict,
    repo_root: str,
    state: dict | None,
) -> VerifierResult:
    output = observation.get("structured_output")
    if output is None:
        output = {}
    if not isinstance(output, dict):
        return _fail("structured_output must be an object", run_id, step_id, state)
    missing = [key for key in required_schema if key not in output]
    if missing:
        return _fail(f"missing required structured_output keys: {missing}", run_id, step_id, state)
    schema_errors = []
    for key, schema_type in required_schema.items():
        message = _schema_type_error(key, output.get(key), schema_type, required=True)
        if message:
            schema_errors.append(message)
    for key, schema_type in optional_schema.items():
        if key in output:
            message = _schema_type_error(key, output.get(key), schema_type, required=False)
            if message:
                schema_errors.append(message)
    if schema_errors:
        return _fail("; ".join(schema_errors), run_id, step_id, state)
    rule_errors = []
    for rule in verifier_rules:
        message = _verifier_rule_error(rule, output, repo_root)
        if message:
            rule_errors.append(message)
    if rule_errors:
        return _fail("; ".join(rule_errors), run_id, step_id, state)
    template_errors = []
    for template in verifier_templates:
        message = _verifier_template_error(template, output, repo_root)
        if message:
            template_errors.append(message)
    if template_errors:
        return _fail("; ".join(template_errors), run_id, step_id, state)
    return make_verifier_result(
        passed=True,
        message="structured_output schema, verifier rules, and verifier templates are satisfied",
        details={
            "run_id": run_id,
            "step_id": step_id,
            "checked_required_keys": sorted(required_schema),
            "checked_optional_keys": sorted(optional_schema),
        },
    )


def _schema_type_error(
    key: str,
    value: object,
    schema_type: str,
    *,
    required: bool,
) -> str | None:
    normalized = schema_type.rstrip("?")
    if value is None and not required:
        return None
    if normalized == "string":
        if not isinstance(value, str):
            return f"{key} must be a string"
        if required and not value.strip():
            return f"{key} must be a non-empty string"
        return None
    if normalized == "boolean":
        if not isinstance(value, bool):
            return f"{key} must be a boolean"
        return None
    if normalized == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return f"{key} must be an integer"
        return None
    if normalized == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"{key} must be a number"
        return None
    if normalized == "object":
        if not isinstance(value, dict):
            return f"{key} must be an object"
        return None
    if normalized.endswith("[]"):
        if not isinstance(value, list):
            return f"{key} must be a list"
        item_type = normalized[:-2]
        for index, item in enumerate(value):
            message = _schema_type_error(f"{key}[{index}]", item, item_type, required=False)
            if message:
                return message
        return None
    return None


def _verifier_rule_error(rule: dict, output: dict, repo_root: str) -> str | None:
    key = str(rule.get("output_key") or "")
    operator = str(rule.get("operator") or "")
    expected = rule.get("value")
    message = str(rule.get("message") or f"{key} failed verifier rule: {operator}")
    actual = output.get(key)
    if operator == "one_of":
        allowed = expected if isinstance(expected, list) else []
        return None if actual in allowed else message
    if operator == "path_exists":
        if not isinstance(actual, str) or not actual.strip():
            return message
        candidate = Path(actual)
        if not candidate.is_absolute():
            candidate = Path(repo_root) / candidate
        return None if candidate.exists() else message
    return None if condition_matches(actual, operator, expected) else message


def _verifier_template_error(template: dict, output: dict, repo_root: str) -> str | None:
    template_name = str(template.get("template") or "")
    message = str(template.get("message") or f"{template.get('id') or template_name} failed")
    key = str(template.get("output_key") or "")
    actual = output.get(key)
    if template_name == "conditional_equals":
        return _conditional_equals_error(actual, output, template, message)
    if template_name == "conditional_required":
        return _conditional_required_error(output, template, message)
    if template_name == "min_count":
        return _min_count_error(actual, template, message)
    if template_name == "required_set_members":
        return _required_set_members_error(actual, template, message)
    if template_name == "repo_path_policy":
        return _repo_path_policy_error(actual, template, repo_root, message)
    if template_name == "artifact_file_contains_sections":
        return _artifact_file_contains_sections_error(actual, template, repo_root, message)
    return message


def _conditional_required_error(output: dict, template: dict, message: str) -> str | None:
    when = template.get("when") or {}
    if not isinstance(when, dict):
        return message
    when_key = str(when.get("output_key") or "")
    if not condition_matches(output.get(when_key), str(when.get("operator") or ""), when.get("value")):
        return None
    required_key = str(template.get("required_key") or "")
    return None if output.get(required_key) else message


def _conditional_equals_error(actual, output: dict, template: dict, message: str) -> str | None:
    when = template.get("when") or {}
    if not isinstance(when, dict):
        return message
    when_key = str(when.get("output_key") or "")
    if not condition_matches(output.get(when_key), str(when.get("operator") or ""), when.get("value")):
        return None
    return None if actual == template.get("expected_value") else message


def _min_count_error(actual, template: dict, message: str) -> str | None:
    if not isinstance(actual, list):
        return message
    min_count = template.get("min_count")
    if not isinstance(min_count, int) or isinstance(min_count, bool):
        return message
    return None if len(actual) >= min_count else message


def _required_set_members_error(actual, template: dict, message: str) -> str | None:
    if not isinstance(actual, list):
        return message
    required = template.get("required_members")
    if not isinstance(required, list):
        return message
    case_sensitive = bool(template.get("case_sensitive", False))
    if case_sensitive:
        normalized = {str(item).strip() for item in actual if str(item).strip()}
        required_members = {str(item).strip() for item in required if str(item).strip()}
    else:
        normalized = {str(item).strip().lower() for item in actual if str(item).strip()}
        required_members = {str(item).strip().lower() for item in required if str(item).strip()}
    missing = sorted(required_members - normalized)
    return None if not missing else f"{message}: missing members {missing}"


def _repo_path_policy_error(actual, template: dict, repo_root: str, message: str) -> str | None:
    if not isinstance(actual, str) or not actual.strip():
        return message
    repo = Path(repo_root).resolve()
    candidate = Path(actual)
    if not candidate.is_absolute():
        candidate = repo / candidate
    try:
        relative_path = candidate.resolve().relative_to(repo)
    except ValueError:
        return message
    relative_posix = relative_path.as_posix()
    required_prefix = str(template.get("required_prefix") or "")
    if required_prefix and not relative_posix.startswith(required_prefix):
        return message
    forbidden_prefixes = [str(prefix) for prefix in template.get("forbidden_prefixes") or []]
    if any(relative_posix.startswith(prefix) for prefix in forbidden_prefixes):
        return message
    suffix = template.get("required_suffix")
    if isinstance(suffix, str) and suffix and not relative_posix.endswith(suffix):
        return message
    return None


def _artifact_file_contains_sections_error(actual, template: dict, repo_root: str, message: str) -> str | None:
    if not isinstance(actual, str) or not actual.strip():
        return message
    candidate = Path(actual)
    if not candidate.is_absolute():
        candidate = Path(repo_root) / candidate
    try:
        text = candidate.read_text(encoding="utf-8")
    except OSError:
        return message
    sections = [str(section) for section in template.get("sections") or []]
    missing = [section for section in sections if section not in text]
    return None if not missing else f"{message}: missing sections {missing}"


def _meaningful_entries(value) -> list[str]:
    if not isinstance(value, list):
        return []
    entries: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            entries.append(text)
    return entries


def _path_has_prefix(path: Path, prefix: Path) -> bool:
    try:
        normalized_path = path.as_posix().strip("/")
        normalized_prefix = prefix.as_posix().strip("/")
    except Exception:
        return False
    return normalized_path == normalized_prefix or normalized_path.startswith(normalized_prefix + "/")


def _extract_single_review_perspective(text: str) -> str | None:
    lowered = str(text).lower()
    matched = [label for label in ("development", "design", "testing") if label in lowered]
    if len(matched) != 1:
        return None
    return matched[0]


def _looks_like_visual_evidence(text: str) -> bool:
    lowered = str(text).lower()
    markers = (
        "visual diff",
        "screenshot diff",
        "screenshot comparison",
        "design comparison",
        "figma",
        "pixel diff",
        "visual qa",
        "mock comparison",
    )
    return any(marker in lowered for marker in markers)


def _has_explicit_severity_prefix(text: str) -> bool:
    return _extract_severity_prefix(text) is not None


def _extract_severity_prefix(text: str) -> str | None:
    normalized = str(text).strip().lower()
    for prefix in ("critical", "blocker", "p0", "important", "high", "p1", "major", "medium", "minor", "low"):
        if normalized.startswith(prefix + ":"):
            return prefix
    return None


def _severity_rank(severity: str) -> int:
    ranks = {
        "critical": 0,
        "blocker": 0,
        "p0": 0,
        "important": 1,
        "high": 1,
        "p1": 1,
        "major": 2,
        "medium": 3,
        "minor": 4,
        "low": 5,
    }
    return ranks.get(severity, 999)


def _fail(message: str, run_id: str, step_id: str, state: dict | None) -> VerifierResult:
    return make_verifier_result(
        passed=False,
        message=message,
        details={"run_id": run_id, "step_id": step_id, "state": state or {}},
    )
