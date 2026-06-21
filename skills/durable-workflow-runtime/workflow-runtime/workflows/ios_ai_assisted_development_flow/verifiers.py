from __future__ import annotations

from pathlib import Path

from workflows.common.contracts import VerifierResult, make_verifier_result
from workflows.common.policies import condition_matches

def verify_run_brainstorming(
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
        required_schema={'clarification_questions': 'string[]',
 'clarification_answers_summary': 'string',
 'design_presented': 'boolean',
 'user_approved_design': 'boolean',
 'design_approved': 'boolean',
 'approved_design_summary': 'string',
 'approved_design_path': 'string',
 'ui_surface_affected': 'boolean',
 'spec_review_loop_completed': 'boolean',
 'spec_review_perspectives': 'string[]',
 'spec_review_findings_summary': 'string',
 'spec_review_subagent_summaries': 'string[]',
 'open_questions': 'string[]',
 'ready_for_openspec': 'boolean'},
        optional_schema={'visual_spec_detail_summary': 'string',
 'design_comparison_source': 'string',
 'runtime_visual_comparison_scope': 'string'},
        verifier_rules=[{'output_key': 'clarification_questions',
  'operator': 'non_empty',
  'value': None,
  'message': 'Brainstorming must ask and record at least one clarification question before '
             'continuing.'},
 {'output_key': 'design_presented',
  'operator': 'is_true',
  'value': None,
  'message': 'Brainstorming must present a design before continuing.'},
 {'output_key': 'user_approved_design',
  'operator': 'is_true',
  'value': None,
  'message': 'The user must approve the brainstorming design before continuing.'},
 {'output_key': 'design_approved',
  'operator': 'is_true',
  'value': None,
  'message': 'Brainstorming must finish with an approved design.'},
 {'output_key': 'approved_design_path',
  'operator': 'truthy',
  'value': None,
  'message': 'Brainstorming must return the approved design document path.'},
 {'output_key': 'approved_design_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'Brainstorming must create the approved design document before continuing.'},
 {'output_key': 'ready_for_openspec',
  'operator': 'is_true',
  'value': None,
  'message': 'Brainstorming must declare the change ready for OpenSpec formalization.'},
 {'output_key': 'spec_review_loop_completed',
  'operator': 'is_true',
  'value': None,
  'message': 'Brainstorming must complete the required spec review loop before continuing.'},
 {'output_key': 'spec_review_findings_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Brainstorming must summarize the development, design, and testing spec review '
             'findings.'},
 {'output_key': 'open_questions',
  'operator': 'empty',
  'value': None,
  'message': 'Brainstorming open_questions must be empty before OpenSpec formalization.'}],
        verifier_templates=[{'id': 'ui_change_requires_visual_spec_detail',
  'template': 'conditional_required',
  'output_key': 'visual_spec_detail_summary',
  'message': 'If ui_surface_affected is true, visual_spec_detail_summary is required.',
  'when': {'output_key': 'ui_surface_affected', 'operator': 'is_true', 'value': None},
  'required_key': 'visual_spec_detail_summary'},
 {'id': 'ui_change_requires_design_comparison_source',
  'template': 'conditional_required',
  'output_key': 'design_comparison_source',
  'message': 'If ui_surface_affected is true, design_comparison_source is required.',
  'when': {'output_key': 'ui_surface_affected', 'operator': 'is_true', 'value': None},
  'required_key': 'design_comparison_source'},
 {'id': 'ui_change_requires_runtime_visual_scope',
  'template': 'conditional_required',
  'output_key': 'runtime_visual_comparison_scope',
  'message': 'If ui_surface_affected is true, runtime_visual_comparison_scope is required.',
  'when': {'output_key': 'ui_surface_affected', 'operator': 'is_true', 'value': None},
  'required_key': 'runtime_visual_comparison_scope'},
 {'id': 'spec_review_requires_three_perspectives',
  'template': 'min_count',
  'output_key': 'spec_review_perspectives',
  'message': 'Spec review must include at least development, design, and testing perspectives.',
  'min_count': 3},
 {'id': 'spec_review_requires_three_subagent_summaries',
  'template': 'min_count',
  'output_key': 'spec_review_subagent_summaries',
  'message': 'Spec review must include summaries from three independent review subagents.',
  'min_count': 3},
 {'id': 'approved_design_path_repo_policy',
  'template': 'repo_path_policy',
  'output_key': 'approved_design_path',
  'message': 'approved_design_path must point to a Markdown document under docs/superpowers/specs/ '
             'and must not point at openspec/changes/ artifacts.',
  'required_prefix': 'docs/superpowers/specs/',
  'forbidden_prefixes': ['openspec/changes/'],
  'required_suffix': '.md'},
 {'id': 'spec_review_requires_named_perspectives',
  'template': 'required_set_members',
  'output_key': 'spec_review_perspectives',
  'message': 'Spec review must include development, design, and testing perspectives.',
  'required_members': ['development', 'design', 'testing'],
  'case_sensitive': False}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_propose_openspec_change(
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
        required_schema={'change_name': 'string',
 'change_path': 'string',
 'proposal_path': 'string',
 'tasks_path': 'string',
 'spec_paths': 'string[]',
 'created_artifacts': 'string[]',
 'apply_ready': 'boolean'},
        optional_schema={'openspec_design_path': 'string'},
        verifier_rules=[{'output_key': 'change_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'OpenSpec change_path must exist.'},
 {'output_key': 'proposal_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'OpenSpec proposal_path must exist.'},
 {'output_key': 'tasks_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'OpenSpec tasks_path must exist.'},
 {'output_key': 'apply_ready',
  'operator': 'is_true',
  'value': None,
  'message': 'OpenSpec change must be apply-ready before implementation.'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_refine_change_with_openspec(
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
        required_schema={'refinement_summary': 'string',
 'changed_artifacts': 'string[]',
 'unresolved_questions': 'string[]',
 'ready_for_apply': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'refinement_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'OpenSpec refinement must return a non-empty refinement summary.'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_approve_refine(
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
        required_schema={'user_approved': 'boolean', 'additional_refinement_needed': 'boolean'},
        optional_schema={'user_feedback': 'string'},
        verifier_rules=[{'output_key': 'user_approved',
  'operator': 'is_true',
  'value': None,
  'message': 'User must explicitly approve before proceeding.'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_execute_implementation(
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
        required_schema={'tasks_completed': 'boolean',
 'implementation_summary': 'string',
 'changed_files': 'string[]',
 'completed_tasks': 'string[]',
 'remaining_tasks': 'string[]',
 'verification_commands': 'string[]',
 'verification_passed': 'boolean',
 'open_issues': 'string[]'},
        optional_schema={},
        verifier_rules=[{'output_key': 'tasks_completed',
  'operator': 'is_true',
  'value': None,
  'message': 'Implementation must report all selected OpenSpec tasks complete.'},
 {'output_key': 'verification_passed',
  'operator': 'is_true',
  'value': None,
  'message': 'Implementation verification must pass before review.'},
 {'output_key': 'changed_files',
  'operator': 'non_empty',
  'value': None,
  'message': 'Implementation must report the changed file list.'},
 {'output_key': 'verification_commands',
  'operator': 'non_empty',
  'value': None,
  'message': 'Implementation must report at least one verification command.'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_run_agentic_release_qa(
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
        required_schema={'release_qa_verdict': 'string',
 'release_qa_summary': 'string',
 'release_qa_executed_checks': 'string[]',
 'release_qa_blocked_checks': 'string[]',
 'release_qa_risk_next_steps': 'string[]',
 'release_qa_artifacts': 'string[]'},
        optional_schema={},
        verifier_rules=[{'output_key': 'release_qa_verdict',
  'operator': 'one_of',
  'value': ['ship', 'ship_with_risks', 'do_not_ship', 'blocked'],
  'message': 'release_qa_verdict must be ship, ship_with_risks, do_not_ship, or blocked.'},
 {'output_key': 'release_qa_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Release QA must return a non-empty summary.'},
 {'output_key': 'release_qa_risk_next_steps',
  'operator': 'non_empty',
  'value': None,
  'message': 'Release QA must return risk-based next steps, even if the next step is no further '
             'action.'}],
        verifier_templates=[{'id': 'blocked_release_qa_requires_blocked_checks',
  'template': 'conditional_required',
  'output_key': 'release_qa_blocked_checks',
  'message': 'If release_qa_verdict is blocked, release_qa_blocked_checks must be non-empty.',
  'when': {'output_key': 'release_qa_verdict', 'operator': 'equals', 'value': 'blocked'},
  'required_key': 'release_qa_blocked_checks'},
 {'id': 'do_not_ship_release_qa_requires_next_steps',
  'template': 'conditional_required',
  'output_key': 'release_qa_risk_next_steps',
  'message': 'If release_qa_verdict is do_not_ship, release_qa_risk_next_steps must be non-empty.',
  'when': {'output_key': 'release_qa_verdict', 'operator': 'equals', 'value': 'do_not_ship'},
  'required_key': 'release_qa_risk_next_steps'},
 {'id': 'ship_release_qa_requires_executed_checks',
  'template': 'conditional_required',
  'output_key': 'release_qa_executed_checks',
  'message': 'If release_qa_verdict is ship, release_qa_executed_checks must be non-empty.',
  'when': {'output_key': 'release_qa_verdict', 'operator': 'equals', 'value': 'ship'},
  'required_key': 'release_qa_executed_checks'},
 {'id': 'ship_with_risks_release_qa_requires_executed_checks',
  'template': 'conditional_required',
  'output_key': 'release_qa_executed_checks',
  'message': 'If release_qa_verdict is ship_with_risks, release_qa_executed_checks must be '
             'non-empty.',
  'when': {'output_key': 'release_qa_verdict', 'operator': 'equals', 'value': 'ship_with_risks'},
  'required_key': 'release_qa_executed_checks'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_request_final_code_review(
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
        required_schema={'review_status': 'string',
 'reviewed_snapshot': 'string',
 'findings': 'string[]',
 'review_summary': 'string',
 'changes_requested': 'boolean',
 'missing_review_inputs': 'string[]'},
        optional_schema={},
        verifier_rules=[{'output_key': 'review_status',
  'operator': 'one_of',
  'value': ['approved', 'changes_requested', 'blocked'],
  'message': 'review_status must be approved, changes_requested, or blocked.'},
 {'output_key': 'reviewed_snapshot',
  'operator': 'truthy',
  'value': None,
  'message': 'Review must identify the snapshot that was reviewed.'}],
        verifier_templates=[{'id': 'changes_requested_status_sets_flag',
  'template': 'conditional_equals',
  'output_key': 'changes_requested',
  'message': 'If review_status is changes_requested, changes_requested must be true.',
  'when': {'output_key': 'review_status', 'operator': 'equals', 'value': 'changes_requested'},
  'expected_value': True},
 {'id': 'approved_status_clears_changes_requested',
  'template': 'conditional_equals',
  'output_key': 'changes_requested',
  'message': 'If review_status is approved, changes_requested must be false.',
  'when': {'output_key': 'review_status', 'operator': 'equals', 'value': 'approved'},
  'expected_value': False},
 {'id': 'changes_requested_requires_findings',
  'template': 'conditional_required',
  'output_key': 'findings',
  'message': 'If review_status is changes_requested, findings must be non-empty.',
  'when': {'output_key': 'review_status', 'operator': 'equals', 'value': 'changes_requested'},
  'required_key': 'findings'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_write_code_kb_feedback(
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
        required_schema={'kb_updated': 'boolean',
 'updated_pages': 'string[]',
 'backlog_updates': 'string[]',
 'kb_checks': 'string[]'},
        optional_schema={'qa_feedback_path': 'string', 'skipped_reason': 'string'},
        verifier_rules=[],
        verifier_templates=[{'id': 'skip_requires_reason',
  'template': 'conditional_required',
  'output_key': 'skipped_reason',
  'message': 'If kb_updated is false, skipped_reason is required.',
  'when': {'output_key': 'kb_updated', 'operator': 'is_false', 'value': None},
  'required_key': 'skipped_reason'},
 {'id': 'kb_update_requires_pages',
  'template': 'conditional_required',
  'output_key': 'updated_pages',
  'message': 'If kb_updated is true, updated_pages must be non-empty.',
  'when': {'output_key': 'kb_updated', 'operator': 'is_true', 'value': None},
  'required_key': 'updated_pages'},
 {'id': 'kb_update_requires_checks',
  'template': 'conditional_required',
  'output_key': 'kb_checks',
  'message': 'If kb_updated is true, kb_checks must report formatting or hygiene checks.',
  'when': {'output_key': 'kb_updated', 'operator': 'is_true', 'value': None},
  'required_key': 'kb_checks'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

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


def _fail(message: str, run_id: str, step_id: str, state: dict | None) -> VerifierResult:
    return make_verifier_result(
        passed=False,
        message=message,
        details={"run_id": run_id, "step_id": step_id, "state": state or {}},
    )
