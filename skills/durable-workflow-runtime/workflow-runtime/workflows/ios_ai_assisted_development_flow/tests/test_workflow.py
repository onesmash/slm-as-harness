import sys
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = RUNTIME_ROOT.parent
REPO_ROOT = SKILL_ROOT.parents[2]
VENV_SITE_PACKAGES = next((REPO_ROOT / '.venv' / 'lib').glob('python*/site-packages'), None)
if VENV_SITE_PACKAGES is not None and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_SITE_PACKAGES))
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
                       'ready_for_openspec': True}},
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
                       'ready_for_openspec': True}},
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
                       'spec_review_loop_completed': True,
                       'spec_review_perspectives': ['development', 'design', 'testing'],
                       'spec_review_findings_summary': 'Development, design, and testing reviews '
                                                       'passed.',
                       'spec_review_subagent_summaries': ['Development review passed.',
                                                          'Design review passed.',
                                                          'Testing review passed.'],
                       'open_questions': [],
                       'ready_for_openspec': True}},
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
                       'spec_review_loop_completed': True,
                       'spec_review_perspectives': ['development', 'design', 'testing'],
                       'spec_review_findings_summary': 'Development, design, and testing reviews '
                                                       'passed.',
                       'spec_review_subagent_summaries': ['Development review passed.',
                                                          'Design review passed.',
                                                          'Testing review passed.'],
                       'open_questions': [],
                       'ready_for_openspec': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_brainstorming_rejects_missing_spec_review_perspective(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming completed review without the design perspective.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
                       'approved_design_path': 'docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md',
                       'ui_surface_affected': False,
                       'spec_review_loop_completed': True,
                       'spec_review_perspectives': ['development', 'testing', 'testing'],
                       'spec_review_findings_summary': 'Development and testing reviews passed.',
                       'spec_review_subagent_summaries': ['Development review passed.',
                                                          'Testing review passed.',
                                                          'Second testing review passed.'],
                       'open_questions': [],
                       'ready_for_openspec': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_brainstorming_rejects_openspec_design_path(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming tried to reuse an OpenSpec design document.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
                       'approved_design_path': 'openspec/changes/example-change/design.md',
                       'open_questions': [],
                       'ready_for_openspec': True}},
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
                       'ready_for_openspec': True}},
            verifier_result={'passed': False,
 'checks': [{'name': 'clarification_questions',
             'passed': False,
             'message': 'Brainstorming must ask and record at least one clarification question '
                        'before continuing.'}]},
        )
        self.assertEqual(result.step_id, 'run_brainstorming')
        self.assertEqual(result.branch_kind, 'retry')

    def test_refinement_not_ready_retries_refinement(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='refine_change_with_openspec',
            observation={'status': 'succeeded',
 'summary': 'Refinement found an unresolved architecture decision.',
 'structured_output': {'refinement_summary': 'Need to confirm API ownership.',
                       'changed_artifacts': [],
                       'unresolved_questions': ['Who owns the bridge contract?'],
                       'ready_for_apply': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'refine_change_with_openspec')
        self.assertEqual(result.branch_kind, 'retry')

    def test_implementation_rejects_failed_verification(self):
        result = verifiers.verify_execute_implementation(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation finished but tests failed.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented tasks.',
                       'changed_files': ['Zoom/Classes/Example.mm'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': [],
                       'verification_commands': ['unit-test => failed'],
                       'verification_passed': False,
                       'open_issues': ['unit-test failed']}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_implementation_requires_verification_commands(self):
        result = verifiers.verify_execute_implementation(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation claims verification passed without commands.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented tasks.',
                       'changed_files': ['Zoom/Classes/Example.mm'],
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
 'summary': 'Implementation finished with verification evidence.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented tasks.',
                       'changed_files': ['Zoom/Classes/Example.mm'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': [],
                       'verification_commands': ['unit-test => passed'],
                       'verification_passed': True,
                       'open_issues': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'run_agentic_release_qa')
        self.assertEqual(result.branch_kind, 'continue')

    def test_release_qa_rejects_unknown_verdict(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA returned an unknown verdict.',
 'structured_output': {'release_qa_verdict': 'maybe_ship',
                       'release_qa_summary': 'QA found ambiguous risk.',
                       'release_qa_executed_checks': ['Reviewed changed files.'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Normalize verdict before continuing.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_blocked_routes_to_unblocking(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA could not run because device access is missing.',
 'structured_output': {'release_qa_verdict': 'blocked',
                       'release_qa_summary': 'Device QA could not run.',
                       'release_qa_executed_checks': ['Inspected changed files and local '
                                                      'verification evidence.'],
                       'release_qa_blocked_checks': ['Run on an iOS device with the release build '
                                                     'installed.'],
                       'release_qa_risk_next_steps': ['Provide device access or release build '
                                                      'artifact.'],
                       'release_qa_artifacts': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_unblocking_input')
        self.assertEqual(result.branch_kind, 'repair')

    def test_release_qa_do_not_ship_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA found a blocking regression.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'A stateful regression was found in the changed flow.',
                       'release_qa_executed_checks': ['Ran targeted regression scenario for the '
                                                      'changed flow.'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Fix the regression and rerun implementation '
                                                      'verification.'],
                       'release_qa_artifacts': ['logs/release-qa-regression.txt']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

    def test_release_qa_ship_routes_to_final_review(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA passed with no blocking risks.',
 'structured_output': {'release_qa_verdict': 'ship',
                       'release_qa_summary': 'Targeted release QA found no blocking risk.',
                       'release_qa_executed_checks': ['Ran targeted regression scenario for the '
                                                      'changed flow.'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['No additional release QA action required.'],
                       'release_qa_artifacts': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_final_code_review')
        self.assertEqual(result.branch_kind, 'continue')

    def test_review_changes_requested_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_final_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review found a regression.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'merge_commit_sha:abc123',
                       'findings': ['major | Zoom/Classes/Example.mm | Missing lifecycle guard. | '
                                    'Add lifecycle guard before shipping.'],
                       'review_summary': 'Changes requested.',
                       'changes_requested': True,
                       'missing_review_inputs': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

    def test_review_blocked_routes_to_unblocking(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_final_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review could not run because MR URL is missing.',
 'structured_output': {'review_status': 'blocked',
                       'reviewed_snapshot': 'missing',
                       'findings': [],
                       'review_summary': 'Missing MR URL.',
                       'changes_requested': False,
                       'missing_review_inputs': ['mr_url']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_unblocking_input')
        self.assertEqual(result.branch_kind, 'repair')

    def test_review_changes_requested_requires_findings(self):
        result = verifiers.verify_request_final_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_final_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review requested changes without findings.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'merge_commit_sha:abc123',
                       'findings': [],
                       'review_summary': 'Changes requested.',
                       'changes_requested': True,
                       'missing_review_inputs': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_approved_requires_changes_flag_false(self):
        result = verifiers.verify_request_final_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_final_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review approved with inconsistent flag.',
 'structured_output': {'review_status': 'approved',
                       'reviewed_snapshot': 'merge_commit_sha:abc123',
                       'findings': [],
                       'review_summary': 'Approved.',
                       'changes_requested': True,
                       'missing_review_inputs': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_code_kb_skip_requires_reason(self):
        result = verifiers.verify_write_code_kb_feedback(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_code_kb_feedback',
            observation={'status': 'succeeded',
 'summary': 'KB update skipped without reason.',
 'structured_output': {'kb_updated': False,
                       'updated_pages': [],
                       'backlog_updates': [],
                       'kb_checks': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_code_kb_update_requires_pages(self):
        result = verifiers.verify_write_code_kb_feedback(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_code_kb_feedback',
            observation={'status': 'succeeded',
 'summary': 'KB update reported without page list.',
 'structured_output': {'kb_updated': True,
                       'updated_pages': [],
                       'backlog_updates': [],
                       'kb_checks': ['check_page_format.py => passed']}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_code_kb_update_requires_checks(self):
        result = verifiers.verify_write_code_kb_feedback(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_code_kb_feedback',
            observation={'status': 'succeeded',
 'summary': 'KB update reported without checks.',
 'structured_output': {'kb_updated': True,
                       'updated_pages': ['knowledge-base/workflows/ai-assisted-development-flow.md'],
                       'backlog_updates': [],
                       'kb_checks': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_propose_rejects_missing_tasks_path(self):
        result = verifiers.verify_propose_openspec_change(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='propose_openspec_change',
            observation={'status': 'succeeded',
 'summary': 'OpenSpec proposal omitted tasks path.',
 'structured_output': {'change_name': 'ios-ai-assisted-development-flow',
                       'change_path': 'openspec/changes/example-change',
                       'proposal_path': 'openspec/changes/example-change/proposal.md',
                       'tasks_path': '',
                       'spec_paths': [],
                       'created_artifacts': ['proposal.md'],
                       'apply_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_code_kb_update_accepts_pages_and_checks(self):
        result = verifiers.verify_write_code_kb_feedback(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_code_kb_feedback',
            observation={'status': 'succeeded',
 'summary': 'KB update reported pages and checks.',
 'structured_output': {'kb_updated': True,
                       'updated_pages': ['knowledge-base/workflows/ai-assisted-development-flow.md'],
                       'backlog_updates': ['Updated backlog row for AI-assisted development flow.'],
                       'kb_checks': ['check_page_format.py => passed']}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_code_kb_skip_accepts_reason(self):
        result = verifiers.verify_write_code_kb_feedback(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='write_code_kb_feedback',
            observation={'status': 'succeeded',
 'summary': 'KB update skipped with reason.',
 'structured_output': {'kb_updated': False,
                       'updated_pages': [],
                       'backlog_updates': [],
                       'kb_checks': [],
                       'skipped_reason': 'Change has no durable knowledge-base update.'}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_review_approved_routes_to_kb_feedback(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_final_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review approved final state.',
 'structured_output': {'review_status': 'approved',
                       'reviewed_snapshot': 'merge_commit_sha:abc123',
                       'findings': [],
                       'review_summary': 'No findings.',
                       'changes_requested': False,
                       'missing_review_inputs': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'write_code_kb_feedback')
        self.assertEqual(result.branch_kind, 'continue')

    def test_kb_feedback_success_completes_workflow(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='write_code_kb_feedback',
            observation={'status': 'succeeded',
 'summary': 'KB feedback finished.',
 'structured_output': {'kb_updated': False,
                       'updated_pages': [],
                       'backlog_updates': [],
                       'kb_checks': [],
                       'skipped_reason': 'No durable KB update needed.'}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'finalize_delivery_summary')
        self.assertEqual(result.branch_kind, 'complete')

    def test_brainstorming_rejects_non_spec_doc_path(self):
        result = verifiers.verify_run_brainstorming(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_brainstorming',
            observation={'status': 'succeeded',
 'summary': 'Brainstorming pointed at a non-spec document path.',
 'structured_output': {'clarification_questions': ['What user-visible behavior should change?'],
                       'clarification_answers_summary': 'The user confirmed behavior, scope, and '
                                                        'success criteria.',
                       'design_presented': True,
                       'user_approved_design': True,
                       'design_approved': True,
                       'approved_design_summary': 'Approved design summary.',
                       'approved_design_path': 'README.md',
                       'open_questions': [],
                       'ready_for_openspec': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_accepts_ship_output(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA passed.',
 'structured_output': {'release_qa_verdict': 'ship',
                       'release_qa_summary': 'Targeted release QA found no blocking risk.',
                       'release_qa_executed_checks': ['Ran targeted regression scenario for the '
                                                      'changed flow.'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['No additional release QA action required.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_release_qa_accepts_ship_with_risks_output(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA passed with risks.',
 'structured_output': {'release_qa_verdict': 'ship_with_risks',
                       'release_qa_summary': 'Targeted release QA found non-blocking residual '
                                             'risk.',
                       'release_qa_executed_checks': ['Inspected changed files and ran targeted '
                                                      'regression scenario.'],
                       'release_qa_blocked_checks': ['Full device matrix was not available.'],
                       'release_qa_risk_next_steps': ['Review residual device-matrix risk during '
                                                      'final MR review.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_release_qa_rejects_ship_without_executed_checks(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA claimed ship without executed checks.',
 'structured_output': {'release_qa_verdict': 'ship',
                       'release_qa_summary': 'Targeted release QA found no blocking risk.',
                       'release_qa_executed_checks': [],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['No additional release QA action required.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_ship_with_risks_routes_to_final_review(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA found non-blocking risks.',
 'structured_output': {'release_qa_verdict': 'ship_with_risks',
                       'release_qa_summary': 'Targeted release QA found non-blocking residual '
                                             'risk.',
                       'release_qa_executed_checks': ['Inspected changed files and ran targeted '
                                                      'regression scenario.'],
                       'release_qa_blocked_checks': ['Full device matrix was not available.'],
                       'release_qa_risk_next_steps': ['Review residual device-matrix risk during '
                                                      'final MR review.'],
                       'release_qa_artifacts': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_final_code_review')
        self.assertEqual(result.branch_kind, 'continue')

    def test_max_steps_routes_to_unblocking(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'constraints': {'max_steps': 1}, 'attempt_counts': {}}),
            current_step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation finished but workflow reached max steps.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented tasks.',
                       'changed_files': ['Zoom/Classes/Example.mm'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': [],
                       'verification_commands': ['unit-test => passed'],
                       'verification_passed': True,
                       'open_issues': []}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'request_unblocking_input')
        self.assertEqual(result.branch_kind, 'repair')

    def test_approve_refine_approved_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='approve_refine',
            observation={'status': 'succeeded',
 'summary': 'User approved the refinement.',
 'structured_output': {'user_approved': True,
                       'user_feedback': 'Looks good, proceed.',
                       'additional_refinement_needed': False}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'continue')

    def test_approve_refine_rejected_retries_refinement(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='approve_refine',
            observation={'status': 'succeeded',
 'summary': 'User requested additional refinement.',
 'structured_output': {'user_approved': False,
                       'user_feedback': 'Need to reconsider the approach.',
                       'additional_refinement_needed': True}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'refine_change_with_openspec')
        self.assertEqual(result.branch_kind, 'retry')

    def test_generated_request_unblocking_input_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'run_brainstorming'
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

    def test_generated_repair_and_resume_blocked_preserves_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'write_code_kb_feedback'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(state.return_stage_id, 'write_code_kb_feedback')


if __name__ == "__main__":
    unittest.main()
