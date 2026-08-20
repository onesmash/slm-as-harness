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

from workflows.earnings_reviewer import graphbuilder_runtime, state as workflow_state, verifiers


class EarningsReviewerWorkflowGeneratedTests(unittest.TestCase):
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

    def test_packet_not_ready_retries_collect(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='collect_earnings_packet',
            observation={'status': 'succeeded',
 'summary': 'Packet still missing the transcript.',
 'structured_output': {'ticker': 'NVDA',
                       'reporting_period': 'Q1-FY27',
                       'earnings_packet_path': 'out/nvda-q1-fy27-packet.md',
                       'transcript_locator': '',
                       'filings_inventory': ['8-K'],
                       'actuals_source': 'FactSet',
                       'consensus_source': 'FactSet',
                       'skip_note': False,
                       'missing_packet_inputs': ['transcript'],
                       'packet_ready': False}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'collect_earnings_packet')
        self.assertEqual(result.branch_kind, 'retry')

    def test_packet_not_ready_passes_verifier(self):
        result = verifiers.verify_collect_earnings_packet(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='collect_earnings_packet',
            observation={'status': 'succeeded',
 'summary': 'Packet still missing the transcript.',
 'structured_output': {'ticker': 'NVDA',
                       'reporting_period': 'Q1-FY27',
                       'earnings_packet_path': 'out/nvda-q1-fy27-packet.md',
                       'transcript_locator': '',
                       'filings_inventory': ['8-K'],
                       'actuals_source': 'FactSet',
                       'consensus_source': 'FactSet',
                       'skip_note': False,
                       'missing_packet_inputs': ['transcript'],
                       'packet_ready': False}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_packet_ready_without_transcript_fails_verifier(self):
        result = verifiers.verify_collect_earnings_packet(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='collect_earnings_packet',
            observation={'status': 'succeeded',
 'summary': 'Packet claimed ready without a transcript.',
 'structured_output': {'ticker': 'NVDA',
                       'reporting_period': 'Q1-FY27',
                       'earnings_packet_path': 'out/nvda-q1-fy27-packet.md',
                       'transcript_locator': '',
                       'filings_inventory': ['8-K'],
                       'actuals_source': 'FactSet',
                       'consensus_source': 'FactSet',
                       'skip_note': False,
                       'missing_packet_inputs': [],
                       'packet_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_call_analysis_not_ready_retries_analyze(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='analyze_earnings_call',
            observation={'status': 'succeeded',
 'summary': 'Call read still incomplete.',
 'structured_output': {'headline_read': 'Print mixed.',
                       'beat_miss_summary': 'Revenue beat, EPS miss.',
                       'guidance_changes': [],
                       'management_tone': 'cautious',
                       'dodged_questions': [],
                       'thesis_impact': 'unchanged',
                       'call_analysis_summary': 'Need remaining Q&A.',
                       'unsourced_flags': [],
                       'used_full_transcript': True,
                       'call_analysis_ready': False}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'analyze_earnings_call')
        self.assertEqual(result.branch_kind, 'retry')

    def test_update_without_handoff_continues_to_audit(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Model updated; no DCF rebuild.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA', 'EPS'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'},
                                         {'metric': 'EPS',
                                          'actual': '1.10',
                                          'consensus': '1.00',
                                          'prior_estimate': '1.02',
                                          'source': 'FactSet'}],
                       'estimate_change_summary': 'FY EPS raised on revenue beat.',
                       'price_target_change': 'unchanged',
                       'thesis_change_summary': 'noise',
                       'requires_model_builder_handoff': False,
                       'skip_note': False,
                       'model_update_ready': True}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'audit_coverage_model')
        self.assertEqual(result.branch_kind, 'continue')

    def test_thesis_change_handoff_still_continues_to_audit(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Actuals in; DCF thesis changed.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA', 'EPS'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'},
                                         {'metric': 'EPS',
                                          'actual': '1.10',
                                          'consensus': '1.00',
                                          'prior_estimate': '1.02',
                                          'source': 'FactSet'}],
                       'estimate_change_summary': 'FY EPS cut on margin.',
                       'price_target_change': 'pending DCF',
                       'thesis_change_summary': 'Structural margin reset requires DCF rebuild.',
                       'requires_model_builder_handoff': True,
                       'skip_note': False,
                       'model_update_ready': True,
                       'handoff_target': 'model-builder',
                       'handoff_reason': 'Rebuild DCF after structural margin reset.',
                       'handoff_payload': {'ticker': 'NVDA',
                                           'reporting_period': 'Q1-FY27',
                                           'updated_model_path': 'out/model-NVDA.xlsx',
                                           'thesis_change_summary': 'Structural margin reset '
                                                                    'requires DCF rebuild.'}}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'audit_coverage_model')
        self.assertEqual(result.branch_kind, 'continue')

    def test_variance_missing_eps_fails_verifier(self):
        result = verifiers.verify_update_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Variance table missing EPS.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'}],
                       'estimate_change_summary': 'Revenue beat.',
                       'price_target_change': 'unchanged',
                       'thesis_change_summary': 'noise',
                       'requires_model_builder_handoff': False,
                       'skip_note': False,
                       'model_update_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_complete_variance_table_passes_verifier(self):
        result = verifiers.verify_update_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Four-metric sourced variance table.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA', 'EPS'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'},
                                         {'metric': 'EPS',
                                          'actual': '1.10',
                                          'consensus': '1.00',
                                          'prior_estimate': '1.02',
                                          'source': 'FactSet'}],
                       'estimate_change_summary': 'FY EPS raised on revenue beat.',
                       'price_target_change': 'unchanged',
                       'thesis_change_summary': 'noise',
                       'requires_model_builder_handoff': False,
                       'skip_note': False,
                       'model_update_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_unsourced_variance_without_flag_fails_verifier(self):
        result = verifiers.verify_update_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'EPS actual has no source.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA', 'EPS'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'},
                                         {'metric': 'EPS',
                                          'actual': '1.10',
                                          'consensus': '1.00',
                                          'prior_estimate': '1.02',
                                          'source': 'internal estimate'}],
                       'estimate_change_summary': 'FY EPS raised.',
                       'price_target_change': 'unchanged',
                       'thesis_change_summary': 'noise',
                       'requires_model_builder_handoff': False,
                       'skip_note': False,
                       'model_update_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_negated_filing_source_fails_verifier(self):
        result = verifiers.verify_update_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'EPS source is not a filing.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA', 'EPS'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'},
                                         {'metric': 'EPS',
                                          'actual': '1.10',
                                          'consensus': '1.00',
                                          'prior_estimate': '1.02',
                                          'source': 'not a filing'}],
                       'estimate_change_summary': 'FY EPS raised on revenue beat.',
                       'price_target_change': 'unchanged',
                       'thesis_change_summary': 'noise',
                       'requires_model_builder_handoff': False,
                       'skip_note': False,
                       'model_update_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_variance_row_missing_consensus_fails_verifier(self):
        result = verifiers.verify_update_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'EPS row missing consensus.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA', 'EPS'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'},
                                         {'metric': 'EPS',
                                          'actual': '1.10',
                                          'consensus': '',
                                          'prior_estimate': '1.02',
                                          'source': 'FactSet'}],
                       'estimate_change_summary': 'FY EPS raised on revenue beat.',
                       'price_target_change': 'unchanged',
                       'thesis_change_summary': 'noise',
                       'requires_model_builder_handoff': False,
                       'skip_note': False,
                       'model_update_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_required_handoff_empty_payload_fails_verifier(self):
        result = verifiers.verify_update_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Handoff required but payload empty.',
 'structured_output': {'updated_model_path': 'out/model-NVDA.xlsx',
                       'variance_metrics': ['Revenue', 'GM', 'EBITDA', 'EPS'],
                       'variance_rows': [{'metric': 'Revenue',
                                          'actual': '10',
                                          'consensus': '9',
                                          'prior_estimate': '9.5',
                                          'source': 'FactSet'},
                                         {'metric': 'GM',
                                          'actual': '70%',
                                          'consensus': '69%',
                                          'prior_estimate': '69%',
                                          'source': '10-Q'},
                                         {'metric': 'EBITDA',
                                          'actual': '5',
                                          'consensus': '4.8',
                                          'prior_estimate': '4.9',
                                          'source': 'Daloopa'},
                                         {'metric': 'EPS',
                                          'actual': '1.10',
                                          'consensus': '1.00',
                                          'prior_estimate': '1.02',
                                          'source': 'FactSet'}],
                       'estimate_change_summary': 'FY EPS raised on revenue beat.',
                       'price_target_change': 'unchanged',
                       'thesis_change_summary': 'noise',
                       'requires_model_builder_handoff': True,
                       'skip_note': False,
                       'model_update_ready': True,
                       'handoff_target': 'model-builder',
                       'handoff_reason': 'Need DCF rebuild.',
                       'handoff_payload': {}}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_skip_note_after_audit_goes_to_final(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='audit_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Model audited; skip the note.',
 'structured_output': {'audit_summary': 'Model type: 3-stmt — Overall: Clean — 0 critical',
                       'audit_findings': [],
                       'critical_finding_count': 0,
                       'skip_note': True,
                       'model_audit_ready': True}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'finalize_earnings_review')
        self.assertEqual(result.branch_kind, 'complete')

    def test_skip_note_false_continues_to_draft(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='audit_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Model audited; draft the note.',
 'structured_output': {'audit_summary': 'Model type: 3-stmt — Overall: Clean — 0 critical',
                       'audit_findings': [],
                       'critical_finding_count': 0,
                       'skip_note': False,
                       'model_audit_ready': True}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'draft_earnings_note')
        self.assertEqual(result.branch_kind, 'continue')

    def test_empty_audit_findings_pass_verifier(self):
        result = verifiers.verify_audit_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='audit_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Clean audit.',
 'structured_output': {'audit_summary': 'Model type: 3-stmt — Overall: Clean — 0 critical',
                       'audit_findings': [],
                       'critical_finding_count': 0,
                       'skip_note': False,
                       'model_audit_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_unresolved_critical_audit_fails_verifier(self):
        result = verifiers.verify_audit_coverage_model(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='audit_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'BS still does not balance.',
 'structured_output': {'audit_summary': 'Major Issues',
                       'audit_findings': ['Critical: BS does not balance in Q1'],
                       'critical_finding_count': 0,
                       'skip_note': False,
                       'model_audit_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_audit_blocked_goes_to_shared_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='audit_coverage_model',
            observation={'status': 'blocked',
 'summary': 'Workbook unreadable.',
 'structured_output': {'blocked_reason': 'updated model missing',
                       'missing_inputs': ['updated_model_path']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'repair')

    def test_audit_verifier_failed_goes_to_model_audit_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='audit_coverage_model',
            observation={'status': 'succeeded',
 'summary': 'Audit claimed ready with critical findings.',
 'structured_output': {'audit_summary': 'Major Issues',
                       'audit_findings': ['Critical: BS does not balance in Q1'],
                       'critical_finding_count': 0,
                       'skip_note': False,
                       'model_audit_ready': True}},
            verifier_result={'passed': False},
        )
        self.assertEqual(result.step_id, 'repair_model_audit')
        self.assertEqual(result.branch_kind, 'repair')

    def test_published_note_fails_verifier(self):
        result = verifiers.verify_draft_earnings_note(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='draft_earnings_note',
            observation={'status': 'succeeded',
 'summary': 'Note was published.',
 'structured_output': {'note_path': 'out/note-NVDA.md',
                       'note_headline': 'NVDA beats on data center.',
                       'note_includes_variance_table': True,
                       'published_externally': True,
                       'note_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_unpublished_note_passes_verifier(self):
        result = verifiers.verify_draft_earnings_note(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='draft_earnings_note',
            observation={'status': 'succeeded',
 'summary': 'Staged unpublished note.',
 'structured_output': {'note_path': 'out/note-NVDA.md',
                       'note_headline': 'NVDA beats on data center.',
                       'note_includes_variance_table': True,
                       'published_externally': False,
                       'note_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_draft_ready_completes_to_final(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='draft_earnings_note',
            observation={'status': 'succeeded',
 'summary': 'Note staged.',
 'structured_output': {'note_path': 'out/note-NVDA.md',
                       'note_headline': 'NVDA beats on data center.',
                       'note_includes_variance_table': True,
                       'published_externally': False,
                       'note_ready': True}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'finalize_earnings_review')
        self.assertEqual(result.branch_kind, 'complete')

    def test_generated_request_unblocking_input_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'collect_earnings_packet'
        state.repair_context = {'source_stage_id': 'request_unblocking_input'}
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {'blocking_reason': 'Approval was missing.', 'user_action_needed': 'Confirm the approval.', 'suggested_next_input': 'Approval confirmed.'}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'collect_earnings_packet')
        self.assertEqual(result.branch_kind, "continue")

    def test_generated_request_unblocking_input_without_return_stage_stays_put(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {'blocking_reason': 'Approval was missing.', 'user_action_needed': 'Confirm the approval.', 'suggested_next_input': 'Approval confirmed.'}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")

    def test_generated_request_unblocking_input_returns_to_repair_owner(self):
        state = self._make_state(None)
        state.return_stage_id = 'collect_earnings_packet'
        state.repair_context = {'source_stage_id': 'repair_and_resume'}
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {'blocking_reason': 'Approval was missing.', 'user_action_needed': 'Confirm the approval.', 'suggested_next_input': 'Approval confirmed.'}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "continue")

    def test_generated_repair_and_resume_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'collect_earnings_packet'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {'retry_reason': 'Retry is safe after the repair.', 'retry_notes': 'The missing dependency was refreshed.', 'repair_actions': ['Retry the original stage.']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'collect_earnings_packet')
        self.assertEqual(result.branch_kind, "continue")

    def test_generated_repair_and_resume_without_return_stage_stays_put(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id="repair_and_resume",
            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {'retry_reason': 'Retry is safe after the repair.', 'retry_notes': 'The missing dependency was refreshed.', 'repair_actions': ['Retry the original stage.']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "retry")

    def test_generated_repair_and_resume_blocked_before_threshold_retries_locally(self):
        state = self._make_state(None)
        state.return_stage_id = 'draft_earnings_note'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "retry")
        self.assertEqual(state.return_stage_id, 'draft_earnings_note')

    def test_generated_repair_and_resume_blocked_after_threshold_requests_unblocking(self):
        state = self._make_state({'attempt_counts': {'repair_and_resume': 2}})
        state.return_stage_id = 'draft_earnings_note'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'request_unblocking_input')
        self.assertEqual(result.branch_kind, 'repair')
        self.assertEqual(state.return_stage_id, 'draft_earnings_note')

    def test_generated_blocked_repair_context_preserves_host_visible_summary(self):
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        response = engine.start('earnings_reviewer', {
            "task_input": {"goal": "generated workflow regression"},
            "context": {"repo_root": str(REPO_ROOT)},
            "constraints": {"max_steps": 5},
        })
        run_id = response['run_id']
        response = engine.resume(run_id, {
            'run_id': run_id,
            'step_id': 'collect_earnings_packet',
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

    def test_generated_template_context_prefers_state_for_reporting_period(self):
        state = self._make_state(None)
        state.task_input['reporting_period'] = 'stale-input-value'
        state.reporting_period = 'state-preferred-value'
        context = graphbuilder_runtime._template_context_from_state(state)
        self.assertEqual(context['reporting_period'], 'state-preferred-value')

    def test_generated_template_context_prefers_state_for_skip_note(self):
        state = self._make_state(None)
        state.task_input['skip_note'] = 'stale-input-value'
        state.skip_note = 'state-preferred-value'
        context = graphbuilder_runtime._template_context_from_state(state)
        self.assertEqual(context['skip_note'], 'state-preferred-value')

    def test_generated_template_context_prefers_state_for_ticker(self):
        state = self._make_state(None)
        state.task_input['ticker'] = 'stale-input-value'
        state.ticker = 'state-preferred-value'
        context = graphbuilder_runtime._template_context_from_state(state)
        self.assertEqual(context['ticker'], 'state-preferred-value')


if __name__ == "__main__":
    unittest.main()
