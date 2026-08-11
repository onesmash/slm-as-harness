import sys
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = RUNTIME_ROOT.parent
REPO_ROOT = SKILL_ROOT.parents[1]
for _lib_root in (REPO_ROOT / '.venv' / 'lib', SKILL_ROOT / '.venv' / 'lib', REPO_ROOT.parent / '.venv' / 'lib'):
    _site_packages = next(_lib_root.glob('python*/site-packages'), None)
    if _site_packages is not None and str(_site_packages) not in sys.path:
        sys.path.insert(0, str(_site_packages))
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from workflows.ios_ai_assisted_development_flow import graphbuilder_runtime, state as workflow_state, verifiers


class IosAiAssistedDevelopmentFlowWorkflowGeneratedTests(unittest.TestCase):
    def _make_state(self, payload=None):
        if payload is not None:
            return workflow_state.deserialize_state(payload)
        return workflow_state.make_initial_state(
            {
                "task_input": {"goal": "generated workflow regression"},
                "context": {},
                "constraints": {},
            }
        )

    def test_brainstorming_requires_design_path(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Design package completed without a written design path.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The change should update one behavior '
                                                        'with no scope expansion.',
                       'design_presented': True,
                       'design_summary': 'Approved design summary.',
                       'open_questions': [],
                       'ready_for_subagent_review': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_brainstorming_rejects_skipped_clarification(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Design package completed without asking clarification questions.',
 'structured_output': {'clarification_questions': [],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'design_summary': 'Approved design summary.',
                       'design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
                       'open_questions': [],
                       'ready_for_subagent_review': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_brainstorming_accepts_completed_clarification(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming completed with clarification and a written design package.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'design_summary': 'Approved design summary.',
                       'design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
                       'ui_surface_affected': False,
                       'open_questions': [],
                       'ready_for_subagent_review': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_brainstorming_rejects_ui_change_without_visual_qa_inputs(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming completed a UI change without visual QA inputs.',
 'structured_output': {'clarification_questions': ['Which screen changes?'],
                       'clarification_answers_summary': 'The request updates a visible meeting UI '
                                                        'surface.',
                       'design_presented': True,
                       'design_summary': 'Approved UI design summary.',
                       'design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
                       'ui_surface_affected': True,
                       'open_questions': [],
                       'ready_for_subagent_review': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_approve_subagent_review_accepts_explicit_no(self):
        result = verifiers.verify_approve_subagent_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='approve_subagent_review',
            observation={'status': 'succeeded',
 'summary': 'The user declined subagent review.',
 'structured_output': {'subagent_review_approved': False,
                       'authorization_summary': 'The user declined independent development, '
                                                'design, and testing review subagents.',
                       'ready_for_spec_review': False}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_approve_subagent_review_accepts_explicit_yes(self):
        result = verifiers.verify_approve_subagent_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='approve_subagent_review',
            observation={'status': 'succeeded',
 'summary': 'The user approved subagent review.',
 'structured_output': {'subagent_review_approved': True,
                       'authorization_summary': 'Approved independent development, design, and '
                                                'testing review subagents.',
                       'ready_for_spec_review': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_run_spec_review_rejects_missing_spec_review_perspective(self):
        result = verifiers.verify_run_spec_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_spec_review',
            observation={'status': 'succeeded',
 'summary': 'Spec review completed without the design perspective.',
 'structured_output': {'spec_review_loop_completed': True,
                       'spec_review_perspectives': ['development', 'testing', 'testing'],
                       'spec_review_findings_summary': 'Development and testing reviews passed.',
                       'spec_review_subagent_summaries': ['Development review passed.',
                                                          'Testing review passed.',
                                                          'Second testing review passed.'],
                       'spec_review_artifact_paths': ['docs/superpowers/specs/2026-06-24-ios-change-development-review.md',
                                                      'docs/superpowers/specs/2026-06-24-ios-change-testing-review.md',
                                                      'docs/superpowers/specs/2026-06-24-ios-change-testing-review.md'],
                       'open_questions': [],
                       'ready_for_planning': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_brainstorming_rejects_non_spec_doc_path(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming tried to reuse a plan document as the design spec.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'design_summary': 'Approved design summary.',
                       'design_path': 'docs/superpowers/plans/2026-06-24-sample-plan.md',
                       'open_questions': [],
                       'ready_for_subagent_review': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_brainstorming_gate_failure_retries_brainstorming(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming tried to continue without clarification.',
 'structured_output': {'clarification_questions': [],
                       'clarification_answers_summary': '',
                       'design_presented': True,
                       'design_summary': 'Approved design summary.',
                       'design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
                       'open_questions': [],
                       'ready_for_subagent_review': True}},
            verifier_result={'passed': False,
 'checks': [{'name': 'clarification_questions',
             'passed': False,
             'message': 'Brainstorming must ask and record at least one clarification question '
                        'before continuing.'}]},
        )
        self.assertEqual(result.step_id, 'run_brainstorming')
        self.assertEqual(result.branch_kind, 'retry')

    def test_approve_subagent_review_success_routes_to_spec_review(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='approve_subagent_review',
            observation={'status': 'succeeded',
 'summary': 'The user approved subagent review.',
 'structured_output': {'subagent_review_approved': True,
                       'authorization_summary': 'Approved independent development, design, and '
                                                'testing review subagents.',
                       'ready_for_spec_review': True}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'run_spec_review')
        self.assertEqual(result.branch_kind, 'continue')

    def test_run_spec_review_gate_failure_retries_run_spec_review(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_spec_review',
            observation={'status': 'succeeded',
 'summary': 'Spec review tried to continue without concrete artifacts.',
 'structured_output': {'spec_review_loop_completed': True,
                       'spec_review_perspectives': ['development', 'design', 'testing'],
                       'spec_review_findings_summary': 'Development, design, and testing reviews '
                                                       'passed.',
                       'spec_review_subagent_summaries': ['Development review passed.',
                                                          'Design review passed.',
                                                          'Testing review passed.'],
                       'spec_review_artifact_paths': [],
                       'open_questions': [],
                       'ready_for_planning': True}},
            verifier_result={'passed': False,
 'checks': [{'name': 'spec_review_artifact_paths',
             'passed': False,
             'message': 'The workflow must return the concrete subagent review artifact paths.'}]},
        )
        self.assertEqual(result.step_id, 'run_spec_review')
        self.assertEqual(result.branch_kind, 'retry')

    def test_plan_requires_written_plan_path(self):
        result = verifiers.verify_write_implementation_plan(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning finished without recording the plan path.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': '',
                       'execution_mode': 'subagent-driven',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_plan_accepts_no_manual_review_requirement(self):
        result = verifiers.verify_write_implementation_plan(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning completed without a manual user review gate.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'execution_mode': 'subagent-driven',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_plan_rejects_inline_execution_mode(self):
        result = verifiers.verify_write_implementation_plan(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning picked inline execution while claiming readiness.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'execution_mode': 'inline',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_plan_accepts_subagent_execution_mode(self):
        result = verifiers.verify_write_implementation_plan(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning completed with a written plan and subagent-driven execution.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'execution_mode': 'subagent-driven',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_plan_rejects_replanning_without_reason(self):
        result = verifiers.verify_write_implementation_plan(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning revised the plan without acknowledging recorded replanning context.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'execution_mode': 'subagent-driven',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            state={'plan_update_summary': 'The prior implementation pass exposed a missing owner.'},
        )
        self.assertIs(result['passed'], False)

    def test_planning_not_ready_retries_planning(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning still has unresolved questions.',
 'structured_output': {'plan_summary': 'Need another planning pass.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'execution_mode': 'subagent-driven',
                       'open_questions': ['Confirm rollout constraints.'],
                       'ready_for_implementation': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'write_implementation_plan')
        self.assertEqual(result.branch_kind, 'retry')

    def test_planning_ready_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning completed with a written plan and ready execution mode.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'execution_mode': 'subagent-driven',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'continue')

    def test_implementation_requires_verification_commands(self):
        result = verifiers.verify_execute_implementation(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation finished without verification commands.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented the requested change.',
                       'changed_files': ['Zoom/Foo.swift'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': [],
                       'verification_commands': [],
                       'verification_passed': True,
                       'open_issues': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_implementation_success_routes_to_release_qa(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation completed successfully.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented the requested change.',
                       'changed_files': ['Zoom/Foo.swift'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': [],
                       'verification_commands': ['xcodebuild test -scheme ZoomClient'],
                       'verification_passed': True,
                       'open_issues': [],
                       'debugging_summary': 'No debugging detours were needed.',
                       'plan_updates_required': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'run_agentic_release_qa')
        self.assertEqual(result.branch_kind, 'continue')

    def test_implementation_plan_issue_routes_back_to_planning(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation found a missing architecture decision.',
 'structured_output': {'tasks_completed': False,
                       'implementation_summary': 'Stopped when the plan exposed an ownership gap.',
                       'changed_files': ['Zoom/Foo.swift'],
                       'completed_tasks': [],
                       'remaining_tasks': ['Clarify owner for shared presenter.'],
                       'verification_commands': ['xcodebuild test -scheme ZoomClient'],
                       'verification_passed': True,
                       'open_issues': ['Ownership of shared presenter is unclear.'],
                       'debugging_summary': 'Root cause traced to an unresolved plan assumption.',
                       'plan_updates_required': True,
                       'plan_update_summary': 'The plan needs an explicit owner for the shared '
                                              'presenter before implementation can continue.'}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'write_implementation_plan')
        self.assertEqual(result.branch_kind, 'retry')

    def test_implementation_rejects_completed_with_remaining_tasks(self):
        result = verifiers.verify_execute_implementation(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation claims completion with remaining tasks.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented most of the change.',
                       'changed_files': ['Zoom/Foo.swift'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': ['Task 2'],
                       'verification_commands': ['xcodebuild test -scheme ZoomClient'],
                       'verification_passed': True,
                       'open_issues': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_implementation_rejects_failed_verification(self):
        result = verifiers.verify_execute_implementation(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation failed verification without routing detail.',
 'structured_output': {'tasks_completed': False,
                       'implementation_summary': 'Implementation is incomplete.',
                       'changed_files': ['Zoom/Foo.swift'],
                       'completed_tasks': [],
                       'remaining_tasks': ['Fix failing tests.'],
                       'verification_commands': ['xcodebuild test -scheme ZoomClient'],
                       'verification_passed': False,
                       'open_issues': ['Tests are failing.']}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_unknown_verdict(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA returned an unknown verdict.',
 'structured_output': {'release_qa_target_scope': 'Changed meeting footer flow',
                       'release_qa_summary': 'QA pass summary.',
                       'release_qa_verdict': 'unknown',
                       'release_qa_executed_checks': ['Smoke test'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Clarify verdict.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_blocked_routes_to_unblocking(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'blocked',
 'summary': 'QA environment is unavailable.',
 'structured_output': {'blocked_reason': 'Simulator unavailable',
                       'missing_inputs': ['Working simulator environment']}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'repair')

    def test_release_qa_do_not_ship_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA found a ship blocker.',
 'structured_output': {'release_qa_target_scope': 'Crash flow on iPad simulator',
                       'release_qa_summary': 'A crash reproduces in the target flow.',
                       'release_qa_verdict': 'do_not_ship',
                       'release_qa_executed_checks': ['Crash reproduction'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Fix the crash before ship.'],
                       'release_qa_artifacts': []}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

    def test_release_qa_ship_routes_to_final_review(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA is ready for review.',
 'structured_output': {'release_qa_target_scope': 'Changed meeting footer flow on iPhone simulator',
                       'release_qa_summary': 'All targeted checks passed.',
                       'release_qa_verdict': 'ship',
                       'release_qa_executed_checks': ['Smoke', 'Regression'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Proceed to code review.'],
                       'release_qa_artifacts': []}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'request_pre_merge_code_review')
        self.assertEqual(result.branch_kind, 'continue')

    def test_review_changes_requested_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review requested changes.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'review_summary': 'One high-severity issue must be fixed.',
                       'findings': ['high: fix retain cycle in meeting footer'],
                       'changes_requested': True}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

    def test_review_approved_routes_to_completion_verification(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review approved the change.',
 'structured_output': {'review_status': 'approved',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'review_summary': 'No actionable findings remain.',
                       'findings': [],
                       'changes_requested': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'verify_completion')
        self.assertEqual(result.branch_kind, 'continue')

    def test_completion_verification_failed_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification found unresolved issues.',
 'structured_output': {'verification_passed': False,
                       'verification_summary': 'Need one more regression pass.',
                       'verification_evidence': ['xcodebuild test still missing target case'],
                       'remaining_risks': ['Target regression case not re-run'],
                       'release_qa_risks_resolved': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

    def test_completion_verification_requires_evidence(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification claimed success without evidence.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Everything looks good.',
                       'verification_evidence': [],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': True,
                       'release_qa_risk_resolution_summary': 'Resolved residual QA risks.'}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_success_completes_workflow(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification passed with fresh evidence.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'All completion checks passed.',
                       'verification_evidence': ['xcodebuild test -scheme ZoomClient',
                                                 'Manual smoke test on updated screen'],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'finalize_delivery_summary')
        self.assertEqual(result.branch_kind, 'complete')

    def test_release_qa_rejects_ship_with_risks_verdict(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA returned a forbidden residual-risk verdict.',
 'structured_output': {'release_qa_target_scope': 'Meeting footer flow',
                       'release_qa_summary': 'Core checks passed with unresolved residual risk.',
                       'release_qa_verdict': 'ship_with_risks',
                       'release_qa_executed_checks': ['Smoke', 'Regression'],
                       'release_qa_blocked_checks': ['Long-run soak'],
                       'release_qa_risk_next_steps': ['Resolve soak gap.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_requires_target_scope(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA omitted target scope.',
 'structured_output': {'release_qa_target_scope': '',
                       'release_qa_summary': 'QA pass summary.',
                       'release_qa_verdict': 'ship',
                       'release_qa_executed_checks': ['Smoke'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Proceed'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_blank_executed_checks(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA used blank executed checks.',
 'structured_output': {'release_qa_target_scope': 'Meeting footer flow',
                       'release_qa_summary': 'QA pass summary.',
                       'release_qa_verdict': 'ship',
                       'release_qa_executed_checks': ['   '],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['   '],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_blank_blocked_checks(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA used blank blocked checks placeholders.',
 'structured_output': {'release_qa_target_scope': 'Meeting footer flow',
                       'release_qa_summary': 'QA pass summary.',
                       'release_qa_verdict': 'do_not_ship',
                       'release_qa_executed_checks': ['Smoke'],
                       'release_qa_blocked_checks': ['   '],
                       'release_qa_risk_next_steps': ['Capture the missing soak-test result.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_missing_visual_evidence_when_ui_comparison_is_required(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA omitted visual comparison evidence for a UI-affecting change.',
 'structured_output': {'release_qa_target_scope': 'Meeting footer flow',
                       'release_qa_summary': 'Smoke and regression checks passed.',
                       'release_qa_verdict': 'ship',
                       'release_qa_executed_checks': ['Smoke test on updated meeting footer',
                                                      'Regression pass on navigation flow'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Proceed to code review.'],
                       'release_qa_artifacts': []}},
            state={'ui_surface_affected': True,
 'design_comparison_source': 'figma://meeting-footer',
 'runtime_visual_comparison_scope': 'Meeting footer on updated screen'},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_ship_with_blocked_checks(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA tried to ship with blocked checks still open.',
 'structured_output': {'release_qa_target_scope': 'Changed meeting footer flow on iPhone simulator',
                       'release_qa_summary': 'Core checks passed, but one visual confirmation is '
                                             'still blocked.',
                       'release_qa_verdict': 'ship',
                       'release_qa_executed_checks': ['Smoke', 'Regression'],
                       'release_qa_blocked_checks': ['Final screenshot diff confirmation'],
                       'release_qa_risk_next_steps': ['Resolve the blocked screenshot diff before '
                                                      'shipping.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_rejects_blank_findings(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review findings were blank placeholders.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'findings': ['   '],
                       'review_summary': 'Need changes.',
                       'changes_requested': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_rejects_findings_without_severity(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review findings omitted severity labels.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'findings': ['Fix retain cycle in meeting footer presenter'],
                       'review_summary': 'One issue must be fixed.',
                       'changes_requested': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_accepts_findings_with_supported_severity(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review findings included supported severity labels.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'findings': ['medium: fix retain cycle in meeting footer presenter'],
                       'review_summary': 'One medium-severity issue must be fixed.',
                       'changes_requested': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_review_accepts_findings_with_important_prefix(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review findings used the important severity label.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'findings': ['important: fix retain cycle in meeting footer presenter'],
                       'review_summary': 'One important issue must be fixed.',
                       'changes_requested': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_review_rejects_findings_out_of_severity_order(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review findings jumped from lower severity back to higher severity.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'findings': ['medium: fix retain cycle in meeting footer presenter',
                                    'important: fix leaked observer in toolbar coordinator'],
                       'review_summary': 'Two findings need follow-up.',
                       'changes_requested': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_verifier_failure_routes_to_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA returned invalid structured output.',
 'structured_output': {'release_qa_target_scope': 'Changed meeting footer flow on iPhone simulator',
                       'release_qa_summary': 'Core checks passed, but one visual confirmation is '
                                             'still blocked.',
                       'release_qa_verdict': 'ship',
                       'release_qa_executed_checks': ['Smoke', 'Regression'],
                       'release_qa_blocked_checks': ['Final screenshot diff confirmation'],
                       'release_qa_risk_next_steps': ['Resolve the blocked screenshot diff before '
                                                      'shipping.'],
                       'release_qa_artifacts': []}},
            verifier_result={'passed': False, 'checks': []},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_review_verifier_failure_routes_to_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review output violated the severity contract.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'review_summary': 'One issue must be fixed.',
                       'findings': ['Fix retain cycle in meeting footer presenter'],
                       'changes_requested': True}},
            verifier_result={'passed': False, 'checks': []},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_completion_verifier_failure_routes_to_execute_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Completion output violated the final gate contract.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Looks done.',
                       'verification_evidence': ['xcodebuild test -scheme ZoomClient'],
                       'remaining_risks': ['Residual issue'],
                       'release_qa_risks_resolved': False}},
            verifier_result={'passed': False, 'checks': []},
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

    def test_review_rejects_approved_status_with_findings(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review tried to approve despite leaving one actionable finding.',
 'structured_output': {'review_status': 'approved',
                       'reviewed_snapshot': 'HEAD vs working tree',
                       'findings': ['low: rename the leaked presenter helper before merge'],
                       'review_summary': 'Mostly ready, but one cleanup item remains.',
                       'changes_requested': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_rejects_pass_with_remaining_risks(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed with remaining risks still listed.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Looks done.',
                       'verification_evidence': ['xcodebuild test'],
                       'remaining_risks': ['Residual issue'],
                       'release_qa_risks_resolved': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_accepts_ship_without_resolved_flag_when_no_blocked_checks(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed after ship verdict with only informational next steps left in '
            'state.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Looks done.',
                       'verification_evidence': ['xcodebuild test'],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': False}},
            state={'release_qa_verdict': 'ship',
 'review_status': 'approved',
 'open_issues': [],
 'release_qa_blocked_checks': [],
 'release_qa_risk_next_steps': ['Proceed to final delivery summary.']},
        )
        self.assertIs(result['passed'], True)

    def test_completion_verification_rejects_blank_evidence_items(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification used blank evidence placeholders.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Looks done.',
                       'verification_evidence': ['   '],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': False}},
            state={'release_qa_verdict': 'ship', 'review_status': 'approved', 'open_issues': []},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_requires_release_qa_ship_state(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed even though release QA did not end in ship.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Completion looks ready.',
                       'verification_evidence': ['xcodebuild test -scheme ZoomClient'],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': False}},
            state={'release_qa_verdict': 'do_not_ship', 'review_status': 'approved', 'open_issues': []},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_requires_review_approved_state(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed even though code review still requested changes.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Completion looks ready.',
                       'verification_evidence': ['xcodebuild test -scheme ZoomClient'],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': False}},
            state={'release_qa_verdict': 'ship', 'review_status': 'changes_requested', 'open_issues': []},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_rejects_pass_with_open_issues_in_state(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed while open issues are still recorded.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Completion looks ready.',
                       'verification_evidence': ['xcodebuild test -scheme ZoomClient'],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': False}},
            state={'release_qa_verdict': 'ship',
 'review_status': 'approved',
 'open_issues': ['Known crash in edge case']},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_requires_release_qa_risk_resolution(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed even though release QA blocked checks were not marked resolved.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Completion looks ready.',
                       'verification_evidence': ['xcodebuild test -scheme ZoomClient'],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': False}},
            state={'release_qa_verdict': 'ship',
 'review_status': 'approved',
 'open_issues': [],
 'release_qa_blocked_checks': ['Need final screenshot diff confirmation'],
 'release_qa_risk_next_steps': ['Re-run screenshot diff and confirm no visual regression.']},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_accepts_resolved_release_qa_risks(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed after release QA blocked checks were explicitly resolved.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Completion looks ready.',
                       'verification_evidence': ['xcodebuild test -scheme ZoomClient',
                                                 'Re-ran screenshot diff and compared against '
                                                 'approved mock.'],
                       'remaining_risks': [],
                       'release_qa_risks_resolved': True,
                       'release_qa_risk_resolution_summary': 'Re-ran the screenshot diff and '
                                                             'cleared the last release QA blocked '
                                                             'check.'}},
            state={'release_qa_verdict': 'ship',
 'review_status': 'approved',
 'open_issues': [],
 'release_qa_blocked_checks': ['Need final screenshot diff confirmation'],
 'release_qa_risk_next_steps': ['Re-run screenshot diff and confirm no visual regression.']},
        )
        self.assertIs(result['passed'], True)

    def test_completion_verification_missing_inputs_blocks_to_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_completion',
            observation={'status': 'blocked',
 'summary': 'Final verification cannot proceed without missing evidence.',
 'structured_output': {'blocked_reason': 'Missing production screenshot comparison',
                       'missing_inputs': ['Production screenshot comparison']}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'repair')

    def test_brainstorming_rejects_whitespace_ui_visual_inputs(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming used whitespace-only visual QA inputs.',
 'structured_output': {'clarification_questions': ['Which screen changes?'],
                       'clarification_answers_summary': 'The requested UI surface was confirmed.',
                       'design_presented': True,
                       'design_summary': 'Approved UI design summary.',
                       'design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
                       'ui_surface_affected': True,
                       'visual_spec_detail_summary': '   ',
                       'design_comparison_source': '   ',
                       'runtime_visual_comparison_scope': '   ',
                       'open_questions': [],
                       'ready_for_subagent_review': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_run_spec_review_rejects_artifact_path_traversal(self):
        result = verifiers.verify_run_spec_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_spec_review',
            observation={'status': 'succeeded',
 'summary': 'Spec review used a path that escapes the artifact directory.',
 'structured_output': {'spec_review_loop_completed': True,
                       'spec_review_perspectives': ['development', 'design', 'testing'],
                       'spec_review_findings_summary': 'Development, design, and testing reviews '
                                                       'passed.',
                       'spec_review_subagent_summaries': ['Development review passed.',
                                                          'Design review passed.',
                                                          'Testing review passed.'],
                       'spec_review_artifact_paths': ['docs/superpowers/specs/../../../skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/flowchart.md',
                                                      'docs/superpowers/specs/2026-06-24-ios-change-design-review.md',
                                                      'docs/superpowers/specs/2026-06-24-ios-change-testing-review.md'],
                       'open_questions': [],
                       'ready_for_planning': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_implementation_verification_failure_requires_planning_route(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation verification failed and needs a plan update.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implementation needs a debugging and planning '
                                                 'pass.',
                       'changed_files': ['Zoom/Foo.swift'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': [],
                       'verification_commands': ['xcodebuild test -scheme ZoomClient'],
                       'verification_passed': False,
                       'open_issues': ['The failing verification exposes a plan assumption.'],
                       'plan_updates_required': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'write_implementation_plan')
        self.assertEqual(result.branch_kind, 'retry')

    def test_request_unblocking_input_returns_to_repair_owner(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'return_stage_id': 'verify_completion', 'repair_context': {'source_stage_id': 'repair_and_resume'}}),
            current_step_id='request_unblocking_input',
            observation={'status': 'succeeded',
 'summary': 'The user supplied the missing approval context.',
 'structured_output': {'blocking_reason': 'Approval was missing.',
                       'user_action_needed': 'Confirm the release QA exception.',
                       'suggested_next_input': 'Release QA exception approved by owner.'}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'continue')

    def test_max_steps_exceeded_terminates_at_degraded_final(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'constraints': {'max_steps': 1}, 'attempt_counts': {}}),
            current_step_id='verify_completion',
            observation={'status': 'succeeded', 'summary': 'Workflow hit its step budget.', 'structured_output': {}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'finalize_delivery_summary')
        self.assertEqual(result.branch_kind, 'complete')

    def test_request_unblocking_input_rejects_missing_required_fields(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'return_stage_id': 'verify_completion', 'repair_context': {'source_stage_id': 'repair_and_resume'}}),
            current_step_id='request_unblocking_input',
            observation={'status': 'succeeded',
 'summary': 'Unblocking output omitted its required fields.',
 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_unblocking_input')
        self.assertEqual(result.branch_kind, 'repair')

    def test_repair_and_resume_rejects_missing_required_fields(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'return_stage_id': 'verify_completion'}),
            current_step_id='repair_and_resume',
            observation={'status': 'succeeded',
 'summary': 'Repair output omitted its required fields.',
 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_main_success_without_verifier_fails_closed_to_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA output had no verifier result.',
 'structured_output': {'release_qa_target_scope': 'Meeting footer',
                       'release_qa_summary': 'Checks completed.',
                       'release_qa_verdict': 'ship',
                       'release_qa_executed_checks': ['Smoke test'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Proceed to review.'],
                       'release_qa_artifacts': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'repair')

    def test_release_qa_accepts_agent_device_off_mode_without_device_output(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA completed without requesting device QA.',
 'structured_output': {'release_qa_verdict': 'ship',
                       'release_qa_summary': 'Static and implementation checks passed.',
                       'release_qa_executed_checks': ['Unit test suite'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Proceed to pre-merge review.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'Changed Swift sources',
                       'agent_device_status': None,
                       'agent_device_commands': None,
                       'agent_device_artifacts': None}},
            state={'context': {'agent_device_mode': 'off'}},
        )
        self.assertIs(result['passed'], True)

    def test_release_qa_rejects_required_agent_device_without_evidence(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA omitted required device evidence.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'Device evidence is missing.',
                       'release_qa_executed_checks': ['Unit test suite'],
                       'release_qa_blocked_checks': ['Required device evidence missing'],
                       'release_qa_risk_next_steps': ['Run the required agent-device smoke flow.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'Changed Swift sources'}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': 'com.zoom.Zoom',
             'agent_device_artifact_path': 'artifacts/build/Zoom.ipa',
             'agent_device_device': 'iPhone 15'}},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_failed_required_agent_device(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Required device runner failed.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'The device runner could not be prepared.',
                       'release_qa_executed_checks': ['Unit test suite'],
                       'release_qa_blocked_checks': ['agent-device runner unavailable'],
                       'release_qa_risk_next_steps': ['Repair the device runner and rerun QA.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'Zoom iOS app',
                       'agent_device_status': 'blocked',
                       'agent_device_commands': [],
                       'agent_device_artifacts': []}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': 'com.zoom.Zoom',
             'agent_device_artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json',
             'agent_device_device': 'iPhone 15',
             'agent_device_evidence_dir': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references'}},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_accepts_successful_required_agent_device(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA completed with device evidence.',
 'structured_output': {'release_qa_verdict': 'ship',
                       'release_qa_summary': 'Implementation and device smoke checks passed.',
                       'release_qa_executed_checks': ['Unit test suite',
                                                      'agent-device snapshot and replay smoke'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Proceed to pre-merge review.'],
                       'release_qa_artifacts': ['artifacts/release-qa/agent-device/session.json'],
                       'release_qa_target_scope': 'com.zoom.Zoom on iPhone 15, build 123',
                       'agent_device_status': 'succeeded',
                       'agent_device_commands': ['agent-device prepare ios-runner --platform ios',
                                                 'agent-device replay smoke.ad'],
                       'agent_device_artifacts': ['skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/flowchart.md',
                                                  'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-review.md'],
                       'agent_device_session': 'qa-session-123',
                       'agent_device_replay_suite': 'smoke.ad',
                       'agent_device_cli_version': '0.4.0',
                       'agent_device_observed_device': 'iPhone 15',
                       'agent_device_observed_app_id': 'com.zoom.Zoom',
                       'agent_device_runner_status': 'succeeded',
                       'agent_device_execution_receipt': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json'}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': 'com.zoom.Zoom',
             'agent_device_artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json',
             'agent_device_device': 'iPhone 15',
             'agent_device_evidence_dir': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references'}},
        )
        self.assertIs(result['passed'], True)

    def test_release_qa_rejects_agent_device_artifact_escape(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Required device QA attempted to report an artifact outside its evidence root.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'The device artifact path is unsafe.',
                       'release_qa_executed_checks': ['agent-device prepare ios-runner',
                                                      'agent-device snapshot'],
                       'release_qa_blocked_checks': ['Unsafe agent-device artifact path'],
                       'release_qa_risk_next_steps': ['Use the configured evidence directory and '
                                                      'rerun device QA.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'com.zoom.Zoom on iPhone 15, build 123',
                       'agent_device_status': 'succeeded',
                       'agent_device_commands': ['agent-device prepare ios-runner --platform ios',
                                                 'agent-device snapshot'],
                       'agent_device_artifacts': ['../outside-evidence/report.json'],
                       'agent_device_cli_version': '0.4.0',
                       'agent_device_observed_device': 'iPhone 15',
                       'agent_device_observed_app_id': 'com.zoom.Zoom',
                       'agent_device_runner_status': 'succeeded'}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': 'com.zoom.Zoom',
             'agent_device_artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json',
             'agent_device_device': 'iPhone 15',
             'agent_device_evidence_dir': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references'}},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_accepts_empty_agent_device_mode_without_device_output(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA completed without requesting device QA.',
 'structured_output': {'release_qa_verdict': 'ship',
                       'release_qa_summary': 'Static checks passed.',
                       'release_qa_executed_checks': ['Unit test suite'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Proceed to review.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'Changed Swift sources',
                       'agent_device_status': None,
                       'agent_device_commands': None,
                       'agent_device_artifacts': None}},
            state={'context': {}},
        )
        self.assertIs(result['passed'], True)

    def test_release_qa_rejects_unknown_agent_device_mode(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA supplied an unsupported device mode.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'The device mode is invalid.',
                       'release_qa_executed_checks': ['Unit test suite'],
                       'release_qa_blocked_checks': ['Unsupported agent-device mode'],
                       'release_qa_risk_next_steps': ['Choose off or required and rerun QA.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'Changed Swift sources'}},
            state={'context': {'agent_device_mode': 'maybe'}},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_required_agent_device_without_output_evidence(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA omitted required device execution evidence.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'The required device evidence is missing.',
                       'release_qa_executed_checks': ['Unit test suite'],
                       'release_qa_blocked_checks': ['Required device evidence missing'],
                       'release_qa_risk_next_steps': ['Run the required agent-device smoke flow.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'com.zoom.Zoom on iPhone 15'}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': 'com.zoom.Zoom',
             'agent_device_artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json',
             'agent_device_device': 'iPhone 15',
             'agent_device_evidence_dir': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references'}},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_device_operations_before_runner_prepare(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA recorded device operations before runner preparation.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'Runner preparation order is invalid.',
                       'release_qa_executed_checks': ['agent-device snapshot'],
                       'release_qa_blocked_checks': ['Runner was prepared after a device '
                                                     'operation'],
                       'release_qa_risk_next_steps': ['Prepare the runner and rerun the device '
                                                      'flow.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'com.zoom.Zoom on iPhone 15',
                       'agent_device_status': 'succeeded',
                       'agent_device_commands': ['agent-device snapshot -i',
                                                 'agent-device prepare ios-runner --platform ios'],
                       'agent_device_artifacts': ['artifacts/release-qa/agent-device/screenshot.png'],
                       'agent_device_cli_version': '0.4.0',
                       'agent_device_observed_device': 'iPhone 15',
                       'agent_device_observed_app_id': 'com.zoom.Zoom',
                       'agent_device_runner_status': 'succeeded'}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': 'com.zoom.Zoom',
             'agent_device_artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json',
             'agent_device_device': 'iPhone 15',
             'agent_device_evidence_dir': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references'}},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_absolute_agent_device_artifact_path(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA attempted to record an absolute device artifact path.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'The device artifact path is unsafe.',
                       'release_qa_executed_checks': ['agent-device snapshot'],
                       'release_qa_blocked_checks': ['Unsafe agent-device artifact path'],
                       'release_qa_risk_next_steps': ['Use the configured evidence directory and '
                                                      'rerun QA.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'com.zoom.Zoom on iPhone 15',
                       'agent_device_status': 'succeeded',
                       'agent_device_commands': ['agent-device prepare ios-runner --platform ios',
                                                 'agent-device snapshot'],
                       'agent_device_artifacts': ['/tmp/outside-evidence/report.json'],
                       'agent_device_cli_version': '0.4.0',
                       'agent_device_observed_device': 'iPhone 15',
                       'agent_device_observed_app_id': 'com.zoom.Zoom',
                       'agent_device_runner_status': 'succeeded'}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': 'com.zoom.Zoom',
             'agent_device_artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json',
             'agent_device_device': 'iPhone 15',
             'agent_device_evidence_dir': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references'}},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_non_string_agent_device_context(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA received malformed device configuration.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'The device configuration is malformed.',
                       'release_qa_executed_checks': ['Unit test suite'],
                       'release_qa_blocked_checks': ['Malformed device configuration'],
                       'release_qa_risk_next_steps': ['Fix the device configuration and rerun QA.'],
                       'release_qa_artifacts': [],
                       'release_qa_target_scope': 'Changed Swift sources'}},
            state={'context': {'agent_device_mode': 'required',
             'agent_device_expected_version': '0.4.0',
             'agent_device_app_id': {},
             'agent_device_artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json',
             'agent_device_device': 'iPhone 15',
             'agent_device_evidence_dir': 'skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references'}},
        )
        self.assertIs(result['passed'], False)

    def test_generated_template_context_prefers_state_for_agent_device_replay_suite(self):
        state = self._make_state(None)
        state.context['agent_device_replay_suite'] = 'stale-input-value'
        state.agent_device_replay_suite = 'state-preferred-value'
        context = graphbuilder_runtime._template_context_from_state(state)
        self.assertEqual(context['agent_device_replay_suite'], 'state-preferred-value')

    def test_generated_template_context_prefers_state_for_agent_device_session(self):
        state = self._make_state(None)
        state.context['agent_device_session'] = 'stale-input-value'
        state.agent_device_session = 'state-preferred-value'
        context = graphbuilder_runtime._template_context_from_state(state)
        self.assertEqual(context['agent_device_session'], 'state-preferred-value')


if __name__ == "__main__":
    unittest.main()
