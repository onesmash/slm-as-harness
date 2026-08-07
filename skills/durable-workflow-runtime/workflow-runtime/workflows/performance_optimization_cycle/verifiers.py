from __future__ import annotations

import ast
import os
import re
import subprocess
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
  'operator': 'path_exists',
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
 'planned_change_summary': 'string',
 'verification_plan': 'string[]',
 'ready_for_implementation': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'research_brief_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'research must return a brief path'},
 {'output_key': 'evidence_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'research must return an evidence summary'},
 {'output_key': 'planned_change_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'research must define the implementation-ready change'},
 {'output_key': 'verification_plan',
  'operator': 'non_empty',
  'value': None,
  'message': 'research must name verification commands'},
 {'output_key': 'ready_for_implementation',
  'operator': 'is_true',
  'value': None,
  'message': 'research must declare implementation readiness'}],
        verifier_templates=[{'id': 'research_brief_contains_markdown_heading',
  'template': 'artifact_file_contains_sections',
  'output_key': 'research_brief_path',
  'message': 'research must return a non-empty Markdown brief artifact',
  'sections': ['#']}],
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
 'planned_change_summary': 'string',
 'verification_plan': 'string[]',
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
 {'output_key': 'planned_change_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'implementation must define the smallest testable change'},
 {'output_key': 'verification_plan',
  'operator': 'non_empty',
  'value': None,
  'message': 'implementation must name verification commands'},
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
        verifier_templates=[{'id': 'review_findings_are_resolved_before_approval',
  'template': 'no_unresolved_findings',
  'output_key': 'review_findings',
  'message': 'review cannot approve knowledge-base maintenance with unresolved high-severity findings',
  'when': {'output_key': 'ready_for_knowledge_base',
   'operator': 'is_true',
   'value': None},
  'unresolved_terms': ['critical', 'blocker', 'p0', 'high', 'p1'],
  'resolved_terms': ['resolved', 'fixed', 'closed']}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    unresolved = [
        finding for finding in output.get("review_findings") or []
        if isinstance(finding, str)
        and re.search(r"\b(critical|blocker|p0|high|p1)\b", finding, re.IGNORECASE)
        and not re.search(r"\b(resolved|fixed|closed)\b", finding, re.IGNORECASE)
    ]
    if output.get("ready_for_knowledge_base") is True and unresolved:
        return _fail(
            "review cannot approve knowledge-base maintenance with unresolved high-severity findings",
            run_id,
            step_id,
            state,
        )
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
        verifier_templates=[{'id': 'knowledge_base_artifacts_are_safe_markdown',
  'template': 'artifact_list_policy',
  'output_key': 'knowledge_base_artifacts',
  'message': 'knowledge-base maintenance must record existing non-empty Markdown knowledge-base artifacts',
  'required_prefix': 'knowledge-base/',
  'allowed_suffixes': ['.md', '.markdown', '.txt'],
  'require_non_empty_content': True}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    artifact_error = _artifact_list_error(
        output=(observation.get("structured_output") or {}).get("knowledge_base_artifacts"),
        repo_root=repo_root,
        message="knowledge-base maintenance must record existing repository-relative regular-file artifacts",
    )
    if artifact_error:
        return _fail(artifact_error, run_id, step_id, state)
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
        verifier_templates=[{'id': 'blocked_cycle_artifacts_are_safe_markdown',
  'template': 'artifact_list_policy',
  'output_key': 'knowledge_base_artifacts',
  'message': 'blocked-cycle capture must record existing non-empty Markdown knowledge-base artifacts',
  'required_prefix': 'knowledge-base/',
  'allowed_suffixes': ['.md', '.markdown', '.txt'],
  'require_non_empty_content': True}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    artifact_error = _artifact_list_error(
        output=(observation.get("structured_output") or {}).get("knowledge_base_artifacts"),
        repo_root=repo_root,
        message="blocked-cycle capture must record existing repository-relative regular-file artifacts",
    )
    if artifact_error:
        return _fail(artifact_error, run_id, step_id, state)
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
# spec_fingerprint: 6ffa8e04f3564aecd069562427480a79b33d277e317d9daa2cd959b2cd947a60
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

Requirement: Verify directly that changed_paths contains only non-empty implementation paths, every requested path is changed from origin/main, tests/ is unchanged, problem.py is a safe regular file containing exactly one module-level literal N_CORES = 1 assignment (not bool, float, or nested), and python tests/submission_tests.py succeeds from repo_root.
Signals: changed_paths, submission_test_command, submission_test_exit_code, submission_tests_passed
Implementation surfaces: verifiers.py, tests/test_workflow.py
Hint pseudocode:
- Reject empty, absolute, traversal-containing, or tests/ changed_paths; require every requested path in the origin/main diff.
- Run git diff --quiet origin/main -- tests/.
- Read problem.py without following a final symlink, parse only module-level assignments, and require one exact integer literal N_CORES = 1.
- Run python tests/submission_tests.py in repo_root and require exit code 0.
Test intent:
- Reject a changed tests/ path.
- Reject a changed implementation path omitted from changed_paths.
- Reject N_CORES other than 1.
- Reject a failing submission command."""
    _ = state
    changed_paths = output.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        return "changed_paths must contain at least one implementation path"
    normalized_paths = []
    for path in changed_paths:
        if not isinstance(path, str) or not path.strip():
            return "changed_paths must contain non-empty relative paths"
        normalized = path
        path_parts = normalized.split("/")
        if (
            normalized != normalized.strip()
            or "\\" in normalized
            or normalized.startswith("/")
            or re.match(r"^[A-Za-z]:/", normalized)
            or any(part in ("", ".", "..") for part in path_parts)
        ):
            return "changed_paths must contain safe repository-relative paths"
        if any(ord(char) < 32 for char in normalized):
            return "changed_paths must not contain control characters"
        normalized_paths.append(normalized)
    if len(normalized_paths) != len(set(normalized_paths)):
        return "changed_paths must not contain duplicate paths"
    if any(path.split("/", 1)[0] == "tests" for path in normalized_paths):
        return "changed_paths must not modify tests/"

    repo = Path(repo_root)
    diff = subprocess.run(
        ["git", "diff", "--quiet", "origin/main", "--", "tests/"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if diff.returncode != 0:
        return "tests/ differs from origin/main"
    changed_diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "--"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if changed_diff.returncode != 0:
        return "could not determine changed implementation paths from origin/main"
    actual_diff_paths = {
        line.replace("\\", "/").strip()
        for line in changed_diff.stdout.splitlines()
        if line.strip()
    }
    missing_paths = sorted(set(normalized_paths) - actual_diff_paths)
    if missing_paths:
        return f"changed_paths must identify every requested path changed from origin/main: {missing_paths}"
    undeclared_paths = sorted(actual_diff_paths - set(normalized_paths))
    if undeclared_paths:
        return f"changed_paths must declare every path changed from origin/main: {undeclared_paths}"

    problem_path = _safe_repo_file(repo_root, "problem.py")
    if problem_path is None:
        return "problem.py is required to verify N_CORES = 1"
    try:
        problem_text = _read_safe_repo_text(repo_root, "problem.py")
        if problem_text is None:
            return "problem.py could not be read as UTF-8"
        tree = ast.parse(problem_text, filename=str(problem_path))
    except (SyntaxError, UnicodeError) as exc:
        return f"problem.py could not be parsed: {exc}"
    n_cores_values = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "N_CORES":
                    n_cores_values.append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "N_CORES":
            n_cores_values.append(node.value)
    if len(n_cores_values) != 1 or not (
        isinstance(n_cores_values[0], ast.Constant)
        and type(n_cores_values[0].value) is int
        and n_cores_values[0].value == 1
    ):
        return "problem.py must contain exactly one literal assignment N_CORES = 1"

    try:
        submission = subprocess.run(
            ["python", "tests/submission_tests.py"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"submission tests could not run: {exc}"
    if submission.returncode != 0:
        return "python tests/submission_tests.py failed"
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
        message = _verifier_template_error(template, output, repo_root, state)
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
        return None if _safe_repo_file(repo_root, actual) is not None else message
    return None if condition_matches(actual, operator, expected) else message


def _verifier_template_error(
    template: dict,
    output: dict,
    repo_root: str,
    state: dict | None,
) -> str | None:
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
    if template_name == "min_count_from_constraint":
        return _min_count_from_constraint_error(actual, template, state, message)
    if template_name == "required_set_members":
        return _required_set_members_error(actual, template, message)
    if template_name == "artifact_list_policy":
        return _artifact_list_policy_error(actual, template, repo_root, message)
    if template_name == "no_unresolved_findings":
        return _no_unresolved_findings_error(output, template, message)
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


def _artifact_list_policy_error(actual, template: dict, repo_root: str, message: str) -> str | None:
    if not isinstance(actual, list) or not actual:
        return message
    required_prefix = str(template.get("required_prefix") or "")
    allowed_suffixes = tuple(
        str(item).lower() for item in template.get("allowed_suffixes") or []
    )
    require_non_empty_content = bool(template.get("require_non_empty_content", True))
    repo = Path(repo_root).expanduser().resolve()
    for index, item in enumerate(actual):
        if not isinstance(item, str) or not item.strip():
            return f"{message}: invalid artifact at index {index}"
        candidate = _safe_repo_file(repo_root, item)
        if candidate is None:
            return f"{message}: invalid artifact at index {index}"
        relative_posix = candidate.relative_to(repo).as_posix()
        if required_prefix and not relative_posix.startswith(required_prefix):
            return f"{message}: artifact at index {index} is outside the required directory"
        if allowed_suffixes and not relative_posix.lower().endswith(allowed_suffixes):
            return f"{message}: artifact at index {index} has an unsupported file type"
        if require_non_empty_content:
            text = _read_safe_repo_text(repo_root, item)
            if text is None or not text.strip():
                return f"{message}: artifact at index {index} is empty or unreadable"
    return None


def _no_unresolved_findings_error(output: dict, template: dict, message: str) -> str | None:
    when = template.get("when")
    if when is not None:
        if not isinstance(when, dict):
            return message
        when_key = str(when.get("output_key") or "")
        if not condition_matches(
            output.get(when_key),
            str(when.get("operator") or ""),
            when.get("value"),
        ):
            return None
    findings = output.get(str(template.get("output_key") or ""))
    if not isinstance(findings, list):
        return message
    unresolved_terms = tuple(
        str(item).lower() for item in template.get("unresolved_terms") or []
    )
    resolved_terms = tuple(
        str(item).lower() for item in template.get("resolved_terms") or []
    )
    for finding in findings:
        if not isinstance(finding, str) or not finding.strip():
            return message
        lowered = finding.lower()
        unresolved = any(
            term
            and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered)
            for term in unresolved_terms
        )
        resolved = any(
            term
            and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered)
            for term in resolved_terms
        )
        if unresolved and not resolved:
            return f"{message}: unresolved findings present"
    return None


def _min_count_error(actual, template: dict, message: str) -> str | None:
    if not isinstance(actual, list):
        return message
    min_count = template.get("min_count")
    if not isinstance(min_count, int) or isinstance(min_count, bool):
        return message
    if len(actual) < min_count:
        return message
    if any(isinstance(item, str) and not item.strip() for item in actual):
        return message
    return None


def _min_count_from_constraint_error(
    actual,
    template: dict,
    state: dict | None,
    message: str,
) -> str | None:
    if not isinstance(actual, list):
        return message
    constraints = state.get("constraints") if isinstance(state, dict) else {}
    constraint_key = str(template.get("constraint_key") or "")
    raw_min_count = constraints.get(constraint_key) if isinstance(constraints, dict) else None
    default_min_count = template.get("default_min_count")
    min_count = (
        raw_min_count
        if isinstance(raw_min_count, int)
        and not isinstance(raw_min_count, bool)
        and raw_min_count >= 0
        else default_min_count
    )
    if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 0:
        return message
    if len(actual) < min_count:
        return message
    if any(isinstance(item, str) and not item.strip() for item in actual):
        return message
    return None


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
    candidate = _safe_repo_path(repo_root, actual)
    if candidate is None:
        return message
    repo = Path(repo_root).expanduser().resolve()
    relative_path = candidate.relative_to(repo)
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
    candidate = _safe_repo_file(repo_root, actual)
    if candidate is None:
        return message
    text = _read_safe_repo_text(repo_root, actual)
    if text is None:
        return message
    sections = [str(section) for section in template.get("sections") or []]
    missing = []
    for section in sections:
        if section.startswith("#") and set(section) == {"#"}:
            pattern = rf"(?m)^\s*{re.escape(section)}(?!#)\s+\S"
            if re.search(pattern, text) is None:
                missing.append(section)
        elif section not in text:
            missing.append(section)
    return None if not missing else f"{message}: missing sections {missing}"


_MAX_SAFE_REPO_TEXT_BYTES = 512 * 1024


def _safe_repo_path(repo_root: str, raw_path: str) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    try:
        repo = Path(repo_root).expanduser().resolve()
        normalized = raw_path
        if (
            normalized != normalized.strip()
            or "\\" in normalized
            or any(ord(char) < 32 for char in normalized)
            or normalized.startswith("/")
            or re.match(r"^[A-Za-z]:/", normalized)
        ):
            return None
        parts = normalized.split("/")
        if any(part in ("", ".", "..") for part in parts):
            return None
        candidate = repo.joinpath(*parts)
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(repo)
        current = repo
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return None
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def _safe_repo_file(repo_root: str, raw_path: str) -> Path | None:
    candidate = _safe_repo_path(repo_root, raw_path)
    if candidate is None or candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate


def _read_safe_repo_text(repo_root: str, raw_path: str) -> str | None:
    candidate = _safe_repo_file(repo_root, raw_path)
    if candidate is None:
        return None
    file_descriptor = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        file_descriptor = os.open(str(candidate), flags)
        with os.fdopen(file_descriptor, "rb") as handle:
            file_descriptor = None
            data = handle.read(_MAX_SAFE_REPO_TEXT_BYTES + 1)
            if len(data) > _MAX_SAFE_REPO_TEXT_BYTES:
                return None
            return data.decode("utf-8")
    except (OSError, UnicodeError):
        return None
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass


def _artifact_list_error(*, output, repo_root: str, message: str) -> str | None:
    if not isinstance(output, list) or not output:
        return message
    repo = Path(repo_root).expanduser().resolve()
    required_prefix = "knowledge-base/"
    allowed_suffixes = (".md", ".markdown", ".txt")
    for index, item in enumerate(output):
        candidate = _safe_repo_file(repo_root, item) if isinstance(item, str) else None
        if candidate is None:
            return f"{message}: invalid artifact at index {index}"
        relative_posix = candidate.relative_to(repo).as_posix()
        if not relative_posix.startswith(required_prefix):
            return f"{message}: artifact at index {index} is outside knowledge-base/"
        if not relative_posix.lower().endswith(allowed_suffixes):
            return f"{message}: artifact at index {index} is not Markdown/text"
        text = _read_safe_repo_text(repo_root, item)
        if text is None or not text.strip():
            return f"{message}: artifact at index {index} is empty or unreadable"
    return None


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
