from __future__ import annotations

import os
import re
import json

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
 'design_summary': 'string',
 'design_path': 'string',
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
 {'output_key': 'design_path',
  'operator': 'truthy',
  'value': None,
  'message': 'Brainstorming must return the design document path.'},
 {'output_key': 'design_path',
  'operator': 'path_exists',
  'value': None,
  'message': 'Brainstorming must create the design document before continuing.'},
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
 {'id': 'design_path_repo_policy',
  'template': 'repo_path_policy',
  'output_key': 'design_path',
  'message': 'design_path must point to a Markdown document under docs/superpowers/specs/ and must '
             'not point at docs/superpowers/plans/ artifacts.',
  'required_prefix': 'docs/superpowers/specs/',
  'forbidden_prefixes': ['docs/superpowers/plans/'],
  'required_suffix': '.md'}],
        observation=observation,
        repo_root=repo_root,
        state=state,
    )
    if not result["passed"]:
        return result
    output = observation.get("structured_output") or {}
    custom_error = _run_custom_verifier_requirements_run_brainstorming(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if custom_error is not None:
        return _fail(custom_error, run_id, step_id, state)
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
        verifier_rules=[{'output_key': 'authorization_summary',
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
 {'output_key': 'open_questions',
  'operator': 'empty',
  'value': None,
  'message': 'Planning open_questions must be empty before implementation can begin.'},
 {'output_key': 'execution_mode',
  'operator': 'truthy',
  'value': None,
  'message': 'Implementation planning must return an explicit execution_mode.'},
 {'output_key': 'execution_mode',
  'operator': 'one_of',
  'value': ['subagent-driven'],
  'message': 'Implementation planning must record execution_mode as subagent-driven.'}],
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
        optional_schema={'agent_device_status': 'string',
 'agent_device_commands': 'string[]',
 'agent_device_artifacts': 'string[]',
 'agent_device_session': 'string',
 'agent_device_replay_suite': 'string',
 'agent_device_cli_version': 'string',
 'agent_device_observed_device': 'string',
 'agent_device_observed_app_id': 'string',
 'agent_device_runner_status': 'string',
 'agent_device_execution_receipt': 'string'},
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
        run_id=run_id,
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
 'changes_requested': 'boolean'},
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
 'remaining_risks': 'string[]'},
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

