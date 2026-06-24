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

    def test_brainstorming_requires_approved_design_path(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Design approved without a written design path.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The change should update one iOS Client '
                                                        'behavior with no scope expansion.',
                       'design_presented': True,
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
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
 'summary': 'Design approved without asking clarification questions.',
 'structured_output': {'clarification_questions': [],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
                       'approved_design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
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
 'summary': 'Brainstorming completed with clarification and approval.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
                       'approved_design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
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
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved UI design summary.',
                       'approved_design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
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
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
                       'approved_design_path': 'docs/superpowers/plans/2026-06-24-sample-plan.md',
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
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
                       'approved_design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
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
                       'plan_reviewed': True,
                       'execution_mode': 'subagent-driven',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_plan_rejects_missing_review(self):
        result = verifiers.verify_write_implementation_plan(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning skipped the user review gate.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'plan_reviewed': False,
                       'execution_mode': 'subagent-driven',
                       'open_questions': [],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_plan_rejects_inline_execution_mode(self):
        result = verifiers.verify_write_implementation_plan(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_implementation_plan',
            observation={'status': 'succeeded',
 'summary': 'Planning picked inline execution while claiming readiness.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'plan_reviewed': True,
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
 'summary': 'Planning completed with a reviewed plan and subagent-driven execution.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'plan_reviewed': True,
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
                       'plan_reviewed': True,
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
 'summary': 'Planning still needs user review.',
 'structured_output': {'plan_summary': 'Need another review pass.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'plan_reviewed': False,
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
 'summary': 'Planning completed with a reviewed plan and ready execution mode.',
 'structured_output': {'plan_summary': 'Plan summary.',
                       'plan_path': 'docs/superpowers/plans/2026-06-24-ios-change.md',
                       'plan_reviewed': True,
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
                       'changes_requested': True,
                       'missing_review_inputs': []}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

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
                       'missing_verification_inputs': [],
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
                       'missing_verification_inputs': [],
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
                       'missing_verification_inputs': [],
                       'release_qa_risks_resolved': True,
                       'release_qa_risk_resolution_summary': 'Residual release QA risks were '
                                                             'rechecked and cleared.'}},
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
                       'changes_requested': True,
                       'missing_review_inputs': []}},
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
                       'changes_requested': True,
                       'missing_review_inputs': []}},
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
                       'changes_requested': True,
                       'missing_review_inputs': []}},
            state={},
        )
        self.assertIs(result['passed'], True)

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
                       'changes_requested': False,
                       'missing_review_inputs': []}},
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
                       'missing_verification_inputs': [],
                       'release_qa_risks_resolved': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_rejects_pass_with_missing_inputs(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Verification passed with missing inputs still listed.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Looks done.',
                       'verification_evidence': ['xcodebuild test'],
                       'remaining_risks': [],
                       'missing_verification_inputs': ['Need one more artifact'],
                       'release_qa_risks_resolved': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

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
                       'missing_verification_inputs': [],
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
                       'missing_verification_inputs': [],
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
                       'missing_verification_inputs': [],
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
                       'missing_verification_inputs': [],
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
                       'missing_verification_inputs': [],
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
                       'missing_verification_inputs': [],
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

    def test_generated_request_unblocking_input_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'run_brainstorming'
        state.repair_context = {'source_stage_id': 'request_unblocking_input'}
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'run_brainstorming')
        self.assertEqual(result.branch_kind, "continue")

    def test_generated_request_unblocking_input_without_return_stage_stays_put(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")

    def test_generated_request_unblocking_input_returns_to_repair_owner(self):
        state = self._make_state(None)
        state.return_stage_id = 'run_brainstorming'
        state.repair_context = {'source_stage_id': 'repair_and_resume'}
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "continue")

    def test_generated_repair_and_resume_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'run_brainstorming'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'run_brainstorming')
        self.assertEqual(result.branch_kind, "continue")

    def test_generated_repair_and_resume_without_return_stage_stays_put(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id="repair_and_resume",
            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "retry")

    def test_generated_repair_and_resume_blocked_before_threshold_retries_locally(self):
        state = self._make_state(None)
        state.return_stage_id = 'verify_completion'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "retry")
        self.assertEqual(state.return_stage_id, 'verify_completion')

    def test_generated_repair_and_resume_blocked_after_threshold_requests_unblocking(self):
        state = self._make_state({'attempt_counts': {'repair_and_resume': 2}})
        state.return_stage_id = 'verify_completion'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(state.return_stage_id, 'verify_completion')

    def test_generated_blocked_repair_context_preserves_host_visible_summary(self):
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        response = engine.start('ios_ai_assisted_development_flow', {
            "task_input": {"goal": "generated workflow regression"},
            "context": {"repo_root": str(REPO_ROOT)},
            "constraints": {"max_steps": 5},
        })
        run_id = response['run_id']
        response = engine.resume(run_id, {
            'run_id': run_id,
            'step_id': 'run_brainstorming',
            'status': 'blocked',
            'summary': 'Need external approval before continuing.',
            'structured_output': {'blocked_reason': 'awaiting approval', 'missing_inputs': ['approval']},
            'artifacts': [],
            'error': None,
            'tool_trace': [],
            'raw_output': '',
        })
        self.assertEqual(response['kind'], 'yield')
        self.assertEqual(response['retry_context']['category'], 'blocked')
        self.assertEqual(response['retry_context']['summary'], 'awaiting approval')
        self.assertEqual(response['retry_context']['requirements'], ['approval'])

    def test_generated_max_steps_preserves_return_stage_for_repair(self):
        state = self._make_state({'constraints': {'max_steps': 1}, 'attempt_counts': {}})
        expected_return_stage = 'verify_completion'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id=expected_return_stage,
            observation={'status': 'succeeded', 'summary': 'Workflow hit max steps.', 'structured_output': {}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(state.return_stage_id, expected_return_stage)


if __name__ == "__main__":
    unittest.main()
