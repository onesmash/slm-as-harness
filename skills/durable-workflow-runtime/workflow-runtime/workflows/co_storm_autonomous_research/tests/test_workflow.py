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

from workflows.co_storm_autonomous_research import graphbuilder_runtime, state as workflow_state, verifiers


class CoStormAutonomousResearchWorkflowGeneratedTests(unittest.TestCase):
    def _roster(self):
        return [
            {'id': 'historian', 'role': 'historian', 'brief': 'Trace origins and chronology.'},
            {'id': 'systems_analyst', 'role': 'systems analyst', 'brief': 'Trace mechanisms and trade-offs.'},
        ]

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

    def test_warm_start_success_enters_expert_fanout(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='warm_start_shared_space',
            observation={'status': 'succeeded',
 'summary': 'Warm start completed.',
 'structured_output': {'expert_roster': self._roster(),
                       'conversation_transcript': ['background turn', 'perspective turn'],
                       'knowledge_map_summary': 'root with two supported topics',
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'round_index': 0,
                       'warm_start_ready': True}},
            verifier_result={'passed': True, 'message': 'warm-start contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'launch_expert_subagents')
        self.assertEqual(result.branch_kind, 'continue')

    def test_expert_fanout_success_enters_roundtable(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'expert_roster': self._roster(),
 'round_index': 0,
 'constraints': {'max_rounds': 8}}),
            current_step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'All independent expert subagents completed.',
 'structured_output': {'execution_mode': 'parallel_fanout',
                       'fanout_round_index': 1,
                       'subagent_expert_ids': ['historian', 'systems_analyst'],
                       'subagent_run_ids': ['run-historian-1', 'run-systems-analyst-1'],
                       'subagent_result_summaries': ['Historian perspective completed.',
                                                     'Systems analyst perspective completed.'],
                       'subagent_artifact_paths': ['reports/subagents/1/historian.md',
                                                   'reports/subagents/1/systems_analyst.md'],
                       'subagent_binding_records': [
                           {'artifact_path': 'reports/subagents/1/historian.md',
                            'completion_receipt': 'join-round-1',
                            'expert_id': 'historian',
                            'spawn_receipt': 'spawn-run-historian-1',
                            'subagent_run_id': 'run-historian-1',
                            'summary': 'Historian perspective completed.'},
                           {'artifact_path': 'reports/subagents/1/systems_analyst.md',
                            'completion_receipt': 'join-round-1',
                            'expert_id': 'systems_analyst',
                            'spawn_receipt': 'spawn-run-systems-analyst-1',
                            'subagent_run_id': 'run-systems-analyst-1',
                            'summary': 'Systems analyst perspective completed.'}],
                       'fanout_complete': True},
 'tool_trace': [{'tool_name': 'host.subagent.spawn',
                 'status': 'succeeded',
                 'metadata': {'phase': 'spawn',
                              'expert_id': 'historian',
                              'subagent_run_id': 'run-historian-1',
                              'fanout_round_index': 1,
                              'receipt_id': 'spawn-run-historian-1'}},
                {'tool_name': 'host.subagent.wait',
                 'status': 'completed',
                 'metadata': {'phase': 'wait',
                              'expert_id': 'historian',
                              'subagent_run_id': 'run-historian-1',
                              'fanout_round_index': 1,
                              'receipt_id': 'wait-run-historian-1'}},
                {'tool_name': 'host.subagent.spawn',
                 'status': 'succeeded',
                 'metadata': {'phase': 'spawn',
                              'expert_id': 'systems_analyst',
                              'subagent_run_id': 'run-systems-analyst-1',
                              'fanout_round_index': 1,
                              'receipt_id': 'spawn-run-systems-analyst-1'}},
                {'tool_name': 'host.subagent.wait',
                 'status': 'completed',
                 'metadata': {'phase': 'wait',
                              'expert_id': 'systems_analyst',
                              'subagent_run_id': 'run-systems-analyst-1',
                              'fanout_round_index': 1,
                              'receipt_id': 'wait-run-systems-analyst-1'}},
                {'tool_name': 'host.subagent.join',
                 'status': 'completed',
                 'metadata': {'phase': 'join',
                              'expert_ids': ['historian', 'systems_analyst'],
                              'subagent_run_ids': ['run-historian-1', 'run-systems-analyst-1'],
                              'fanout_round_index': 1,
                              'receipt_id': 'join-round-1'}}]},
            verifier_result={'passed': True, 'message': 'fan-out contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'autonomous_roundtable')
        self.assertEqual(result.branch_kind, 'continue')

    def test_roundtable_continue_starts_next_expert_fanout(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'Moderator selected another expert.',
 'structured_output': {'last_turn_summary': 'The analyst added a grounded comparison.',
                       'conversation_transcript': ['prior turn', 'new analyst turn'],
                       'evidence_registry': ['[1] source-a',
                                             '[2] source-b',
                                             '[3] source-c',
                                             '[4] source-d'],
                       'coverage_map': ['history', 'mechanism', 'comparison'],
                       'knowledge_map_summary': 'root with three supported topics',
                       'expert_roster': self._roster(),
                       'round_index': 1,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'launch_expert_subagents')
        self.assertEqual(result.branch_kind, 'continue')

    def test_roundtable_reorganize_branch(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'Moderator requested a mind-map reorganization.',
 'structured_output': {'last_turn_summary': 'The moderator found overlapping branches.',
                       'conversation_transcript': ['prior turn', 'overlap finding'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'knowledge_map_summary': 'overlapping branches detected',
                       'expert_roster': self._roster(),
                       'round_index': 2,
                       'round_decision': 'reorganize',
                       'continue_roundtable': False,
                       'should_reorganize': True,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'reorganize_knowledge_space')
        self.assertEqual(result.branch_kind, 'reorganize')

    def test_roundtable_report_branch(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'Coverage reached the stopping threshold.',
 'structured_output': {'last_turn_summary': 'The moderator confirmed coverage saturation.',
                       'conversation_transcript': ['prior turn', 'final coverage turn'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism', 'comparison'],
                       'knowledge_map_summary': 'complete supported map',
                       'expert_roster': self._roster(),
                       'round_index': 3,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': True,
                       'ready_for_report': True}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'synthesize_report')
        self.assertEqual(result.branch_kind, 'complete_research')

    def test_reorganization_returns_to_roundtable(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='reorganize_knowledge_space',
            observation={'status': 'succeeded',
 'summary': 'Knowledge map reorganized.',
 'structured_output': {'knowledge_map_summary': 'deduplicated supported map',
                       'coverage_map': ['history', 'mechanism'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'reorganization_summary': 'Merged duplicate mechanism nodes.',
                       'reorganization_count': 1,
                       'reorganized': True}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'launch_expert_subagents')
        self.assertEqual(result.branch_kind, 'continue')

    def test_failed_report_verification_enters_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_report',
            observation={'status': 'succeeded',
 'summary': 'Unknown citation marker found.',
 'structured_output': {'quality_verdict': 'repair',
                       'quality_findings': ['Unknown citation [99]'],
                       'citation_coverage_summary': 'One citation is unresolved.',
                       'report_ready': False,
                       'verified_report_path': 'reports/draft.md'}},
            verifier_result={'passed': False, 'message': 'citation integrity failed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'repair_report')
        self.assertEqual(result.branch_kind, 'repair')

    def test_report_repair_returns_to_synthesis(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='repair_report',
            observation={'status': 'succeeded',
 'summary': 'Report repair actions prepared.',
 'structured_output': {'report_repair_summary': 'Replace the unresolved citation with evidence '
                                                '[2].',
                       'repair_actions': ['replace unknown citation'],
                       'repair_ready': True}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'synthesize_report')
        self.assertEqual(result.branch_kind, 'continue')

    def test_warm_start_rejects_insufficient_experts(self):
        result = verifiers.verify_warm_start_shared_space(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='warm_start_shared_space',
            observation={'status': 'succeeded',
 'summary': 'Warm start returned one perspective.',
 'structured_output': {'expert_roster': [{'id': 'generalist', 'role': 'generalist', 'brief': 'Provide a broad but single perspective.'}],
                       'conversation_transcript': ['one turn', 'another turn'],
                       'knowledge_map_summary': 'partial map',
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'round_index': 0,
                       'warm_start_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_roundtable_rejects_ambiguous_decision(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'Two routing flags were selected.',
 'structured_output': {'last_turn_summary': 'The moderator produced a turn.',
                       'conversation_transcript': ['prior turn', 'new turn'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'knowledge_map_summary': 'supported map',
                       'expert_roster': self._roster(),
                       'round_index': 1,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': True,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            state={'expert_roster': self._roster(), 'round_index': 0, 'conversation_transcript': ['prior turn'], 'constraints': {'max_rounds': 3}, 'fanout_complete': True, 'subagent_run_ids': ['run-historian-1', 'run-systems-analyst-1']},
        )
        self.assertIs(result['passed'], False)

    def test_roundtable_rejects_premature_report(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'Report was selected before coverage was sufficient.',
 'structured_output': {'last_turn_summary': 'The moderator produced a turn.',
                       'conversation_transcript': ['prior turn', 'new turn'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'knowledge_map_summary': 'partial map',
                       'expert_roster': self._roster(),
                       'round_index': 1,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': True}},
            state={'expert_roster': self._roster(), 'round_index': 0, 'conversation_transcript': ['prior turn'], 'constraints': {'max_rounds': 3}, 'fanout_complete': True, 'subagent_run_ids': ['run-historian-1', 'run-systems-analyst-1']},
        )
        self.assertIs(result['passed'], False)

    def test_reorganization_rejects_budget_overrun(self):
        result = verifiers.verify_reorganize_knowledge_space(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='reorganize_knowledge_space',
            observation={'status': 'succeeded',
 'summary': 'Reorganization exceeded the autonomous budget.',
 'structured_output': {'knowledge_map_summary': 'deduplicated map',
                       'coverage_map': ['history', 'mechanism'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'reorganization_summary': 'Merged duplicate branches.',
                       'reorganization_count': 3,
                       'reorganized': True}},
            state={'constraints': {'max_reorganizations': 2}, 'reorganization_count': 2},
        )
        self.assertIs(result['passed'], False)

    def test_warm_start_accepts_valid_package(self):
        result = verifiers.verify_warm_start_shared_space(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='warm_start_shared_space',
            observation={'status': 'succeeded',
 'summary': 'Warm start produced a grounded shared space.',
 'structured_output': {'expert_roster': self._roster(),
                       'conversation_transcript': ['background turn', 'perspective turn'],
                       'knowledge_map_summary': 'root with two supported topics',
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'round_index': 0,
                       'warm_start_ready': True}},
            state={},
        )
        self.assertIs(result['passed'], True)

    def test_roundtable_accepts_one_appended_turn(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'The moderator selected another expert.',
 'structured_output': {'last_turn_summary': 'The analyst added a grounded comparison.',
                       'conversation_transcript': ['prior turn', 'new analyst turn'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'knowledge_map_summary': 'supported map',
                       'expert_roster': self._roster(),
                       'round_index': 1,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            state={'expert_roster': self._roster(), 'round_index': 0, 'conversation_transcript': ['prior turn'], 'constraints': {'max_rounds': 3}, 'fanout_complete': True, 'subagent_run_ids': ['run-historian-1', 'run-systems-analyst-1']},
        )
        self.assertIs(result['passed'], True)

    def test_roundtable_rejects_skipped_round(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'The moderator skipped a round index.',
 'structured_output': {'last_turn_summary': 'The analyst added a grounded comparison.',
                       'conversation_transcript': ['prior turn', 'new analyst turn'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'knowledge_map_summary': 'supported map',
                       'expert_roster': self._roster(),
                       'round_index': 2,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            state={'expert_roster': self._roster(), 'round_index': 0, 'conversation_transcript': ['prior turn'], 'constraints': {'max_rounds': 3}, 'fanout_complete': True, 'subagent_run_ids': ['run-historian-1', 'run-systems-analyst-1']},
        )
        self.assertIs(result['passed'], False)

    def test_reorganization_accepts_first_budgeted_pass(self):
        result = verifiers.verify_reorganize_knowledge_space(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='reorganize_knowledge_space',
            observation={'status': 'succeeded',
 'summary': 'The knowledge map was reorganized.',
 'structured_output': {'knowledge_map_summary': 'deduplicated supported map',
                       'coverage_map': ['history', 'mechanism'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'reorganization_summary': 'Merged duplicate mechanism nodes.',
                       'reorganization_count': 1,
                       'reorganized': True}},
            state={'constraints': {'max_reorganizations': 2}},
        )
        self.assertIs(result['passed'], True)

    def test_generated_request_unblocking_input_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'warm_start_shared_space'
        state.repair_context = {'source_stage_id': 'request_unblocking_input'}
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'warm_start_shared_space')
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
        state.return_stage_id = 'warm_start_shared_space'
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
        state.return_stage_id = 'warm_start_shared_space'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'warm_start_shared_space')
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
        state.return_stage_id = 'verify_report'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "retry")
        self.assertEqual(state.return_stage_id, 'verify_report')

    def test_generated_repair_and_resume_blocked_after_threshold_requests_unblocking(self):
        state = self._make_state({'attempt_counts': {'repair_and_resume': 2}})
        state.return_stage_id = 'verify_report'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(state.return_stage_id, 'verify_report')

    def test_generated_blocked_repair_context_preserves_host_visible_summary(self):
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        response = engine.start('co_storm_autonomous_research', {
            "task_input": {"goal": "generated workflow regression"},
            "context": {"repo_root": str(REPO_ROOT)},
            "constraints": {"max_steps": 5},
        })
        run_id = response['run_id']
        response = engine.resume(run_id, {
            'run_id': run_id,
            'step_id': 'warm_start_shared_space',
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


if __name__ == "__main__":
    unittest.main()
