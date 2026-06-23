import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


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

    def test_refinement_rejects_missing_conversation_evidence(self):
        result = verifiers.verify_refine_change_with_openspec(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='refine_change_with_openspec',
            observation={'status': 'succeeded',
 'summary': 'Refinement skipped the talk-first discussion and jumped to output.',
 'structured_output': {'refinement_summary': 'Need to confirm API ownership.',
                       'user_discussion_summary': '',
                       'discussion_turn_count': 0,
                       'changed_artifacts': [],
                       'unresolved_questions': ['Who owns the bridge contract?'],
                       'ready_for_apply': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_refinement_accepts_recorded_conversation_evidence(self):
        result = verifiers.verify_refine_change_with_openspec(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='refine_change_with_openspec',
            observation={'status': 'succeeded',
 'summary': 'Refinement discussed risks with the user before finishing.',
 'structured_output': {'refinement_summary': 'Confirmed API ownership and narrowed the apply '
                                             'scope.',
                       'user_discussion_summary': 'Discussed API ownership, rollout boundaries, '
                                                  'and whether the bridge contract needed a '
                                                  'compatibility note.',
                       'discussion_turn_count': 2,
                       'changed_artifacts': ['openspec/changes/example-change/design.md'],
                       'unresolved_questions': [],
                       'ready_for_apply': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

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

    def test_implementation_design_issue_routes_back_to_refinement(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation found a spec gap that requires refinement.',
 'structured_output': {'tasks_completed': False,
                       'implementation_summary': 'Started implementation, but discovered the '
                                                 'OpenSpec task does not define the fallback UI '
                                                 'state clearly enough.',
                       'changed_files': ['Zoom/Classes/Example.mm'],
                       'completed_tasks': [],
                       'remaining_tasks': ['Clarify fallback UI state in the OpenSpec design '
                                           'before finishing implementation.'],
                       'verification_commands': ['unit-test => not-run'],
                       'verification_passed': False,
                       'open_issues': ['OpenSpec design does not define the fallback UI state.'],
                       'openspec_updates_required': True,
                       'openspec_update_summary': 'The approved design and OpenSpec tasks need a '
                                                  'fallback UI state clarification before '
                                                  'implementation can continue safely.'}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'refine_change_with_openspec')
        self.assertEqual(result.branch_kind, 'retry')

    def test_implementation_rejects_completed_with_remaining_tasks(self):
        result = verifiers.verify_execute_implementation(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='execute_implementation',
            observation={'status': 'succeeded',
 'summary': 'Implementation claimed completion while still listing remaining tasks.',
 'structured_output': {'tasks_completed': True,
                       'implementation_summary': 'Implemented most tasks.',
                       'changed_files': ['Zoom/Classes/Example.mm'],
                       'completed_tasks': ['Task 1'],
                       'remaining_tasks': ['Task 2'],
                       'verification_commands': ['unit-test => passed'],
                       'verification_passed': True,
                       'open_issues': []}},
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
        self.assertEqual(result.step_id, 'request_pre_merge_code_review')
        self.assertEqual(result.branch_kind, 'continue')

    def test_review_changes_requested_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review found a regression.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'base_sha:abc123..head_sha:def456',
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
            current_step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review could not run because the git review base is missing.',
 'structured_output': {'review_status': 'blocked',
                       'reviewed_snapshot': 'missing',
                       'findings': [],
                       'review_summary': 'Missing review base.',
                       'changes_requested': False,
                       'missing_review_inputs': ['base_sha']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_unblocking_input')
        self.assertEqual(result.branch_kind, 'repair')

    def test_review_changes_requested_requires_findings(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review requested changes without findings.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'base_sha:abc123..head_sha:def456',
                       'findings': [],
                       'review_summary': 'Changes requested.',
                       'changes_requested': True,
                       'missing_review_inputs': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_approved_requires_changes_flag_false(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review approved with inconsistent flag.',
 'structured_output': {'review_status': 'approved',
                       'reviewed_snapshot': 'base_sha:abc123..head_sha:def456',
                       'findings': [],
                       'review_summary': 'Approved.',
                       'changes_requested': True,
                       'missing_review_inputs': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_approved_rejects_missing_review_inputs(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review approved while still reporting missing inputs.',
 'structured_output': {'review_status': 'approved',
                       'reviewed_snapshot': 'base_sha:abc123..head_sha:def456',
                       'findings': [],
                       'review_summary': 'Approved.',
                       'changes_requested': False,
                       'missing_review_inputs': ['base_sha']}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_blocked_requires_missing_review_inputs(self):
        result = verifiers.verify_request_pre_merge_code_review(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review blocked without identifying any missing input.',
 'structured_output': {'review_status': 'blocked',
                       'reviewed_snapshot': 'missing',
                       'findings': [],
                       'review_summary': 'Review could not run.',
                       'changes_requested': False,
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
 'summary': 'Review returned findings but did not label their severity.',
 'structured_output': {'review_status': 'changes_requested',
                       'reviewed_snapshot': 'base_sha:abc123..head_sha:def456',
                       'findings': ['Zoom/Classes/Example.mm | Missing lifecycle guard. | Add '
                                    'lifecycle guard before shipping.'],
                       'review_summary': 'Changes requested.',
                       'changes_requested': True,
                       'missing_review_inputs': []}},
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

    def test_propose_rejects_missing_design_or_spec_artifact(self):
        result = verifiers.verify_propose_openspec_change(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='propose_openspec_change',
            observation={'status': 'succeeded',
 'summary': 'OpenSpec proposal omitted any durable design or spec artifact.',
 'structured_output': {'change_name': 'ios-ai-assisted-development-flow',
                       'change_path': 'openspec/changes/example-change',
                       'proposal_path': 'openspec/changes/example-change/proposal.md',
                       'tasks_path': 'openspec/changes/example-change/tasks.md',
                       'spec_paths': [],
                       'created_artifacts': ['proposal.md', 'tasks.md'],
                       'apply_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_review_approved_completes_workflow(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='request_pre_merge_code_review',
            observation={'status': 'succeeded',
 'summary': 'Review approved final state.',
 'structured_output': {'review_status': 'approved',
                       'reviewed_snapshot': 'base_sha:abc123..head_sha:def456',
                       'findings': [],
                       'review_summary': 'No findings.',
                       'changes_requested': False,
                       'missing_review_inputs': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'verify_completion')
        self.assertEqual(result.branch_kind, 'continue')

    def test_completion_verification_failed_routes_to_implementation(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification found incomplete evidence.',
 'structured_output': {'verification_passed': False,
                       'verification_summary': 'Final verification failed because release notes '
                                               'and one verification rerun are missing.',
                       'verification_evidence': ['unit-test rerun missing',
                                                 'release QA evidence reviewed'],
                       'remaining_risks': ['Need one fresh test rerun before claiming completion.'],
                       'missing_verification_inputs': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'execute_implementation')
        self.assertEqual(result.branch_kind, 'retry')

    def test_completion_verification_requires_evidence(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification passed without recording evidence.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Verified.',
                       'verification_evidence': [],
                       'remaining_risks': [],
                       'missing_verification_inputs': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_success_completes_workflow(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification gathered enough evidence to claim completion.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Fresh tests, release QA review, and pre-merge '
                                               'review evidence all support completion.',
                       'verification_evidence': ['Re-ran final verification command suite '
                                                 'successfully.',
                                                 'Reviewed release QA verdict and blocked checks.',
                                                 'Confirmed pre-merge review status approved.'],
                       'remaining_risks': [],
                       'missing_verification_inputs': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'finalize_delivery_summary')
        self.assertEqual(result.branch_kind, 'complete')

    def test_completion_verification_rejects_unresolved_ship_with_risks(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification tried to pass without resolving prior release QA residual risks.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Fresh verification passed, but the prior residual '
                                               'QA risk was not revisited explicitly.',
                       'verification_evidence': ['Re-ran final verification command suite '
                                                 'successfully.'],
                       'remaining_risks': [],
                       'missing_verification_inputs': [],
                       'release_qa_risks_resolved': False}},
            state={'release_qa_verdict': 'ship_with_risks',
 'release_qa_blocked_checks': ['Full device matrix was not available.']},
        )
        self.assertIs(result['passed'], False)

    def test_completion_verification_accepts_resolved_ship_with_risks(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification resolved the prior release QA residual risk with fresh evidence.',
 'structured_output': {'verification_passed': True,
                       'verification_summary': 'Fresh verification reran the previously blocked '
                                               'visual and device checks and resolved the residual '
                                               'release QA risk.',
                       'verification_evidence': ['Re-ran final verification command suite '
                                                 'successfully.',
                                                 'Executed the previously blocked device-matrix '
                                                 'spot check and visual comparison.'],
                       'remaining_risks': [],
                       'missing_verification_inputs': [],
                       'release_qa_risks_resolved': True,
                       'release_qa_risk_resolution_summary': 'Resolved the prior ship_with_risks '
                                                             'release QA hold by rerunning the '
                                                             'blocked visual and device checks '
                                                             'with fresh evidence.'}},
            state={'release_qa_verdict': 'ship_with_risks',
 'release_qa_blocked_checks': ['Full device matrix was not available.']},
        )
        self.assertIs(result['passed'], True)

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
                                                      'pre-merge code review.'],
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

    def test_release_qa_rejects_blocked_without_blocked_checks(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA reported blocked without listing blocked checks.',
 'structured_output': {'release_qa_verdict': 'blocked',
                       'release_qa_summary': 'QA environment is unavailable.',
                       'release_qa_executed_checks': ['Reviewed changed files.'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': ['Provide the missing QA environment.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_do_not_ship_without_next_steps(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA reported do_not_ship without remediation next steps.',
 'structured_output': {'release_qa_verdict': 'do_not_ship',
                       'release_qa_summary': 'A blocking regression was found.',
                       'release_qa_executed_checks': ['Ran a targeted regression scenario.'],
                       'release_qa_blocked_checks': [],
                       'release_qa_risk_next_steps': [],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_ship_with_risks_without_executed_checks(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA reported ship_with_risks without executed checks.',
 'structured_output': {'release_qa_verdict': 'ship_with_risks',
                       'release_qa_summary': 'Residual non-blocking risk remains.',
                       'release_qa_executed_checks': [],
                       'release_qa_blocked_checks': ['Full device matrix was not available.'],
                       'release_qa_risk_next_steps': ['Review residual risk during pre-merge '
                                                      'review.'],
                       'release_qa_artifacts': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_rejects_ui_change_without_visual_evidence(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA skipped explicit visual comparison evidence for a UI change.',
 'structured_output': {'release_qa_verdict': 'ship_with_risks',
                       'release_qa_summary': 'Release QA ran targeted checks but omitted the '
                                             'visual comparison evidence.',
                       'release_qa_executed_checks': ['Ran targeted regression scenario for the '
                                                      'changed flow.'],
                       'release_qa_blocked_checks': ['Full device matrix was not available.'],
                       'release_qa_risk_next_steps': ['Resolve the missing visual comparison '
                                                      'evidence before delivery.'],
                       'release_qa_artifacts': []}},
            state={'ui_surface_affected': True,
 'design_comparison_source': 'Figma frame: MeetingToolbar/Updated',
 'runtime_visual_comparison_scope': 'Meeting toolbar visible in the active-call screen'},
        )
        self.assertIs(result['passed'], False)

    def test_release_qa_accepts_ui_change_with_visual_evidence(self):
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='run_agentic_release_qa',
            observation={'status': 'succeeded',
 'summary': 'Release QA included the visual comparison evidence for a UI change.',
 'structured_output': {'release_qa_verdict': 'ship_with_risks',
                       'release_qa_summary': 'Release QA found one non-blocking residual risk '
                                             'after visual comparison.',
                       'release_qa_executed_checks': ['Ran targeted regression scenario for the '
                                                      'changed flow.',
                                                      'Compared the approved Figma frame against '
                                                      'the runtime toolbar screenshot with pixel '
                                                      'diff.'],
                       'release_qa_blocked_checks': ['Full device matrix was not available.'],
                       'release_qa_risk_next_steps': ['Review the residual device-matrix risk '
                                                      'during pre-merge review.'],
                       'release_qa_artifacts': ['artifacts/pixel-diff/meeting-toolbar-diff.png']}},
            state={'ui_surface_affected': True,
 'design_comparison_source': 'Figma frame: MeetingToolbar/Updated',
 'runtime_visual_comparison_scope': 'Meeting toolbar visible in the active-call screen'},
        )
        self.assertIs(result['passed'], True)

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
                                                      'pre-merge code review.'],
                       'release_qa_artifacts': []}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_pre_merge_code_review')
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

    def test_approve_refine_rejects_approved_with_additional_refinement(self):
        result = verifiers.verify_approve_refine(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='approve_refine',
            observation={'status': 'succeeded',
 'summary': 'Approval output was internally inconsistent.',
 'structured_output': {'user_approved': True,
                       'user_feedback': 'Proceed.',
                       'additional_refinement_needed': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_approve_refine_rejects_rejection_without_refinement_request(self):
        result = verifiers.verify_approve_refine(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='approve_refine',
            observation={'status': 'succeeded',
 'summary': 'User did not approve but no refinement request was recorded.',
 'structured_output': {'user_approved': False,
                       'user_feedback': 'Not ready yet.',
                       'additional_refinement_needed': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

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

    def test_completion_verification_missing_inputs_route_to_unblocking(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification is blocked on missing evidence inputs.',
 'structured_output': {'verification_passed': False,
                       'verification_summary': 'Need one more external verification artifact '
                                               'before completion can be claimed.',
                       'verification_evidence': ['Reviewed existing release QA and review '
                                                 'evidence.'],
                       'remaining_risks': ['Completion evidence is incomplete.'],
                       'missing_verification_inputs': ['final device screenshot']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_unblocking_input')
        self.assertEqual(result.branch_kind, 'repair')

    def test_completion_verification_rejects_failed_without_remaining_risks(self):
        result = verifiers.verify_verify_completion(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='verify_completion',
            observation={'status': 'succeeded',
 'summary': 'Final verification failed without listing remaining risks.',
 'structured_output': {'verification_passed': False,
                       'verification_summary': 'Verification is still incomplete.',
                       'verification_evidence': ['Reviewed prior evidence.'],
                       'remaining_risks': [],
                       'missing_verification_inputs': []}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_repair_context_keeps_precise_verifier_requirements(self):
        state = self._make_state(None)
        workflow_state.record_observation(
            state,
            current_step_id='verify_completion',
            observation={
                'status': 'succeeded',
                'summary': 'Final verification passed without fresh evidence.',
                'structured_output': {
                    'verification_passed': True,
                    'verification_summary': 'Verified.',
                    'verification_evidence': [],
                    'remaining_risks': [],
                    'missing_verification_inputs': [],
                },
            },
            verifier_result={
                'passed': False,
                'message': 'Completion verification must record at least one fresh evidence item.',
                'details': {},
            },
        )
        repair_payload = state.repair_context.get('repair_payload') or {}
        self.assertEqual(state.repair_context.get('transition_reason'), 'verifier_failed')
        self.assertEqual(repair_payload.get('category'), 'verifier_failed')
        self.assertEqual(
            repair_payload.get('requirements'),
            ['Completion verification must record at least one fresh evidence item.'],
        )

    def test_repair_template_context_uses_trimmed_payload_fields(self):
        state = self._make_state(None)
        state.return_stage_id = 'verify_completion'
        state.repair_context = {
            'source_stage_id': 'verify_completion',
            'return_stage_id': 'verify_completion',
            'transition_reason': 'blocked',
            'repair_payload': {
                'category': 'blocked',
                'summary': 'Final completion verification needs external verification inputs before completion can be claimed.',
                'requirements': ['final device screenshot'],
                'evidence': ['Completion evidence is incomplete.'],
            },
        }
        context = graphbuilder_runtime.build_template_context(
            step_id='request_unblocking_input',
            run_state=SimpleNamespace(graph_state=workflow_state.serialize_state(state)),
        )
        self.assertEqual(context['repair_category'], 'blocked')
        self.assertIn('final device screenshot', context['repair_requirements'])
        self.assertEqual(context['repair_evidence'], '- Completion evidence is incomplete.')

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

    def test_generated_max_steps_preserves_return_stage_for_unblocking(self):
        state = self._make_state({'constraints': {'max_steps': 1}, 'attempt_counts': {}})
        expected_return_stage = 'verify_completion'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id=expected_return_stage,
            observation={'status': 'succeeded', 'summary': 'Workflow hit max steps.', 'structured_output': {}},
            verifier_result={'passed': True, 'checks': []},
        )
        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(state.return_stage_id, expected_return_stage)


if __name__ == "__main__":
    unittest.main()
