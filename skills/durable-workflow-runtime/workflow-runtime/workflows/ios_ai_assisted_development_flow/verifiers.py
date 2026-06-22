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
  'operator': 'one_of',
  'value': [True, False],
  'message': 'OpenSpec proposal must report whether the change is currently apply-ready.'}],
        verifier_templates=[{'id': 'created_artifacts_minimum_surface',
  'template': 'min_count',
  'output_key': 'created_artifacts',
  'message': 'OpenSpec proposal must report at least proposal, tasks, and one design/spec '
             'artifact.',
  'min_count': 3},
 {'id': 'change_path_repo_policy',
  'template': 'repo_path_policy',
  'output_key': 'change_path',
  'message': 'change_path must point inside openspec/changes/.',
  'required_prefix': 'openspec/changes/',
  'forbidden_prefixes': []},
 {'id': 'proposal_path_repo_policy',
  'template': 'repo_path_policy',
  'output_key': 'proposal_path',
  'message': 'proposal_path must point to an OpenSpec proposal markdown file under '
             'openspec/changes/.',
  'required_prefix': 'openspec/changes/',
  'forbidden_prefixes': [],
  'required_suffix': 'proposal.md'},
 {'id': 'tasks_path_repo_policy',
  'template': 'repo_path_policy',
  'output_key': 'tasks_path',
  'message': 'tasks_path must point to an OpenSpec tasks markdown file under openspec/changes/.',
  'required_prefix': 'openspec/changes/',
  'forbidden_prefixes': [],
  'required_suffix': 'tasks.md'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_propose_openspec_change(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
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
 'user_discussion_summary': 'string',
 'discussion_turn_count': 'integer',
 'changed_artifacts': 'string[]',
 'unresolved_questions': 'string[]',
 'ready_for_apply': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'refinement_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'OpenSpec refinement must return a non-empty refinement summary.'},
 {'output_key': 'user_discussion_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'OpenSpec refinement must summarize the actual user discussion before it can '
             'continue.'}],
        verifier_templates=[],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_refine_change_with_openspec(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
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
        verifier_rules=[],
        verifier_templates=[{'id': 'approved_clears_additional_refinement',
  'template': 'conditional_equals',
  'output_key': 'additional_refinement_needed',
  'message': 'If user_approved is true, additional_refinement_needed must be false.',
  'when': {'output_key': 'user_approved', 'operator': 'is_true', 'value': None},
  'expected_value': False},
 {'id': 'rejected_requires_additional_refinement',
  'template': 'conditional_equals',
  'output_key': 'additional_refinement_needed',
  'message': 'If user_approved is false, additional_refinement_needed must be true.',
  'when': {'output_key': 'user_approved', 'operator': 'is_false', 'value': None},
  'expected_value': True}],
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
        optional_schema={'openspec_updates_required': 'boolean', 'openspec_update_summary': 'string'},
        verifier_rules=[{'output_key': 'changed_files',
  'operator': 'non_empty',
  'value': None,
  'message': 'Implementation must report the changed file list.'},
 {'output_key': 'verification_commands',
  'operator': 'non_empty',
  'value': None,
  'message': 'Implementation must report at least one verification command.'}],
        verifier_templates=[{'id': 'openspec_update_requires_summary',
  'template': 'conditional_required',
  'output_key': 'openspec_update_summary',
  'message': 'If openspec_updates_required is true, openspec_update_summary must explain the spec '
             'gap.',
  'when': {'output_key': 'openspec_updates_required', 'operator': 'is_true', 'value': None},
  'required_key': 'openspec_update_summary'},
 {'id': 'openspec_update_clears_tasks_completed',
  'template': 'conditional_equals',
  'output_key': 'tasks_completed',
  'message': 'If openspec_updates_required is true, tasks_completed must be false.',
  'when': {'output_key': 'openspec_updates_required', 'operator': 'is_true', 'value': None},
  'expected_value': False}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_execute_implementation(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
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
  'required_key': 'release_qa_executed_checks'},
 {'id': 'ship_with_risks_release_qa_requires_blocked_checks',
  'template': 'conditional_required',
  'output_key': 'release_qa_blocked_checks',
  'message': 'If release_qa_verdict is ship_with_risks, release_qa_blocked_checks must identify '
             'the residual risk scope.',
  'when': {'output_key': 'release_qa_verdict', 'operator': 'equals', 'value': 'ship_with_risks'},
  'required_key': 'release_qa_blocked_checks'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_run_agentic_release_qa(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_request_pre_merge_code_review(
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
 {'id': 'approved_status_clears_missing_review_inputs',
  'template': 'conditional_equals',
  'output_key': 'missing_review_inputs',
  'message': 'If review_status is approved, missing_review_inputs must be empty.',
  'when': {'output_key': 'review_status', 'operator': 'equals', 'value': 'approved'},
  'expected_value': []},
 {'id': 'changes_requested_requires_findings',
  'template': 'conditional_required',
  'output_key': 'findings',
  'message': 'If review_status is changes_requested, findings must be non-empty.',
  'when': {'output_key': 'review_status', 'operator': 'equals', 'value': 'changes_requested'},
  'required_key': 'findings'},
 {'id': 'blocked_status_clears_changes_requested',
  'template': 'conditional_equals',
  'output_key': 'changes_requested',
  'message': 'If review_status is blocked, changes_requested must be false.',
  'when': {'output_key': 'review_status', 'operator': 'equals', 'value': 'blocked'},
  'expected_value': False},
 {'id': 'blocked_status_requires_missing_review_inputs',
  'template': 'conditional_required',
  'output_key': 'missing_review_inputs',
  'message': 'If review_status is blocked, missing_review_inputs must be non-empty.',
  'when': {'output_key': 'review_status', 'operator': 'equals', 'value': 'blocked'},
  'required_key': 'missing_review_inputs'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_request_pre_merge_code_review(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_verify_completion(
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
        required_schema={'verification_passed': 'boolean',
 'verification_summary': 'string',
 'verification_evidence': 'string[]',
 'remaining_risks': 'string[]',
 'missing_verification_inputs': 'string[]'},
        optional_schema={'release_qa_risks_resolved': 'boolean', 'release_qa_risk_resolution_summary': 'string'},
        verifier_rules=[{'output_key': 'verification_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Completion verification must summarize the evidence and outcome.'},
 {'output_key': 'verification_evidence',
  'operator': 'non_empty',
  'value': None,
  'message': 'Completion verification must record at least one fresh evidence item.'}],
        verifier_templates=[{'id': 'failed_verification_requires_risks_or_missing_inputs',
  'template': 'conditional_required',
  'output_key': 'remaining_risks',
  'message': 'If verification_passed is false, remaining_risks must be non-empty.',
  'when': {'output_key': 'verification_passed', 'operator': 'is_false', 'value': None},
  'required_key': 'remaining_risks'},
 {'id': 'resolved_release_qa_risks_require_summary',
  'template': 'conditional_required',
  'output_key': 'release_qa_risk_resolution_summary',
  'message': 'If release_qa_risks_resolved is true, release_qa_risk_resolution_summary must '
             'explain the fresh evidence.',
  'when': {'output_key': 'release_qa_risks_resolved', 'operator': 'is_true', 'value': None},
  'required_key': 'release_qa_risk_resolution_summary'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_verify_completion(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def _run_custom_verifier_requirements_propose_openspec_change(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_propose_openspec_change_artifact_completeness(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

def _custom_verifier_requirement_propose_openspec_change_artifact_completeness(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: OpenSpec proposal output must prove that proposal, tasks, and at least one durable design/spec artifact were created and reported consistently.
Signals: created_artifacts, proposal_path, tasks_path, openspec_design_path, spec_paths
Implementation surfaces: verifier, tests
Hint pseudocode:
- Require created_artifacts to mention proposal and tasks artifacts.
- Require either openspec_design_path or spec_paths to provide at least one design/spec artifact path.
- Reject outputs where created_artifacts omits the durable design/spec surface even if raw files exist.
Test intent:
- Reject outputs that only report proposal/tasks and omit any design/spec artifact.
- Accept outputs that report proposal, tasks, and at least one design/spec artifact consistently."""
    _ = state, repo_root
    created_artifacts = _string_list(output.get("created_artifacts"))
    created_text = " ".join(created_artifacts).lower()
    has_proposal = "proposal" in created_text
    has_tasks = "task" in created_text
    openspec_design_path = str(output.get("openspec_design_path") or "").strip()
    spec_paths = _string_list(output.get("spec_paths"))
    has_design_or_spec_path = bool(openspec_design_path or spec_paths)
    has_design_or_spec_artifact = any(
        any(marker in artifact.lower() for marker in ("design", "spec"))
        for artifact in created_artifacts
    )
    if not has_proposal or not has_tasks:
        return "OpenSpec proposal must report proposal and tasks artifacts in created_artifacts."
    if not has_design_or_spec_path:
        return (
            "OpenSpec proposal must report at least one durable design/spec artifact path via "
            "openspec_design_path or spec_paths."
        )
    if not has_design_or_spec_artifact:
        return (
            "OpenSpec proposal must include a design/spec artifact in created_artifacts when it "
            "reports durable design/spec paths."
        )
    return None

def _run_custom_verifier_requirements_refine_change_with_openspec(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_refine_change_with_openspec_talk_first_conversation_evidence(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

def _custom_verifier_requirement_refine_change_with_openspec_talk_first_conversation_evidence(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: OpenSpec refinement must prove that at least one real conversational exchange happened before the stage claimed readiness.
Signals: user_discussion_summary, discussion_turn_count, unresolved_questions, ready_for_apply
Implementation surfaces: verifier, tests
Hint pseudocode:
- Reject if discussion_turn_count is less than 1.
- Reject if user_discussion_summary is missing or looks empty after trimming.
- If unresolved_questions is empty and ready_for_apply is true, still require concrete conversation evidence instead of accepting a checklist-only output.
Test intent:
- Reject outputs that claim ready_for_apply without any discussion turn evidence.
- Accept outputs that record a user discussion summary and a positive discussion_turn_count."""
    _ = state, repo_root
    discussion_turn_count = output.get("discussion_turn_count")
    if not isinstance(discussion_turn_count, int) or isinstance(discussion_turn_count, bool):
        return "discussion_turn_count must be an integer."
    if discussion_turn_count < 1:
        return (
            "OpenSpec refinement must record at least one conversational exchange before "
            "claiming readiness."
        )
    discussion_summary = str(output.get("user_discussion_summary") or "").strip()
    if not discussion_summary:
        return (
            "OpenSpec refinement must summarize the actual user discussion before it can "
            "continue."
        )
    return None

def _run_custom_verifier_requirements_execute_implementation(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_execute_implementation_completed_tasks_consistency(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

def _custom_verifier_requirement_execute_implementation_completed_tasks_consistency(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: Implementation success output must not claim tasks are complete while still listing remaining tasks.
Signals: tasks_completed, remaining_tasks, completed_tasks, openspec_updates_required
Implementation surfaces: verifier, tests
Hint pseudocode:
- If tasks_completed is true, require remaining_tasks to be empty.
- If tasks_completed is false and openspec_updates_required is not true, require remaining_tasks to be non-empty so the retry reason is concrete.
- If verification_passed is false and openspec_updates_required is not true, reject the output so plain failing implementation cannot continue.
Test intent:
- Reject outputs that set tasks_completed=true while still listing remaining_tasks.
- Reject unfinished implementation outputs that provide neither a remaining task list nor an OpenSpec refinement reason.
- Reject implementation outputs that fail verification without explicitly routing back for OpenSpec updates."""
    _ = state, repo_root
    tasks_completed = output.get("tasks_completed")
    remaining_tasks = _string_list(output.get("remaining_tasks"))
    openspec_updates_required = bool(output.get("openspec_updates_required"))
    verification_passed = output.get("verification_passed")
    if tasks_completed is True and remaining_tasks:
        return "Implementation cannot set tasks_completed=true while remaining_tasks is non-empty."
    if tasks_completed is False and not openspec_updates_required and not remaining_tasks:
        return (
            "Implementation retries must list remaining_tasks unless they are explicitly routing "
            "back for OpenSpec updates."
        )
    if verification_passed is False and not openspec_updates_required:
        return (
            "Implementation verification cannot fail unless the output is explicitly routing back "
            "for OpenSpec updates."
        )
    return None

def _run_custom_verifier_requirements_run_agentic_release_qa(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_run_agentic_release_qa_ui_visual_qa_evidence(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

def _custom_verifier_requirement_run_agentic_release_qa_ui_visual_qa_evidence(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: When the workflow state says a UI surface changed and visual comparison inputs are available, release QA must report executed or blocked visual comparison evidence explicitly.
Signals: state.ui_surface_affected, state.design_comparison_source, state.runtime_visual_comparison_scope, release_qa_executed_checks, release_qa_blocked_checks, release_qa_artifacts
Implementation surfaces: verifier, tests
Hint pseudocode:
- Read ui_surface_affected, design_comparison_source, and runtime_visual_comparison_scope from persisted state.
- Only enforce this requirement when all three values indicate visual QA should have been attempted.
- Require executed_checks, blocked_checks, or artifacts to mention a visual diff, screenshot comparison, or design comparison pass.
Test intent:
- Reject UI-impacting release QA output that omits all visual comparison evidence despite having comparison inputs.
- Accept UI-impacting release QA output when visual comparison evidence appears in executed checks, blocked checks, or artifacts."""
    _ = repo_root
    state = state or {}
    ui_surface_affected = bool(state.get("ui_surface_affected"))
    design_source = str(state.get("design_comparison_source") or "").strip()
    runtime_scope = str(state.get("runtime_visual_comparison_scope") or "").strip()
    if not (ui_surface_affected and design_source and runtime_scope):
        return None
    evidence_lines = (
        _string_list(output.get("release_qa_executed_checks"))
        + _string_list(output.get("release_qa_blocked_checks"))
        + _string_list(output.get("release_qa_artifacts"))
    )
    if not any(_looks_like_visual_evidence(item) for item in evidence_lines):
        return (
            "UI-impacting release QA must report explicit visual comparison evidence when "
            "design and runtime comparison inputs are available."
        )
    return None

def _run_custom_verifier_requirements_request_pre_merge_code_review(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_request_pre_merge_code_review_findings_include_severity_grouping(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

def _custom_verifier_requirement_request_pre_merge_code_review_findings_include_severity_grouping(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: Non-empty review findings must make severity explicit so the workflow can distinguish major merge blockers from lower-risk notes.
Signals: review_status, findings
Implementation surfaces: verifier, tests
Hint pseudocode:
- Skip the requirement when findings is empty.
- Require each finding string to begin with or clearly include a recognized severity marker such as critical, high, medium, low, major, or minor.
Test intent:
- Reject change-requested findings that omit any severity marker.
- Accept findings that carry an explicit severity prefix."""
    _ = state, repo_root
    findings = _string_list(output.get("findings"))
    if not findings:
        return None
    for finding in findings:
        if not _has_severity_marker(finding):
            return (
                "Review findings must include an explicit severity marker such as critical, "
                "high, medium, low, major, or minor."
            )
    return None

def _run_custom_verifier_requirements_verify_completion(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_verify_completion_ship_with_risks_requires_resolution_before_pass(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

def _custom_verifier_requirement_verify_completion_ship_with_risks_requires_resolution_before_pass(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: If persisted release QA ended in ship_with_risks, final completion verification may pass only after those residual risks are explicitly resolved with fresh evidence.
Signals: state.release_qa_verdict, state.release_qa_blocked_checks, verification_passed, verification_evidence, remaining_risks, release_qa_risks_resolved, release_qa_risk_resolution_summary
Implementation surfaces: verifier, tests
Hint pseudocode:
- Read release_qa_verdict and release_qa_blocked_checks from persisted state.
- If release_qa_verdict is ship_with_risks and verification_passed is true, require release_qa_risks_resolved to be true, a non-empty release_qa_risk_resolution_summary, and fresh verification evidence that resolves the prior risk.
- If release_qa_verdict is ship_with_risks and verification_passed is false, require remaining_risks or missing_verification_inputs to carry the residual risk forward.
Test intent:
- Reject passing completion output that ignores prior ship_with_risks residual QA risk.
- Accept passing completion output only when it explicitly resolves the prior residual QA risk with fresh evidence."""
    _ = repo_root
    state = state or {}
    if state.get("release_qa_verdict") != "ship_with_risks":
        return None
    verification_passed = output.get("verification_passed")
    remaining_risks = _string_list(output.get("remaining_risks"))
    missing_inputs = _string_list(output.get("missing_verification_inputs"))
    evidence = _string_list(output.get("verification_evidence"))
    risks_resolved = output.get("release_qa_risks_resolved") is True
    resolution_summary = str(output.get("release_qa_risk_resolution_summary") or "").strip()
    if verification_passed is True:
        if not risks_resolved:
            return (
                "Completion verification cannot pass while prior ship_with_risks residual QA "
                "risks remain unresolved."
            )
        if not resolution_summary:
            return (
                "Completion verification must explain how prior ship_with_risks residual QA "
                "risks were resolved."
            )
        if not any(_looks_like_resolution_evidence(item) for item in evidence):
            return (
                "Completion verification must include fresh evidence that resolves the prior "
                "ship_with_risks QA risk."
            )
        return None
    if not remaining_risks and not missing_inputs:
        return (
            "When prior release QA ended in ship_with_risks, a non-passing completion result "
            "must carry forward remaining_risks or missing_verification_inputs."
        )
    return None


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def _looks_like_visual_evidence(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "visual",
        "pixel",
        "screenshot",
        "figma",
        "design comparison",
        "diff",
        "snapshot",
    )
    return any(marker in lowered for marker in markers)


def _has_severity_marker(text: str) -> bool:
    lowered = text.strip().lower()
    markers = ("critical", "high", "medium", "low", "major", "minor")
    return any(
        lowered.startswith(f"{marker} ")
        or lowered.startswith(f"{marker}|")
        or f"{marker} |" in lowered
        for marker in markers
    )


def _looks_like_resolution_evidence(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "resolved",
        "reran",
        "re-ran",
        "executed",
        "visual",
        "device",
        "pixel",
        "comparison",
    )
    return any(marker in lowered for marker in markers)

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