def _run_custom_verifier_requirements_run_brainstorming(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    errors: list[str] = []
    message = _custom_verifier_requirement_run_brainstorming_ui_visual_inputs_require_meaningful_text(
        output=output,
        state=state,
        repo_root=repo_root,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: run_brainstorming
# custom_verifier_requirement_id: ui_visual_inputs_require_meaningful_text
# template_version: 1
# spec_fingerprint: 9ee6a2178cfe77bdaa5f514d3381840d9015ab3babb4891a8f37398a1de7d037
# implementation_version: 1
def _custom_verifier_requirement_run_brainstorming_ui_visual_inputs_require_meaningful_text(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: When a UI surface is affected, visual QA inputs must contain meaningful non-whitespace text rather than placeholder whitespace.
Signals: ui_surface_affected, visual_spec_detail_summary, design_comparison_source, runtime_visual_comparison_scope
Implementation surfaces: verifier, tests
Implementation notes: Normalize each required visual-QA input with trim semantics and fail closed when UI impact is true but any input is missing or whitespace-only.
Hint pseudocode:
- If ui_surface_affected is not true, do not apply this UI-specific requirement.
- When ui_surface_affected is true, require visual_spec_detail_summary, design_comparison_source, and runtime_visual_comparison_scope to contain non-whitespace text.
Test intent:
- Reject UI-impacting brainstorming output whose visual-QA inputs are whitespace-only.
- Accept non-UI brainstorming output without visual-QA inputs.
- Accept UI-impacting brainstorming output with meaningful visual-QA inputs."""
    _ = state, repo_root
    if output.get("ui_surface_affected") is not True:
        return None
    required_inputs = (
        ("visual_spec_detail_summary", "visual_spec_detail_summary"),
        ("design_comparison_source", "design_comparison_source"),
        ("runtime_visual_comparison_scope", "runtime_visual_comparison_scope"),
    )
    for key, label in required_inputs:
        if not str(output.get(key) or "").strip():
            return f"UI-impacting brainstorming requires meaningful {label}"
    return None

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
# spec_fingerprint: 73f244478bd06614e9485361d0e5d4963337bdea520f04ffb33a7c29566340d1
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
- Require each artifact path to be a relative, canonical, regular UTF-8 Markdown file under docs/superpowers/specs/; reject absolute paths, parent-directory traversal, and symlink traversal.
- Reject empty artifact files and deduplicate by canonical path, not only by the submitted string.
- Require each artifact's Markdown content to name the single perspective encoded by its canonical path.
- Require the combined artifact paths to clearly cover development, design, and testing review outputs.
 - Require three non-empty subagent summaries that map one-to-one to development, design, and testing instead of duplicating one perspective.
 - Reject repeated summaries or repeated artifact paths when they are being used to fake independent review coverage.
Test intent:
- Reject review output that provides review summaries without artifact paths.
- Reject review output whose artifact paths do not exist or do not cover development, design, and testing.
 - Reject review output that repeats one summary or one artifact path while still claiming three independent perspectives.
- Accept review output that hands in concrete review artifacts for all three perspectives."""
    summaries = _meaningful_entries(output.get("spec_review_subagent_summaries"))
    artifact_paths = _meaningful_entries(output.get("spec_review_artifact_paths"))
    if len(summaries) < 3:
        return "spec_review_subagent_summaries must contain at least three concrete review summaries"
    if len(artifact_paths) < 3:
        return "spec_review_artifact_paths must contain at least three concrete artifact paths"
    if len(summaries) != 3:
        return "spec_review_subagent_summaries must map one-to-one to development, design, and testing reviews"
    if len(artifact_paths) != 3:
        return "spec_review_artifact_paths must map one-to-one to development, design, and testing reviews"
    if len({summary.strip().lower() for summary in summaries}) != len(summaries):
        return "spec_review_subagent_summaries must be unique across development, design, and testing reviews"
    if len({artifact_path.strip().lower() for artifact_path in artifact_paths}) != len(artifact_paths):
        return "spec_review_artifact_paths must be unique across development, design, and testing reviews"

    expected_perspectives = {"development", "design", "testing"}
    try:
        repo_root_path = Path(repo_root).expanduser().resolve(strict=True)
        artifact_root = (repo_root_path / "docs/superpowers/specs").resolve(strict=True)
    except (OSError, ValueError):
        return "spec review artifact root is unavailable"
    artifact_perspectives: set[str] = set()
    canonical_artifacts: set[Path] = set()
    for artifact_path in artifact_paths:
        artifact = Path(artifact_path)
        if artifact.is_absolute() or any(part in ("", ".", "..") for part in artifact.parts):
            return "spec review artifact paths must be relative and must not contain parent-directory traversal"
        if artifact.suffix.lower() != ".md":
            return "spec review artifacts must be Markdown files"
        candidate = repo_root_path / artifact
        current_path = repo_root_path
        for part in artifact.parts:
            current_path = current_path / part
            if current_path.is_symlink():
                return "spec review artifacts must not traverse symlinks"
        try:
            canonical = candidate.resolve(strict=True)
        except (OSError, ValueError):
            return f"spec review artifact does not exist: {artifact_path}"
        try:
            canonical.relative_to(artifact_root)
        except ValueError:
            return "spec review artifacts must live under docs/superpowers/specs/"
        if not canonical.is_file():
            return f"spec review artifact is not a regular file: {artifact_path}"
        if canonical in canonical_artifacts:
            return "spec review artifact paths must resolve to unique files"
        canonical_artifacts.add(canonical)
        artifact_text = _read_safe_repo_text(repo_root, artifact_path)
        if artifact_text is None:
            return f"spec review artifact cannot be read as UTF-8 Markdown: {artifact_path}"
        if not artifact_text.strip():
            return f"spec review artifact is empty: {artifact_path}"
        perspective = _extract_single_review_perspective(canonical.relative_to(repo_root_path).as_posix())
        if perspective is None:
            return f"spec review artifact must name exactly one review perspective: {artifact_path}"
        if perspective not in artifact_text.lower():
            return f"spec review artifact content must name its review perspective: {artifact_path}"
        artifact_perspectives.add(perspective)

    summary_perspectives: set[str] = set()
    for summary in summaries:
        perspective = _extract_single_review_perspective(summary)
        if perspective is None:
            return f"spec review summary must name exactly one review perspective: {summary}"
        summary_perspectives.add(perspective)

    missing_artifact_perspectives = expected_perspectives - artifact_perspectives
    if missing_artifact_perspectives:
        joined = ", ".join(sorted(missing_artifact_perspectives))
        return f"spec review artifacts must clearly cover these perspectives: {joined}"
    missing_summary_perspectives = expected_perspectives - summary_perspectives
    if missing_summary_perspectives:
        joined = ", ".join(sorted(missing_summary_perspectives))
        return f"spec review summaries must clearly cover these perspectives: {joined}"
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
# spec_fingerprint: 144e6bc8c2d448ab09f63e2f94efc6c87069fb3e12a03bd9a3a1054728fd040d
# implementation_version: none
def _custom_verifier_requirement_write_implementation_plan_planning_requires_subagent_execution_mode(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: This workflow may continue only when planning records subagent-driven execution as the selected approach and does not ask the user to choose a different execution style.
Signals: execution_mode, ready_for_implementation
Implementation surfaces: verifier, tests
Hint pseudocode:
- Normalize execution_mode to lowercase.
- Accept only subagent-driven as the implementation-ready mode.
- If execution_mode is inline or any other value, reject the output or require ready_for_implementation to remain false.
- If plan_update_summary, debugging_summary, or open_issues are present in state, require the revised planning output to acknowledge the replanning reason via plan_revision_reason.
Test intent:
- Reject planning outputs that pick inline execution while claiming implementation is ready.
- Accept planning outputs that record subagent-driven execution with a written plan.
    - Reject replanning output that ignores recorded plan-update or implementation-learned reasons when such context exists in state."""
    _ = repo_root
    execution_mode = str(output.get("execution_mode") or "").strip().lower()
    ready_for_implementation = output.get("ready_for_implementation")
    if ready_for_implementation is True and execution_mode != "subagent-driven":
        return "planning may be implementation-ready only when execution_mode is subagent-driven"
    if execution_mode and execution_mode != "subagent-driven" and ready_for_implementation is not False:
        return "planning must either use subagent-driven execution or remain not ready for implementation"

    state = state or {}
    replanning_context_present = bool(
        str(state.get("plan_update_summary") or "").strip()
        or str(state.get("debugging_summary") or "").strip()
        or _meaningful_entries(state.get("open_issues"))
    )
    if replanning_context_present:
        has_plan_revision_reason = bool(str(output.get("plan_revision_reason") or "").strip())
        if not has_plan_revision_reason:
            return "planning must acknowledge replanning context via plan_revision_reason"
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
    raw_open_issues = output.get("open_issues")
    if isinstance(raw_open_issues, list) and any(
        not isinstance(item, str) or not item.strip() for item in raw_open_issues
    ):
        return "open_issues must contain only meaningful entries"
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
    run_id: str,
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
    message = _custom_verifier_requirement_run_agentic_release_qa_required_agent_device_evidence(
        output=output,
        state=state,
        repo_root=repo_root,
        run_id=run_id,
    )
    if message:
        errors.append(message)
    return "; ".join(errors) if errors else None

# custom_verifier_stage_id: run_agentic_release_qa
# custom_verifier_requirement_id: ui_visual_qa_evidence
# template_version: 1
# spec_fingerprint: 3bb809aee6fd54a3cdc789f8d6bf76bf1743c04a65df2a69cdeb955e6b6bbf1d
# implementation_version: 1
def _custom_verifier_requirement_run_agentic_release_qa_ui_visual_qa_evidence(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

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
    persisted = state if isinstance(state, dict) else {}
    if persisted.get("ui_surface_affected") is not True:
        return None
    if not all(
        isinstance(persisted.get(key), str) and persisted[key].strip()
        for key in ("design_comparison_source", "runtime_visual_comparison_scope")
    ):
        return None
    evidence = _meaningful_entries(output.get("release_qa_executed_checks"))
    evidence += _meaningful_entries(output.get("release_qa_blocked_checks"))
    evidence += _meaningful_entries(output.get("release_qa_artifacts"))
    visual_markers = (
        "visual",
        "pixel",
        "screenshot",
        "design comparison",
        "visual diff",
        "snapshot diff",
    )
    if not any(
        any(marker in entry.lower() for marker in visual_markers)
        for entry in evidence
    ):
        return "UI-impacting release QA must report executed or blocked visual comparison evidence"
    return None

# custom_verifier_stage_id: run_agentic_release_qa
# custom_verifier_requirement_id: release_qa_lists_require_meaningful_entries
# template_version: 1
# spec_fingerprint: 78384d14f12d4eea4433aaa5e8d734ff7e90f28f4c458a096aa46a0a89fdd95d
# implementation_version: 1
def _custom_verifier_requirement_run_agentic_release_qa_release_qa_lists_require_meaningful_entries(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

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
    verdict = str(output.get("release_qa_verdict") or "").strip().lower()
    for key, label in (
        ("release_qa_executed_checks", "executed checks"),
        ("release_qa_risk_next_steps", "risk next steps"),
    ):
        raw_value = output.get(key)
        if not isinstance(raw_value, list) or not _meaningful_entries(raw_value):
            return f"release QA {label} must contain meaningful entries"
    raw_blocked = output.get("release_qa_blocked_checks")
    if not isinstance(raw_blocked, list):
        return "release QA blocked checks must be a list"
    if any(not isinstance(item, str) or not item.strip() for item in raw_blocked):
        return "release QA blocked checks must contain only meaningful entries"
    if verdict not in {"ship", "do_not_ship"}:
        return "release QA verdict must be ship or do_not_ship"
    return None

# custom_verifier_stage_id: run_agentic_release_qa
# custom_verifier_requirement_id: ship_verdict_requires_no_blocked_checks
# template_version: 1
# spec_fingerprint: 51a4ebc03a2f99b5f9b570111733a55e752bf3bec6ac9721bae16a70b88a242f
# implementation_version: 1
def _custom_verifier_requirement_run_agentic_release_qa_ship_verdict_requires_no_blocked_checks(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: A ship verdict must not carry unresolved blocked checks or other outstanding QA issues forward.
Signals: release_qa_verdict, release_qa_blocked_checks
Implementation surfaces: verifier, tests
Hint pseudocode:
- Trim blocked_checks before validation.
- If release_qa_verdict is ship, require blocked_checks to be empty after trimming.
Test intent:
- Reject ship outputs that still include blocked checks.
- Accept ship outputs only when blocked checks are empty."""
    _ = state, repo_root
    verdict = str(output.get("release_qa_verdict") or "").strip().lower()
    blocked_checks = _meaningful_entries(output.get("release_qa_blocked_checks"))
    if verdict == "ship" and blocked_checks:
        return "release QA cannot return ship while blocked checks remain"
    return None

# custom_verifier_stage_id: run_agentic_release_qa
# custom_verifier_requirement_id: required_agent_device_evidence
# template_version: 1
# spec_fingerprint: bfdeacb7bb30ca732748c59b337aa65dd0a07e055fce98d915bf61526cc768d3
# implementation_version: 1
def _custom_verifier_requirement_run_agentic_release_qa_required_agent_device_evidence(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
    run_id: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: When agent_device_mode is required, release QA must prove that agent-device ran successfully with meaningful commands and artifact evidence; off or empty mode must not create a device gate.
Signals: context.agent_device_mode, context.agent_device_expected_version, context.agent_device_app_id, context.agent_device_artifact_path, context.agent_device_device, context.agent_device_evidence_dir, agent_device_status, agent_device_commands, agent_device_artifacts, agent_device_cli_version, agent_device_observed_device, agent_device_observed_app_id, agent_device_runner_status, agent_device_execution_receipt, release_qa_target_scope, release_qa_blocked_checks
Implementation surfaces: verifier, state, tests
Implementation notes: The verifier must read the persisted workflow context, fail closed only for required mode, require the declared version/app/artifact/device/evidence inputs, require structured host observations for the actual CLI version, device, app, and runner status, require a bounded JSON execution receipt tied to the current workflow run, require runner-preparation evidence before device operations, require regular build and evidence files, and reject unsafe artifact paths. It must not require the CLI or device when mode is off or empty; command execution remains a host responsibility, while the verifier validates the returned observations, receipt, and bounded files.
Hint pseudocode:
- Read context.agent_device_mode from persisted state and normalize whitespace/case.
- If the mode is not required, return no device-specific verifier error.
- When required, require context to identify the expected CLI version, app, build artifact, target device, and evidence directory.
- When required, require agent_device_status to equal succeeded, agent_device_commands to contain meaningful entries including runner preparation before device operations, agent_device_artifacts to contain safe relative paths under the repository, and release_qa_target_scope to identify the app/build/device target.
- Require agent_device_cli_version to exactly match the expected version, agent_device_observed_device to exactly match the configured target device, agent_device_observed_app_id to exactly match the configured app id, and agent_device_runner_status to equal succeeded.
- Require the declared build artifact and every evidence artifact to exist as regular non-symlink files under the repository and evidence directory.
- Require agent_device_execution_receipt to point to a regular JSON file under the evidence directory whose run_id, status, CLI version, device, app, runner status, commands, build artifact, and artifacts match the current host observations and workflow run.
- When session or replay suite is configured, require the reported values and corresponding receipt values to exactly match the configured values.
- Reject required-mode output when release_qa_blocked_checks contains meaningful unresolved device blockers.
- Keep actual CLI command execution in the workflow host/agent, and pass its observed version/device/app/runner results plus bounded artifact paths into the verifier.
Test intent:
- Accept release QA with agent_device_mode off and no device output.
- Reject required mode when agent-device status, commands, or artifacts are missing.
- Reject required mode when agent-device status is blocked or failed.
- Reject required mode when version, app, build artifact, target device, or evidence destination is missing.
- Reject required mode when an artifact path is absolute, traverses a parent directory, or bypasses the repository boundary.
- Reject required mode when observed CLI/device/app/runner evidence is missing or mismatched.
- Reject required mode when the declared build or evidence artifact is missing or not a regular file.
- Reject required mode when the execution receipt is missing, malformed, from another run, or inconsistent with the reported host evidence.
- Accept required mode when status, commands, artifacts, host observations, target scope, and release QA checks are meaningful."""
    context = state.get("context") if isinstance(state, dict) else {}
    context = context if isinstance(context, dict) else {}
    raw_mode = context.get("agent_device_mode")
    if raw_mode is not None and not isinstance(raw_mode, str):
        return "agent_device_mode must be a string when provided"
    mode = (raw_mode or "").strip().lower()
    if mode in {"", "off"}:
        return None
    if mode != "required":
        return "agent_device_mode must be off, required, or empty"

    required_context = (
        ("agent_device_expected_version", "expected CLI version"),
        ("agent_device_app_id", "app id"),
        ("agent_device_artifact_path", "build artifact"),
        ("agent_device_device", "target device"),
        ("agent_device_evidence_dir", "evidence directory"),
    )
    missing_context = []
    for key, label in required_context:
        value = context.get(key)
        if not isinstance(value, str) or not value.strip():
            missing_context.append(label)
    if missing_context:
        return "required agent-device QA is missing " + ", ".join(missing_context)

    def safe_device_path(raw_path: object) -> Path | None:
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None
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
        try:
            repo = Path(repo_root).expanduser().resolve(strict=True)
            current = repo
            for part in parts:
                current = current / part
                if current.is_symlink():
                    return None
            resolved = repo.joinpath(*parts).resolve(strict=False)
            resolved.relative_to(repo)
            return resolved
        except (OSError, RuntimeError, ValueError):
            return None

    build_artifact_input = context["agent_device_artifact_path"].strip()
    build_artifact = safe_device_path(build_artifact_input)
    if build_artifact is None:
        return "required agent-device build artifact must be a safe relative repository path"
    if not build_artifact.is_file() or build_artifact.is_symlink():
        return "required agent-device build artifact must be an existing regular file"

    status = output.get("agent_device_status")
    if not isinstance(status, str) or status.strip().lower() != "succeeded":
        return "required agent-device QA must report agent_device_status=succeeded"

    observed_pairs = (
        ("agent_device_cli_version", "agent_device_expected_version", "CLI version"),
        ("agent_device_observed_device", "agent_device_device", "target device"),
        ("agent_device_observed_app_id", "agent_device_app_id", "app id"),
    )
    for output_key, context_key, label in observed_pairs:
        observed = output.get(output_key)
        expected = context.get(context_key)
        if not isinstance(observed, str) or not observed.strip():
            return f"required agent-device QA must report observed {label}"
        if observed.strip() != expected.strip():
            return f"observed {label} does not match the configured target"
    runner_status = output.get("agent_device_runner_status")
    if not isinstance(runner_status, str) or runner_status.strip().lower() != "succeeded":
        return "required agent-device QA must report agent_device_runner_status=succeeded"

    commands = _meaningful_entries(output.get("agent_device_commands"))
    if not commands:
        return "required agent-device QA must report meaningful executed commands"
    command_indexes = [command.lower() for command in commands]
    preparation_index = next(
        (
            index
            for index, command in enumerate(command_indexes)
            if re.search(r"\bprepare\b", command)
            and re.search(r"\brunner\b", command)
        ),
        None,
    )
    operation_pattern = re.compile(
        r"\b(snapshot|act|press|click|fill|scroll|swipe|type|tap|long-press|back|alert|batch|wait|get|is|screenshot|logs?|perf|trace|replay|test|close)\b"
    )
    operation_indexes = [
        index
        for index, command in enumerate(command_indexes)
        if operation_pattern.search(command)
    ]
    if operation_indexes and preparation_index is None:
        return "required agent-device QA must prepare the iOS runner before device operations"
    if operation_indexes and preparation_index is not None and any(
        index < preparation_index for index in operation_indexes
    ):
        return "required agent-device QA must prepare the iOS runner before device operations"

    artifacts = _meaningful_entries(output.get("agent_device_artifacts"))
    if not artifacts:
        return "required agent-device QA must report meaningful artifact paths"
    evidence_root = safe_device_path(context["agent_device_evidence_dir"].strip())
    if evidence_root is None or not evidence_root.is_dir() or evidence_root.is_symlink():
        return "required agent-device QA evidence directory must be an existing directory"
    for artifact_path in artifacts:
        safe_artifact = safe_device_path(artifact_path)
        if safe_artifact is None:
            return "required agent-device artifact paths must be safe relative repository paths"
        try:
            safe_artifact.relative_to(evidence_root)
        except ValueError:
            return "required agent-device artifacts must remain under the evidence directory"
        if not safe_artifact.is_file() or safe_artifact.is_symlink():
            return "required agent-device artifacts must be existing regular files"

    receipt_raw = output.get("agent_device_execution_receipt")
    receipt_path = safe_device_path(receipt_raw)
    if receipt_path is None or receipt_path.suffix.lower() != ".json":
        return "required agent-device execution receipt must be a safe relative JSON path"
    try:
        receipt_path.relative_to(evidence_root)
    except ValueError:
        return "required agent-device execution receipt must remain under the evidence directory"
    receipt_text = _read_safe_repo_text(repo_root, receipt_raw)
    if receipt_text is None:
        return "required agent-device execution receipt must be an existing bounded UTF-8 JSON file"
    try:
        receipt = json.loads(receipt_text)
    except (TypeError, ValueError):
        return "required agent-device execution receipt must contain valid JSON"
    if not isinstance(receipt, dict):
        return "required agent-device execution receipt must contain a JSON object"
    if receipt.get("schema_version") != 1:
        return "required agent-device execution receipt has an unsupported schema version"
    if receipt.get("run_id") != run_id:
        return "required agent-device execution receipt must belong to the current workflow run"
    if receipt.get("status") != "succeeded":
        return "required agent-device execution receipt must report succeeded status"
    receipt_pairs = (
        ("cli_version", output["agent_device_cli_version"].strip()),
        ("device", output["agent_device_observed_device"].strip()),
        ("app_id", output["agent_device_observed_app_id"].strip()),
        ("runner_status", "succeeded"),
        ("build_artifact", build_artifact_input),
    )
    for receipt_key, expected in receipt_pairs:
        if receipt.get(receipt_key) != expected:
            return f"agent-device execution receipt {receipt_key} does not match the observed evidence"
    if receipt.get("commands") != commands:
        return "agent-device execution receipt commands do not match the reported commands"
    if receipt.get("artifacts") != artifacts:
        return "agent-device execution receipt artifacts do not match the reported artifacts"

    for output_key, context_key, receipt_key, label in (
        ("agent_device_session", "agent_device_session", "session", "session"),
        ("agent_device_replay_suite", "agent_device_replay_suite", "replay_suite", "replay suite"),
    ):
        configured = context.get(context_key)
        reported = output.get(output_key)
        if isinstance(configured, str) and configured.strip():
            if not isinstance(reported, str) or reported.strip() != configured.strip():
                return f"required agent-device QA must report the configured {label} exactly"
        if isinstance(reported, str) and reported.strip():
            if receipt.get(receipt_key) != reported.strip():
                return f"agent-device execution receipt {label} does not match the reported evidence"

    target_scope = output.get("release_qa_target_scope")
    if not isinstance(target_scope, str) or not target_scope.strip():
        return "required agent-device QA must identify the app, build, or device target"

    blocked_checks = _meaningful_entries(output.get("release_qa_blocked_checks"))
    device_blocker_markers = (
        "agent-device",
        "agent device",
        "device qa",
        "runner",
        "signing",
        "replay divergence",
    )
    if any(
        any(marker in check.lower() for marker in device_blocker_markers)
        for check in blocked_checks
    ):
        return "required agent-device QA cannot report succeeded while device blockers remain"
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
# spec_fingerprint: e3dbaa5d14538d0b1bb91ba4dc6cd09e2405a38363f89aa82a343b5a05607bd7
# implementation_version: none
def _custom_verifier_requirement_request_pre_merge_code_review_findings_include_severity_grouping(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: Non-empty review findings must make severity explicit with a stable prefix and keep findings grouped by descending severity so the workflow can distinguish major merge blockers from lower-risk notes.
Signals: review_status, findings
Implementation surfaces: verifier, tests
Hint pseudocode:
- Skip the requirement when findings is empty.
- Require each finding string to begin with an explicit severity prefix such as critical:, important:, high:, medium:, low:, major:, minor:, blocker:, p0:, or p1:.
- Reject findings whose severity is only implied in prose or negated by surrounding text.
- Reject findings that jump from lower severity back to higher severity later in the list.
Test intent:
- Reject change-requested findings that omit a severity prefix.
- Accept findings that carry an explicit severity prefix.
- Reject findings that only mention severity in prose without a stable prefix.
- Reject findings whose order is not grouped from higher severity to lower severity."""
    findings = _meaningful_entries(output.get("findings"))
    if not findings:
        return None

    previous_rank: int | None = None
    for finding in findings:
        if not _has_explicit_severity_prefix(finding):
            return "review findings must start with an explicit severity prefix"
        severity = _extract_severity_prefix(finding)
        if severity is None:
            return "review findings must use a supported severity prefix"
        current_rank = _severity_rank(severity)
        if previous_rank is not None and current_rank < previous_rank:
            return "review findings must stay grouped from higher severity to lower severity"
        previous_rank = current_rank
    return None

# custom_verifier_stage_id: request_pre_merge_code_review
# custom_verifier_requirement_id: findings_require_meaningful_entries
# template_version: 1
# spec_fingerprint: e8978ec2c899daa1028c1c917f1cb71543222d5d13f93d87aa11c7d556bfc0f5
# implementation_version: none
def _custom_verifier_requirement_request_pre_merge_code_review_findings_require_meaningful_entries(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

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
# spec_fingerprint: 8cae2e626592a30e376046bd8a287a36f5a23e278817a22584cd6113fa9464e0
# implementation_version: none
def _custom_verifier_requirement_request_pre_merge_code_review_approved_review_requires_no_findings(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

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
        return "approved review output must not include actionable findings"
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
# spec_fingerprint: a2b43b3870a0450db56f0ad7229c17846f5e525b1d0842024c7a580ccc88c4b9
# implementation_version: none
def _custom_verifier_requirement_verify_completion_completion_evidence_lists_require_meaningful_entries(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: Completion evidence and risk lists must contain meaningful non-empty entries after trimming whitespace.
Signals: verification_passed, verification_evidence, remaining_risks
Implementation surfaces: verifier, tests
Hint pseudocode:
- Trim each list entry before validation.
- Reject verification_evidence that becomes empty after trimming.
- If verification_passed is false, reject remaining_risks when they contain only blank placeholders.
Test intent:
- Reject passing completion output with blank evidence items.
- Reject failed completion output whose remaining_risks are only blank placeholders."""
    evidence_raw = output.get("verification_evidence") or []
    if not _meaningful_entries(evidence_raw):
        return "completion verification must include meaningful evidence entries"
    if not bool(output.get("verification_passed")):
        remaining_risks_raw = output.get("remaining_risks") or []
        if isinstance(remaining_risks_raw, list) and remaining_risks_raw and not _meaningful_entries(remaining_risks_raw):
            return "remaining_risks cannot contain only blank placeholders"
    return None

# custom_verifier_stage_id: verify_completion
# custom_verifier_requirement_id: completion_requires_release_qa_and_review_approval
# template_version: 1
# spec_fingerprint: 537d399997dc71845f58cc033992c5e793781a96efb6abfdc51a60721d159605
# implementation_version: none
def _custom_verifier_requirement_verify_completion_completion_requires_release_qa_and_review_approval(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    """Custom verifier scaffold generated from stages[].custom_verifier_requirements.
Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
If reuse is needed, import stable helpers from shared modules outside verifiers.py.
Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.

Requirement: Completion may pass only after release QA reached ship and pre-merge review reached approved; otherwise the workflow must keep iterating.
Signals: state.release_qa_verdict, state.review_status, verification_passed, state.open_issues, state.release_qa_blocked_checks, release_qa_risks_resolved
Implementation surfaces: verifier, tests
Hint pseudocode:
- If verification_passed is true, require persisted state.release_qa_verdict == ship.
- If verification_passed is true, require persisted state.review_status == approved.
- If verification_passed is true, reject the output when persisted open_issues is non-empty.
- If verification_passed is true and persisted release_qa_blocked_checks is non-empty, require release_qa_risks_resolved == true.
- If release_qa_risks_resolved is true, require a non-empty release_qa_risk_resolution_summary that explains the fresh recheck evidence.
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
    for state_key in ("open_issues", "release_qa_blocked_checks"):
        raw_entries = state.get(state_key)
        if raw_entries is not None and (
            not isinstance(raw_entries, list)
            or any(not isinstance(item, str) or not item.strip() for item in raw_entries)
        ):
            return f"{state_key} must contain only meaningful entries"
    if _meaningful_entries(state.get("open_issues")):
        return "completion cannot pass while open_issues remain in state"

    blocked_checks = _meaningful_entries(state.get("release_qa_blocked_checks"))
    risks_resolved = bool(output.get("release_qa_risks_resolved"))
    risk_resolution_summary = str(output.get("release_qa_risk_resolution_summary") or "").strip()
    if blocked_checks and not risks_resolved:
        return "completion cannot pass while release QA blocked checks remain unresolved"
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
    allowed_keys = set(required_schema) | set(optional_schema)
    unexpected_keys = [
        key for key in output
        if not isinstance(key, str) or key not in allowed_keys
    ]
    if unexpected_keys:
        unexpected = sorted(repr(key) for key in unexpected_keys)
        return _fail(f"unexpected structured_output keys: {unexpected}", run_id, step_id, state)
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
    return f"{key} has unsupported schema type: {schema_type}"


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
        text = _read_safe_repo_text(repo_root, actual)
        return None if text is not None and text.strip() else message
    return None if condition_matches(actual, operator, expected) else message


def _verifier_template_error(template: dict, output: dict, repo_root: str, state: dict | None) -> str | None:
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


def _min_count_from_constraint_error(actual, template: dict, state: dict | None, message: str) -> str | None:
    if not isinstance(actual, list):
        return message
    constraints = state.get("constraints") if isinstance(state, dict) else {}
    constraint_key = str(template.get("constraint_key") or "")
    raw_min_count = constraints.get(constraint_key) if isinstance(constraints, dict) else None
    default_min_count = template.get("default_min_count")
    min_count = raw_min_count if isinstance(raw_min_count, int) and not isinstance(raw_min_count, bool) and raw_min_count >= 0 else default_min_count
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
    if _safe_repo_file(repo_root, actual) is None:
        return message
    text = _read_safe_repo_text(repo_root, actual)
    if text is None or not text.strip():
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


def _artifact_list_policy_error(actual, template: dict, repo_root: str, message: str) -> str | None:
    if not isinstance(actual, list) or not actual:
        return message
    required_prefix = str(template.get("required_prefix") or "")
    allowed_suffixes = tuple(str(item).lower() for item in template.get("allowed_suffixes") or [])
    require_non_empty_content = bool(template.get("require_non_empty_content", True))
    for index, item in enumerate(actual):
        if not isinstance(item, str) or not item.strip():
            return f"{message}: invalid artifact at index {index}"
        candidate = _safe_repo_file(repo_root, item)
        if candidate is None:
            return f"{message}: invalid artifact at index {index}"
        repo = Path(repo_root).expanduser().resolve()
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
        if not condition_matches(output.get(when_key), str(when.get("operator") or ""), when.get("value")):
            return None
    findings = output.get(str(template.get("output_key") or ""))
    if not isinstance(findings, list):
        return message
    unresolved_terms = tuple(str(item).lower() for item in template.get("unresolved_terms") or [])
    resolved_terms = tuple(str(item).lower() for item in template.get("resolved_terms") or [])
    for finding in findings:
        if not isinstance(finding, str) or not finding.strip():
            return message
        lowered = finding.lower()
        unresolved = any(term and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered) for term in unresolved_terms)
        resolved = any(term and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered) for term in resolved_terms)
        if unresolved and not resolved:
            return f"{message}: unresolved findings present"
    return None


_MAX_SAFE_REPO_TEXT_BYTES = 512 * 1024


def _safe_repo_path(repo_root: str, raw_path: str) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    try:
        repo = Path(repo_root).expanduser().resolve()
        normalized = raw_path
        if normalized != normalized.strip() or "\\" in normalized or any(ord(char) < 32 for char in normalized) or normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
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
