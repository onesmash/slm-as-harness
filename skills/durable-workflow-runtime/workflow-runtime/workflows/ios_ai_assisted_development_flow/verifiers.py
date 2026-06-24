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
 'open_questions': 'string[]',
 'ready_for_subagent_review': 'boolean'},
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
 {'output_key': 'ready_for_subagent_review',
  'operator': 'is_true',
  'value': None,
  'message': 'Brainstorming must declare the change ready for subagent review authorization.'},
 {'output_key': 'open_questions',
  'operator': 'empty',
  'value': None,
  'message': 'Brainstorming open_questions must be empty before implementation planning.'}],
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
 {'id': 'approved_design_path_repo_policy',
  'template': 'repo_path_policy',
  'output_key': 'approved_design_path',
  'message': 'approved_design_path must point to a Markdown document under docs/superpowers/specs/ '
             'and must not point at docs/superpowers/plans/ artifacts.',
  'required_prefix': 'docs/superpowers/specs/',
  'forbidden_prefixes': ['docs/superpowers/plans/'],
  'required_suffix': '.md'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_approve_subagent_review(
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
        required_schema={'subagent_review_approved': 'boolean',
 'authorization_summary': 'string',
 'ready_for_spec_review': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'subagent_review_approved',
  'operator': 'is_true',
  'value': None,
  'message': 'The workflow must record an explicit approve-or-decline subagent review decision '
             'before continuing or closing.'},
 {'output_key': 'authorization_summary',
  'operator': 'truthy',
  'value': None,
  'message': "The workflow must record a summary of the user's subagent review authorization "
             'decision.'}],
        verifier_templates=[{'id': 'approved_authorization_requires_ready_for_spec_review',
  'template': 'conditional_equals',
  'output_key': 'ready_for_spec_review',
  'message': 'If subagent_review_approved is true, ready_for_spec_review must be true.',
  'when': {'output_key': 'subagent_review_approved', 'operator': 'is_true', 'value': None},
  'expected_value': True},
 {'id': 'declined_authorization_clears_ready_for_spec_review',
  'template': 'conditional_equals',
  'output_key': 'ready_for_spec_review',
  'message': 'If subagent_review_approved is false, ready_for_spec_review must be false.',
  'when': {'output_key': 'subagent_review_approved', 'operator': 'is_false', 'value': None},
  'expected_value': False}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    return result

def verify_run_spec_review(
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
        required_schema={'spec_review_loop_completed': 'boolean',
 'spec_review_perspectives': 'string[]',
 'spec_review_findings_summary': 'string',
 'spec_review_subagent_summaries': 'string[]',
 'spec_review_artifact_paths': 'string[]',
 'open_questions': 'string[]',
 'ready_for_planning': 'boolean'},
        optional_schema={},
        verifier_rules=[{'output_key': 'spec_review_loop_completed',
  'operator': 'is_true',
  'value': None,
  'message': 'The subagent spec review loop must complete before implementation planning.'},
 {'output_key': 'spec_review_findings_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'The workflow must summarize the development, design, and testing spec review '
             'findings.'},
 {'output_key': 'spec_review_artifact_paths',
  'operator': 'non_empty',
  'value': None,
  'message': 'The workflow must return the concrete subagent review artifact paths.'}],
        verifier_templates=[{'id': 'spec_review_requires_three_perspectives',
  'template': 'min_count',
  'output_key': 'spec_review_perspectives',
  'message': 'Spec review must include at least development, design, and testing perspectives.',
  'min_count': 3},
 {'id': 'spec_review_requires_three_subagent_summaries',
  'template': 'min_count',
  'output_key': 'spec_review_subagent_summaries',
  'message': 'Spec review must include summaries from three independent review subagents.',
  'min_count': 3},
 {'id': 'spec_review_requires_three_artifacts',
  'template': 'min_count',
  'output_key': 'spec_review_artifact_paths',
  'message': 'Spec review must hand in three concrete subagent review artifacts.',
  'min_count': 3},
 {'id': 'spec_review_requires_named_perspectives',
  'template': 'required_set_members',
  'output_key': 'spec_review_perspectives',
  'message': 'Spec review must include development, design, and testing perspectives.',
  'required_members': ['development', 'design', 'testing'],
  'case_sensitive': False},
 {'id': 'planning_ready_requires_open_questions_cleared',
  'template': 'conditional_equals',
  'output_key': 'open_questions',
  'message': 'If ready_for_planning is true, open_questions must be empty.',
  'when': {'output_key': 'ready_for_planning', 'operator': 'is_true', 'value': None},
  'expected_value': []}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_run_spec_review(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
    return result

def verify_write_implementation_plan(
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
        required_schema={'plan_summary': 'string',
 'plan_path': 'string',
 'plan_reviewed': 'boolean',
 'execution_mode': 'string',
 'open_questions': 'string[]',
 'ready_for_implementation': 'boolean'},
        optional_schema={'plan_revision_reason': 'string'},
        verifier_rules=[{'output_key': 'plan_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Implementation planning must return a non-empty plan summary.'},
 {'output_key': 'plan_path',
  'operator': 'truthy',
  'value': None,
  'message': 'Implementation planning must return the written plan path.'},
 {'output_key': 'plan_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'Implementation planning must create the plan document before continuing.'},
 {'output_key': 'plan_reviewed',
  'operator': 'is_true',
  'value': None,
  'message': 'The user must review the written implementation plan before continuing.'},
 {'output_key': 'open_questions',
  'operator': 'empty',
  'value': None,
  'message': 'Planning open_questions must be empty before implementation can begin.'},
 {'output_key': 'execution_mode',
  'operator': 'truthy',
  'value': None,
  'message': 'Implementation planning must return an explicit execution_mode.'}],
        verifier_templates=[{'id': 'plan_path_repo_policy',
  'template': 'repo_path_policy',
  'output_key': 'plan_path',
  'message': 'plan_path must point to a Markdown document under docs/superpowers/plans/.',
  'required_prefix': 'docs/superpowers/plans/',
  'forbidden_prefixes': [],
  'required_suffix': '.md'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_write_implementation_plan(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
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
        optional_schema={'debugging_summary': 'string', 'plan_updates_required': 'boolean', 'plan_update_summary': 'string'},
        verifier_rules=[{'output_key': 'changed_files',
  'operator': 'non_empty',
  'value': None,
  'message': 'Implementation must report the changed file list.'},
 {'output_key': 'verification_commands',
  'operator': 'non_empty',
  'value': None,
  'message': 'Implementation must report at least one verification command.'}],
        verifier_templates=[{'id': 'plan_update_requires_summary',
  'template': 'conditional_required',
  'output_key': 'plan_update_summary',
  'message': 'If plan_updates_required is true, plan_update_summary must explain the plan or '
             'design gap.',
  'when': {'output_key': 'plan_updates_required', 'operator': 'is_true', 'value': None},
  'required_key': 'plan_update_summary'},
 {'id': 'plan_update_clears_tasks_completed',
  'template': 'conditional_equals',
  'output_key': 'tasks_completed',
  'message': 'If plan_updates_required is true, tasks_completed must be false.',
  'when': {'output_key': 'plan_updates_required', 'operator': 'is_true', 'value': None},
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
 'release_qa_artifacts': 'string[]',
 'release_qa_target_scope': 'string'},
        optional_schema={},
        verifier_rules=[{'output_key': 'release_qa_verdict',
  'operator': 'one_of',
  'value': ['ship', 'do_not_ship'],
  'message': 'release_qa_verdict must be ship or do_not_ship when release QA completes '
             'successfully.'},
 {'output_key': 'release_qa_summary',
  'operator': 'truthy',
  'value': None,
  'message': 'Release QA must return a non-empty summary.'},
 {'output_key': 'release_qa_risk_next_steps',
  'operator': 'non_empty',
  'value': None,
  'message': 'Release QA must return risk-based next steps, even if the next step is no further '
             'action.'},
 {'output_key': 'release_qa_target_scope',
  'operator': 'truthy',
  'value': None,
  'message': 'Release QA must identify the code range or artifact under test.'}],
        verifier_templates=[{'id': 'do_not_ship_release_qa_requires_next_steps',
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
  'required_key': 'release_qa_executed_checks'}],
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
  'value': ['approved', 'changes_requested'],
  'message': 'review_status must be approved or changes_requested when code review completes '
             'successfully.'},
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
  'required_key': 'findings'}],
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
  'required_key': 'release_qa_risk_resolution_summary'},
 {'id': 'passed_verification_clears_remaining_risks',
  'template': 'conditional_equals',
  'output_key': 'remaining_risks',
  'message': 'If verification_passed is true, remaining_risks must be empty.',
  'when': {'output_key': 'verification_passed', 'operator': 'is_true', 'value': None},
  'expected_value': []},
 {'id': 'passed_verification_clears_missing_inputs',
  'template': 'conditional_equals',
  'output_key': 'missing_verification_inputs',
  'message': 'If verification_passed is true, missing_verification_inputs must be empty.',
  'when': {'output_key': 'verification_passed', 'operator': 'is_true', 'value': None},
  'expected_value': []}],
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

def _run_custom_verifier_requirements_run_spec_review(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_run_spec_review_spec_review_outputs_require_artifacts(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: run_spec_review
# custom_verifier_requirement_id: spec_review_outputs_require_artifacts
# template_version: 1
# spec_fingerprint: b1bd1d14299261c3cbb486d71fe7ca5cfe6ae81022dbcc92abc6ef90f637f0ad
# implementation_version: none
def _custom_verifier_requirement_run_spec_review_spec_review_outputs_require_artifacts(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: The review stage must hand in concrete subagent review artifacts so the workflow can verify that development, design, and testing reviews really happened.
Signals: spec_review_perspectives, spec_review_subagent_summaries, spec_review_artifact_paths
Implementation surfaces: verifier, tests
Hint pseudocode:
- Require at least three non-empty artifact paths.
- Require each artifact path to exist under docs/superpowers/specs/ and end with .md.
- Require the combined artifact paths to clearly cover development, design, and testing review outputs.
Test intent:
- Reject review output that provides review summaries without artifact paths.
- Reject review output whose artifact paths do not exist or do not cover development, design, and testing.
- Accept review output that hands in concrete review artifacts for all three perspectives."""
    artifact_paths = _meaningful_entries(output.get("spec_review_artifact_paths"))
    if len(artifact_paths) < 3:
        return "spec_review_artifact_paths must contain at least three concrete artifact paths"

    required_prefix = Path("docs/superpowers/specs")
    missing_perspectives = {"development", "design", "testing"}
    repo_root_path = Path(repo_root)
    for artifact_path in artifact_paths:
        artifact = Path(artifact_path)
        if artifact.suffix != ".md":
            return "spec review artifacts must be Markdown files"
        if not _path_has_prefix(artifact, required_prefix):
            return "spec review artifacts must live under docs/superpowers/specs/"
        if not (repo_root_path / artifact).exists():
            return f"spec review artifact does not exist: {artifact_path}"
        lowered = artifact_path.lower()
        missing_perspectives = {
            perspective for perspective in missing_perspectives if perspective not in lowered
        }

    if missing_perspectives:
        joined = ", ".join(sorted(missing_perspectives))
        return f"spec review artifacts must clearly cover these perspectives: {joined}"
    return None

def _run_custom_verifier_requirements_write_implementation_plan(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_write_implementation_plan_planning_requires_subagent_execution_mode(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: write_implementation_plan
# custom_verifier_requirement_id: planning_requires_subagent_execution_mode
# template_version: 1
# spec_fingerprint: 4d55ba5eb104c127a1ac939bb251525ef50bc1e98eb8c256bc4c2c042acf422d
# implementation_version: none
def _custom_verifier_requirement_write_implementation_plan_planning_requires_subagent_execution_mode(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: This workflow may continue only when planning records subagent-driven execution as the selected approach.
Signals: execution_mode, ready_for_implementation, plan_reviewed
Implementation surfaces: verifier, tests
Hint pseudocode:
- Normalize execution_mode to lowercase.
- Accept only subagent-driven or subagent-driven-development as implementation-ready modes.
- If execution_mode is inline, reject the output or require ready_for_implementation to remain false.
- If plan_update_summary, debugging_summary, or open_issues are present in state, require the revised planning output to acknowledge the replanning reason via plan_revision_reason or plan_summary.
Test intent:
- Reject planning outputs that pick inline execution while claiming implementation is ready.
- Accept planning outputs that record subagent-driven execution with a reviewed plan.
- Reject replanning output that ignores recorded plan-update or implementation-learned reasons when such context exists in state."""
    execution_mode = str(output.get("execution_mode") or "").strip().lower()
    ready_for_implementation = bool(output.get("ready_for_implementation"))
    allowed_modes = {"subagent-driven", "subagent-driven-development"}
    if ready_for_implementation and execution_mode not in allowed_modes:
        return "ready_for_implementation requires execution_mode to be subagent-driven"

    replanning_state_present = False
    if isinstance(state, dict):
        replanning_state_present = bool(
            str(state.get("plan_update_summary") or "").strip()
            or str(state.get("debugging_summary") or "").strip()
            or _meaningful_entries(state.get("open_issues"))
        )
    if replanning_state_present:
        plan_revision_reason = str(output.get("plan_revision_reason") or "").strip()
        plan_summary = str(output.get("plan_summary") or "").strip().lower()
        if not plan_revision_reason and "replan" not in plan_summary and "revis" not in plan_summary:
            return "replanning context requires plan_revision_reason or an explicit replanning acknowledgement"
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

# custom_verifier_stage_id: execute_implementation
# custom_verifier_requirement_id: completed_tasks_consistency
# template_version: 1
# spec_fingerprint: 662255397991a8c36420c09c11b274ad4d0b65dbf89d48c47918f960d7017826
# implementation_version: none
def _custom_verifier_requirement_execute_implementation_completed_tasks_consistency(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: Implementation success output must not claim tasks are complete while still listing remaining tasks.
Signals: tasks_completed, remaining_tasks, completed_tasks, plan_updates_required, verification_passed
Implementation surfaces: verifier, tests
Hint pseudocode:
- If tasks_completed is true, require remaining_tasks to be empty.
- If tasks_completed is false and plan_updates_required is not true, require remaining_tasks to be non-empty so the retry reason is concrete.
- If verification_passed is false and plan_updates_required is not true, reject the output so plain failing implementation cannot continue.
Test intent:
- Reject outputs that set tasks_completed=true while still listing remaining_tasks.
- Reject unfinished implementation outputs that provide neither a remaining task list nor a planning reason.
- Reject implementation outputs that fail verification without explicitly routing back for plan updates."""
    tasks_completed = bool(output.get("tasks_completed"))
    plan_updates_required = bool(output.get("plan_updates_required"))
    verification_passed = bool(output.get("verification_passed"))
    remaining_tasks = _meaningful_entries(output.get("remaining_tasks"))
    if tasks_completed and remaining_tasks:
        return "tasks_completed cannot be true when remaining_tasks is non-empty"
    if not tasks_completed and not plan_updates_required and not remaining_tasks:
        return "unfinished implementation must report remaining_tasks or request plan updates"
    if not verification_passed and not plan_updates_required:
        return "verification_passed cannot be false unless the output explicitly routes back for plan updates"
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
    message = _custom_verifier_requirement_run_agentic_release_qa_release_qa_lists_require_meaningful_entries(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    message = _custom_verifier_requirement_run_agentic_release_qa_ship_verdict_requires_no_blocked_checks(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: run_agentic_release_qa
# custom_verifier_requirement_id: ui_visual_qa_evidence
# template_version: 1
# spec_fingerprint: 4606d7538ed7f40b00173c64b06dad404a354f81d3ec170579fe313678109cbf
# implementation_version: none
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
    state = state or {}
    should_require_visual_evidence = bool(
        state.get("ui_surface_affected")
        and str(state.get("design_comparison_source") or "").strip()
        and str(state.get("runtime_visual_comparison_scope") or "").strip()
    )
    if not should_require_visual_evidence:
        return None

    evidence_items = (
        _meaningful_entries(output.get("release_qa_executed_checks"))
        + _meaningful_entries(output.get("release_qa_blocked_checks"))
        + _meaningful_entries(output.get("release_qa_artifacts"))
    )
    if not any(_looks_like_visual_evidence(item) for item in evidence_items):
        return "UI-impacting release QA must report explicit visual comparison evidence"
    return None

# custom_verifier_stage_id: run_agentic_release_qa
# custom_verifier_requirement_id: release_qa_lists_require_meaningful_entries
# template_version: 1
# spec_fingerprint: 40cb637d49a39e4f1f564a44c5966d5411e9a8a45c2963617671dfcb6a8926f2
# implementation_version: none
def _custom_verifier_requirement_run_agentic_release_qa_release_qa_lists_require_meaningful_entries(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: Release QA evidence lists must contain meaningful non-empty entries, not whitespace-only placeholders.
Signals: release_qa_verdict, release_qa_executed_checks, release_qa_blocked_checks, release_qa_risk_next_steps
Implementation surfaces: verifier, tests
Hint pseudocode:
- Trim each list entry before validation.
- Reject ship outputs whose executed checks become empty after trimming.
- Reject any verdict whose risk next steps become empty after trimming.
- If blocked_checks is present, reject blocked_checks that only contain blank placeholders.
Test intent:
- Reject ship outputs with whitespace-only executed checks or next steps.
- Reject outputs with whitespace-only blocked checks."""
    verdict = str(output.get("release_qa_verdict") or "").strip().lower()
    executed_checks_raw = output.get("release_qa_executed_checks") or []
    blocked_checks_raw = output.get("release_qa_blocked_checks") or []
    next_steps_raw = output.get("release_qa_risk_next_steps") or []
    if verdict == "ship" and not _meaningful_entries(executed_checks_raw):
        return "ship release QA output must include meaningful executed checks"
    if not _meaningful_entries(next_steps_raw):
        return "release QA must include meaningful risk next steps"
    if isinstance(blocked_checks_raw, list) and blocked_checks_raw and not _meaningful_entries(blocked_checks_raw):
        return "release QA blocked checks cannot be blank placeholders"
    return None

# custom_verifier_stage_id: run_agentic_release_qa
# custom_verifier_requirement_id: ship_verdict_requires_no_blocked_checks
# template_version: 1
# spec_fingerprint: cf8db0e1aa278387c8d5babe7cdf068f696b6b54a4655efe44f3a45046e79691
# implementation_version: none
def _custom_verifier_requirement_run_agentic_release_qa_ship_verdict_requires_no_blocked_checks(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: A ship verdict must not carry unresolved blocked checks or other outstanding QA issues forward.
Signals: release_qa_verdict, release_qa_blocked_checks
Implementation surfaces: verifier, tests
Hint pseudocode:
- Trim blocked_checks before validation.
- If release_qa_verdict is ship, require blocked_checks to be empty after trimming.
Test intent:
- Reject ship outputs that still include blocked checks.
- Accept ship outputs only when blocked checks are empty."""
    verdict = str(output.get("release_qa_verdict") or "").strip().lower()
    blocked_checks = _meaningful_entries(output.get("release_qa_blocked_checks"))
    if verdict == "ship" and blocked_checks:
        return "release QA cannot return ship while blocked checks remain"
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
    message = _custom_verifier_requirement_request_pre_merge_code_review_findings_require_meaningful_entries(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    message = _custom_verifier_requirement_request_pre_merge_code_review_approved_review_requires_no_findings(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: request_pre_merge_code_review
# custom_verifier_requirement_id: findings_include_severity_grouping
# template_version: 1
# spec_fingerprint: 3b84742beebc9a12109887b903e69e70e9796c58d0b8fb5bac951fa28b13292c
# implementation_version: none
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
    findings = _meaningful_entries(output.get("findings"))
    if not findings:
        return None
    severity_markers = ("critical", "high", "medium", "low", "major", "minor")
    for finding in findings:
        lowered = finding.lower()
        if not any(marker in lowered for marker in severity_markers):
            return "review findings must include an explicit severity marker"
    return None

# custom_verifier_stage_id: request_pre_merge_code_review
# custom_verifier_requirement_id: findings_require_meaningful_entries
# template_version: 1
# spec_fingerprint: 30b6c1be8813a69d6f16dda5b50146973b4341b4603f68ce17a7f5f279a070b9
# implementation_version: none
def _custom_verifier_requirement_request_pre_merge_code_review_findings_require_meaningful_entries(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: Review findings must contain meaningful non-empty entries when findings are provided.
Signals: review_status, findings
Implementation surfaces: verifier, tests
Hint pseudocode:
- Trim each finding string before validation.
- If review_status is changes_requested, reject findings that become empty after trimming.
Test intent:
- Reject changes_requested outputs whose findings are only blank strings."""
    review_status = str(output.get("review_status") or "").strip().lower()
    findings_raw = output.get("findings") or []
    if review_status == "changes_requested" and not _meaningful_entries(findings_raw):
        return "changes_requested review output must include meaningful findings"
    return None

# custom_verifier_stage_id: request_pre_merge_code_review
# custom_verifier_requirement_id: approved_review_requires_no_findings
# template_version: 1
# spec_fingerprint: 139801761cc44ce5025b1d59bfe8db77737228ed8a1fe3c5f9211c756a210f57
# implementation_version: none
def _custom_verifier_requirement_request_pre_merge_code_review_approved_review_requires_no_findings(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: An approved pre-merge review must not leave actionable findings behind.
Signals: review_status, findings
Implementation surfaces: verifier, tests
Hint pseudocode:
- Trim each finding string before validation.
- If review_status is approved, require findings to be empty after trimming.
Test intent:
- Reject approved review outputs that still include findings.
- Accept approved review outputs only when findings are empty."""
    review_status = str(output.get("review_status") or "").strip().lower()
    findings = _meaningful_entries(output.get("findings"))
    if review_status == "approved" and findings:
        return "approved review output must not include remaining findings"
    return None

def _run_custom_verifier_requirements_verify_completion(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_verify_completion_completion_evidence_lists_require_meaningful_entries(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    message = _custom_verifier_requirement_verify_completion_completion_requires_release_qa_and_review_approval(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: verify_completion
# custom_verifier_requirement_id: completion_evidence_lists_require_meaningful_entries
# template_version: 1
# spec_fingerprint: 462d7d54434103cde521ff7e6874c91bc755cb78994b06377bb01a7fa594152f
# implementation_version: none
def _custom_verifier_requirement_verify_completion_completion_evidence_lists_require_meaningful_entries(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: Completion evidence and risk lists must contain meaningful non-empty entries after trimming whitespace.
Signals: verification_passed, verification_evidence, remaining_risks, missing_verification_inputs
Implementation surfaces: verifier, tests
Hint pseudocode:
- Trim each list entry before validation.
- Reject verification_evidence that becomes empty after trimming.
- If verification_passed is false, reject remaining_risks and missing_verification_inputs when they contain only blank placeholders.
Test intent:
- Reject passing completion output with blank evidence items.
- Reject failed completion output whose remaining_risks are only blank placeholders."""
    verification_evidence_raw = output.get("verification_evidence") or []
    if not _meaningful_entries(verification_evidence_raw):
        return "completion verification must include meaningful evidence entries"

    verification_passed = bool(output.get("verification_passed"))
    if not verification_passed:
        remaining_risks_raw = output.get("remaining_risks") or []
        if isinstance(remaining_risks_raw, list) and remaining_risks_raw and not _meaningful_entries(remaining_risks_raw):
            return "remaining_risks cannot contain only blank placeholders"
        missing_inputs_raw = output.get("missing_verification_inputs") or []
        if isinstance(missing_inputs_raw, list) and missing_inputs_raw and not _meaningful_entries(missing_inputs_raw):
            return "missing_verification_inputs cannot contain only blank placeholders"
    return None

# custom_verifier_stage_id: verify_completion
# custom_verifier_requirement_id: completion_requires_release_qa_and_review_approval
# template_version: 1
# spec_fingerprint: 53d6ce501f38df77f351dd6bf62e5020799ed908766ae7dbafda94381438e2f3
# implementation_version: none
def _custom_verifier_requirement_verify_completion_completion_requires_release_qa_and_review_approval(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.

Requirement: Completion may pass only after release QA reached ship and pre-merge review reached approved; otherwise the workflow must keep iterating.
Signals: state.release_qa_verdict, state.review_status, verification_passed, state.open_issues, state.release_qa_blocked_checks, state.release_qa_risk_next_steps, release_qa_risks_resolved
Implementation surfaces: verifier, tests
Hint pseudocode:
- If verification_passed is true, require persisted state.release_qa_verdict == ship.
- If verification_passed is true, require persisted state.review_status == approved.
- If verification_passed is true, reject the output when persisted open_issues is non-empty.
- If verification_passed is true and persisted release_qa_blocked_checks is non-empty, require release_qa_risks_resolved == true.
- If verification_passed is true and persisted release_qa_risk_next_steps still contains unresolved remediation work, require release_qa_risks_resolved == true and a non-empty release_qa_risk_resolution_summary.
Test intent:
- Reject passing completion output when release QA did not end in ship.
- Reject passing completion output when pre-merge review did not end in approved.
- Reject passing completion output when unresolved open_issues are still recorded in state.
- Reject passing completion output when release QA blocked checks are still unresolved.
- Accept passing completion output when release QA blocked checks were rechecked and explicitly resolved."""
    if not bool(output.get("verification_passed")):
        return None

    state = state or {}
    if str(state.get("release_qa_verdict") or "").strip().lower() != "ship":
        return "completion cannot pass before release QA reaches ship"
    if str(state.get("review_status") or "").strip().lower() != "approved":
        return "completion cannot pass before pre-merge review reaches approved"
    if _meaningful_entries(state.get("open_issues")):
        return "completion cannot pass while open_issues remain in state"

    blocked_checks = _meaningful_entries(state.get("release_qa_blocked_checks"))
    unresolved_next_steps = _meaningful_entries(state.get("release_qa_risk_next_steps"))
    risks_resolved = bool(output.get("release_qa_risks_resolved"))
    risk_resolution_summary = str(output.get("release_qa_risk_resolution_summary") or "").strip()
    if blocked_checks and not risks_resolved:
        return "completion cannot pass while release QA blocked checks remain unresolved"
    if unresolved_next_steps and not risks_resolved:
        return "completion cannot pass while release QA next steps remain unresolved"
    if risks_resolved and not risk_resolution_summary:
        return "resolved release QA risks require a risk resolution summary"
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
