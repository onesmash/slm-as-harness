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
 'ready_for_planning': 'boolean'},
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
 {'output_key': 'ready_for_planning',
  'operator': 'is_true',
  'value': None,
  'message': 'Brainstorming must declare the change ready for implementation planning.'},
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
             'and must not point at docs/superpowers/plans/ artifacts.',
  'required_prefix': 'docs/superpowers/specs/',
  'forbidden_prefixes': ['docs/superpowers/plans/'],
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

def verify_approve_plan(
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
        required_schema={'user_approved': 'boolean', 'additional_planning_needed': 'boolean'},
        optional_schema={'user_feedback': 'string'},
        verifier_rules=[],
        verifier_templates=[{'id': 'approved_clears_additional_planning',
  'template': 'conditional_equals',
  'output_key': 'additional_planning_needed',
  'message': 'If user_approved is true, additional_planning_needed must be false.',
  'when': {'output_key': 'user_approved', 'operator': 'is_true', 'value': None},
  'expected_value': False},
 {'id': 'rejected_requires_additional_planning',
  'template': 'conditional_equals',
  'output_key': 'additional_planning_needed',
  'message': 'If user_approved is false, additional_planning_needed must be true.',
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
- If plan_user_feedback, plan_update_summary, debugging_summary, or open_issues are present in state, require the revised planning output to acknowledge the replanning reason via plan_revision_reason or plan_summary.
Test intent:
- Reject planning outputs that pick inline execution while claiming implementation is ready.
- Accept planning outputs that record subagent-driven execution with a reviewed plan.
- Reject replanning output that ignores recorded user feedback or plan-update reasons when such context exists in state."""
    _ = repo_root
    state = state or {}
    execution_mode = _normalized_text(output.get("execution_mode")).lower()
    ready_for_implementation = output.get("ready_for_implementation") is True
    allowed_ready_modes = {"subagent-driven", "subagent-driven-development"}
    if ready_for_implementation and execution_mode not in allowed_ready_modes:
        return (
            "Implementation planning may continue only with a subagent-driven execution_mode "
            "when ready_for_implementation is true."
        )
    replanning_context = any(
        [
            _normalized_text(state.get("plan_user_feedback")),
            _normalized_text(state.get("plan_update_summary")),
            _normalized_text(state.get("debugging_summary")),
            _string_list_trimmed(state.get("open_issues")),
        ]
    )
    if replanning_context:
        revision_reason = _normalized_text(output.get("plan_revision_reason"))
        plan_summary = _normalized_text(output.get("plan_summary")).lower()
        summary_markers = ("revis", "replan", "feedback", "update", "issue", "debug", "owner", "follow-up")
        if not revision_reason and not any(marker in plan_summary for marker in summary_markers):
            return (
                "Replanning output must acknowledge recorded user feedback or implementation "
                "learned issues via plan_revision_reason or plan_summary."
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
    _ = state, repo_root
    tasks_completed = output.get("tasks_completed") is True
    remaining_tasks = _string_list_trimmed(output.get("remaining_tasks"))
    plan_updates_required = output.get("plan_updates_required") is True
    verification_passed = output.get("verification_passed") is True
    if tasks_completed and remaining_tasks:
        return "Implementation cannot set tasks_completed=true while remaining_tasks is non-empty."
    if not tasks_completed and not plan_updates_required and not remaining_tasks:
        return (
            "Implementation retries must list remaining_tasks unless they are explicitly routing "
            "back for plan updates."
        )
    if not verification_passed and not plan_updates_required:
        return (
            "Implementation verification cannot fail unless the output is explicitly routing "
            "back for plan updates."
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
    message = _custom_verifier_requirement_run_agentic_release_qa_release_qa_lists_require_meaningful_entries(
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
    ui_surface_affected = state.get("ui_surface_affected") is True
    design_comparison_source = _normalized_text(state.get("design_comparison_source"))
    runtime_visual_scope = _normalized_text(state.get("runtime_visual_comparison_scope"))
    if not (ui_surface_affected and design_comparison_source and runtime_visual_scope):
        return None
    evidence_lines = (
        _string_list_trimmed(output.get("release_qa_executed_checks"))
        + _string_list_trimmed(output.get("release_qa_blocked_checks"))
        + _string_list_trimmed(output.get("release_qa_artifacts"))
    )
    if not any(_looks_like_visual_evidence(item) for item in evidence_lines):
        return (
            "UI-impacting release QA must report explicit visual comparison evidence when "
            "design and runtime comparison inputs are available."
        )
    return None

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
    _ = state, repo_root
    verdict = _normalized_text(output.get("release_qa_verdict")).lower()
    executed_checks = _string_list_trimmed(output.get("release_qa_executed_checks"))
    risk_next_steps = _string_list_trimmed(output.get("release_qa_risk_next_steps"))
    if verdict == "ship" and not executed_checks:
        return "Release QA ship outputs must contain meaningful executed checks."
    if not risk_next_steps:
        return "Release QA outputs must contain meaningful risk-based next steps."
    if _list_has_only_blank_placeholders(output.get("release_qa_blocked_checks")):
        return "Release QA blocked checks must not contain only blank placeholders."
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
    findings = _string_list_trimmed(output.get("findings"))
    for finding in findings:
        if not _has_severity_marker(finding):
            return (
                "Review findings must include an explicit severity marker such as critical, "
                "high, medium, low, major, or minor."
            )
    return None

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
    _ = state, repo_root
    review_status = _normalized_text(output.get("review_status")).lower()
    findings = _string_list_trimmed(output.get("findings"))
    if review_status == "changes_requested" and not findings:
        return "Review findings must contain meaningful non-empty entries when changes are requested."
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
    _ = state, repo_root
    verification_passed = output.get("verification_passed") is True
    verification_evidence = _string_list_trimmed(output.get("verification_evidence"))
    if not verification_evidence:
        return "Completion verification must include meaningful verification evidence entries."
    if not verification_passed:
        if _list_has_only_blank_placeholders(output.get("remaining_risks")):
            return "remaining_risks must not contain only blank placeholders when verification fails."
        if _list_has_only_blank_placeholders(output.get("missing_verification_inputs")):
            return (
                "missing_verification_inputs must not contain only blank placeholders when "
                "verification fails."
            )
    return None

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
    _ = repo_root
    state = state or {}
    if output.get("verification_passed") is not True:
        return None
    release_qa_verdict = _normalized_text(state.get("release_qa_verdict")).lower()
    if release_qa_verdict != "ship":
        return "Completion cannot pass until release QA reaches a ship verdict in persisted state."
    review_status = _normalized_text(state.get("review_status")).lower()
    if review_status != "approved":
        return "Completion cannot pass until pre-merge review reaches approved in persisted state."
    if _string_list_trimmed(state.get("open_issues")):
        return "Completion cannot pass while persisted open_issues remains non-empty."
    release_qa_blocked_checks = _string_list_trimmed(state.get("release_qa_blocked_checks"))
    release_qa_risk_next_steps = _string_list_trimmed(state.get("release_qa_risk_next_steps"))
    release_qa_risks_resolved = output.get("release_qa_risks_resolved") is True
    release_qa_risk_resolution_summary = _normalized_text(output.get("release_qa_risk_resolution_summary"))
    if release_qa_blocked_checks and not release_qa_risks_resolved:
        return (
            "Completion cannot pass while persisted release QA blocked checks remain unresolved; "
            "set release_qa_risks_resolved only after rechecking them."
        )
    unresolved_release_qa_risk_steps = [
        step for step in release_qa_risk_next_steps if _looks_like_unresolved_release_qa_risk(step)
    ]
    if unresolved_release_qa_risk_steps and not release_qa_risks_resolved:
        return (
            "Completion cannot pass while persisted release QA risk next steps remain unresolved; "
            "set release_qa_risks_resolved only after rechecking them."
        )
    if release_qa_risks_resolved and not release_qa_risk_resolution_summary:
        return (
            "Completion must summarize how release QA blocked checks or risk next steps were "
            "resolved before passing final verification."
        )
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


def _normalized_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list_trimmed(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _normalized_text(item))]


def _list_has_only_blank_placeholders(value: object) -> bool:
    return isinstance(value, list) and bool(value) and not _string_list_trimmed(value)


def _looks_like_visual_evidence(value: object) -> bool:
    text = _normalized_text(value).lower()
    if not text:
        return False
    keywords = (
        "visual",
        "pixel",
        "screenshot",
        "figma",
        "design comparison",
        "diff",
        "snapshot",
        "mock",
        "baseline",
    )
    return any(keyword in text for keyword in keywords)


def _has_severity_marker(value: object) -> bool:
    text = _normalized_text(value).lower()
    if not text:
        return False
    markers = (
        "critical:",
        "high:",
        "medium:",
        "low:",
        "major:",
        "minor:",
        "[critical]",
        "[high]",
        "[medium]",
        "[low]",
        "[major]",
        "[minor]",
        "(critical)",
        "(high)",
        "(medium)",
        "(low)",
        "(major)",
        "(minor)",
    )
    return text.startswith(("critical ", "high ", "medium ", "low ", "major ", "minor ")) or any(
        marker in text for marker in markers
    )


def _looks_like_unresolved_release_qa_risk(value: object) -> bool:
    text = _normalized_text(value).lower()
    if not text:
        return False
    non_remediation_markers = (
        "proceed to code review",
        "no further action",
        "none",
        "no additional action",
        "continue to review",
        "continue to code review",
    )
    if any(marker in text for marker in non_remediation_markers):
        return False
    remediation_markers = (
        "resolve",
        "fix",
        "rerun",
        "re-run",
        "investigate",
        "capture",
        "verify",
        "confirm",
        "address",
        "remediate",
        "soak",
        "retry",
    )
    return any(marker in text for marker in remediation_markers)


def _fail(message: str, run_id: str, step_id: str, state: dict | None) -> VerifierResult:
    return make_verifier_result(
        passed=False,
        message=message,
        details={"run_id": run_id, "step_id": step_id, "state": state or {}},
    )
