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

    def test_warm_start_success_enters_expert_results(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='warm_start_shared_space',
            observation={'status': 'succeeded',
 'summary': 'Warm start completed.',
 'structured_output': {'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
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

    def test_expert_results_success_enters_roundtable(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'constraints': {'max_rounds': 8},
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}),
            current_step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'All expert results completed.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed.',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed.',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            verifier_result={'passed': True, 'message': 'expert-result contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'autonomous_roundtable')
        self.assertEqual(result.branch_kind, 'continue')

    def test_roundtable_continue_starts_next_expert_results(self):
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
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 1,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            verifier_result={'passed': True, 'message': 'roundtable contract passed', 'details': {}},
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
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 2,
                       'round_decision': 'reorganize',
                       'continue_roundtable': False,
                       'should_reorganize': True,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            verifier_result={'passed': True, 'message': 'roundtable contract passed', 'details': {}},
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
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 3,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': True,
                       'ready_for_report': True}},
            verifier_result={'passed': True, 'message': 'roundtable contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'synthesize_report')
        self.assertEqual(result.branch_kind, 'complete_research')

    def test_roundtable_unmatched_decision_retries_stage(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'Moderator output did not contain an exclusive routing decision.',
 'structured_output': {'last_turn_summary': 'The moderator needs another grounded turn.'}},
            verifier_result={'passed': True, 'message': 'roundtable contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'autonomous_roundtable')
        self.assertEqual(result.branch_kind, 'retry')

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
            verifier_result={'passed': True, 'message': 'reorganization contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'launch_expert_subagents')
        self.assertEqual(result.branch_kind, 'continue')

    def test_reorganization_unmatched_decision_retries_stage(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='reorganize_knowledge_space',
            observation={'status': 'succeeded',
 'summary': 'Knowledge-space reorganization was incomplete.',
 'structured_output': {'knowledge_map_summary': 'The map still contains an overloaded branch.'}},
            verifier_result={'passed': True, 'message': 'reorganization contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'reorganize_knowledge_space')
        self.assertEqual(result.branch_kind, 'retry')

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

    def test_report_verification_without_verifier_fails_closed(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='verify_report',
            observation={'status': 'succeeded',
 'summary': 'Report output arrived without an authoritative verifier result.',
 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
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
            verifier_result={'passed': True, 'message': 'report repair contract passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'synthesize_report')
        self.assertEqual(result.branch_kind, 'continue')

    def test_repair_exhaustion_returns_partial_handoff(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'attempt_counts': {'repair_and_resume': 3}}),
            current_step_id='repair_and_resume',
            observation={'status': 'blocked',
 'summary': 'Repair remains blocked after bounded self-repair.',
 'structured_output': {'missing_inputs': ['repair evidence']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'finalize_collaborative_report')
        self.assertEqual(result.branch_kind, 'partial')

    def test_warm_start_rejects_insufficient_experts(self):
        result = verifiers.verify_warm_start_shared_space(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='warm_start_shared_space',
            observation={'status': 'succeeded',
 'summary': 'Warm start returned one perspective.',
 'structured_output': {'expert_roster': [{'id': 'generalist',
                                          'role': 'generalist',
                                          'brief': 'Provide a broad but single perspective.'}],
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
                       'coverage_assessment': [{'topic_id': 'history',
                                                'status': 'covered',
                                                'evidence_refs': ['[1]'],
                                                'open_gaps': [],
                                                'next_validation_metrics': []},
                                               {'topic_id': 'mechanism',
                                                'status': 'missing',
                                                'evidence_refs': [],
                                                'open_gaps': ['Causal mechanism is not yet '
                                                              'corroborated.'],
                                                'next_validation_metrics': ['Find two independent '
                                                                            'sources that support '
                                                                            'the causal chain.']}],
                       'coverage_decision_rationale': 'History is grounded, but the mechanism '
                                                      'still needs independent corroboration.',
                       'next_round_validation_plan': ['mechanism — Find two independent sources '
                                                      'that support the causal chain.'],
                       'report_scope_status': 'in_progress',
                       'knowledge_map_summary': 'supported map',
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 1,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': True,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'Historian perspective completed.',
                     'artifact_path': 'reports/experts/1/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Systems analyst perspective completed.',
                     'artifact_path': 'reports/experts/1/systems_analyst.md'}]},
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
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 1,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': True}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'Historian perspective completed.',
                     'artifact_path': 'reports/experts/1/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Systems analyst perspective completed.',
                     'artifact_path': 'reports/experts/1/systems_analyst.md'}]},
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
 'structured_output': {'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
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
                       'coverage_assessment': [{'topic_id': 'history',
                                                'status': 'covered',
                                                'evidence_refs': ['[1]'],
                                                'open_gaps': [],
                                                'next_validation_metrics': []},
                                               {'topic_id': 'mechanism',
                                                'status': 'missing',
                                                'evidence_refs': [],
                                                'open_gaps': ['Causal mechanism is not yet '
                                                              'corroborated.'],
                                                'next_validation_metrics': ['Find two independent '
                                                                            'sources that support '
                                                                            'the causal chain.']}],
                       'coverage_decision_rationale': 'History is grounded, but the mechanism '
                                                      'still needs independent corroboration.',
                       'next_round_validation_plan': ['mechanism — Find two independent sources '
                                                      'that support the causal chain.'],
                       'report_scope_status': 'in_progress',
                       'knowledge_map_summary': 'supported map',
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 1,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'Historian perspective completed.',
                     'artifact_path': 'reports/experts/1/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Systems analyst perspective completed.',
                     'artifact_path': 'reports/experts/1/systems_analyst.md'}],
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']},
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
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 2,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'Historian perspective completed.',
                     'artifact_path': 'reports/experts/1/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Systems analyst perspective completed.',
                     'artifact_path': 'reports/experts/1/systems_analyst.md'}]},
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
            state={'constraints': {'max_reorganizations': 2},
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']},
        )
        self.assertIs(result['passed'], True)

    def test_expert_results_rejects_incomplete_package(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The expert-result package was not complete.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed.',
                                           'artifact_path': 'reports/experts/1/historian.md',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed.',
                                           'artifact_path': 'reports/experts/1/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': False,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_too_few_results(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'Only one expert result was returned.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed.',
                                           'artifact_path': 'reports/experts/1/historian.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_accepts_valid_package(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The expert-result package is valid.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], True)

    def test_expert_results_rejects_unknown_expert(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The package contains an unknown expert.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed.',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/spec.json',
                                           'new_evidence': []},
                                          {'expert_id': 'unknown',
                                           'summary': 'Unknown perspective completed.',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/manifest.json',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_missing_artifact(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The package points to a missing artifact.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed.',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/spec.json',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed.',
                                           'artifact_path': 'missing/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_unknown_citation(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'An expert result cites an unregistered source.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/spec.json',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [99].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/test_workflow.py',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_malformed_roster(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The persisted roster is missing a role brief.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/spec.json',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/test_workflow.py',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst', 'role': 'systems analyst'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_accepts_appended_evidence(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The expert-result package merged one new source.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [4].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian_appended.md',
                                           'new_evidence': ['source-d — new historian claim']},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a',
                                             '[2] source-b',
                                             '[3] source-c',
                                             '[4] source-d — new historian claim']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], True)

    def test_expert_results_rejects_rewritten_prefix(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The merged registry rewrote a persisted evidence entry.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a-rewritten',
                                             '[2] source-b',
                                             '[3] source-c']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_id_gap(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The merged registry skipped a citation identifier.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [5].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian_appended.md',
                                           'new_evidence': ['source-d — new historian claim']},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a',
                                             '[2] source-b',
                                             '[3] source-c',
                                             '[5] source-d — new historian claim']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_duplicate_locator(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'The merge reintroduced a persisted locator under a new citation id.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [4].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian_appended.md',
                                           'new_evidence': ['source-a — duplicate locator']},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a',
                                             '[2] source-b',
                                             '[3] source-c',
                                             '[4] source-a — duplicate locator']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_report_verification_pass_enters_final_handoff(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'report_path': 'reports/draft.md',
 'report_summary': 'A grounded report.',
 'constraints': {'max_rounds': 8}}),
            current_step_id='verify_report',
            observation={'status': 'succeeded',
 'summary': 'The report passed quality and citation verification.',
 'structured_output': {'quality_verdict': 'pass',
                       'quality_findings': [],
                       'citation_coverage_summary': 'All citations resolve to the evidence '
                                                    'registry.',
                       'report_ready': True,
                       'verified_report_path': 'reports/draft.md'}},
            verifier_result={'passed': True, 'message': 'citation integrity passed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'finalize_collaborative_report')
        self.assertEqual(result.branch_kind, 'complete')

    def test_roundtable_rejects_dropped_merged_evidence(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'The moderator dropped a merged evidence entry.',
 'structured_output': {'last_turn_summary': 'The analyst added a grounded comparison.',
                       'conversation_transcript': ['prior turn', 'new analyst turn'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'knowledge_map_summary': 'supported map',
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 1,
                       'round_decision': 'continue',
                       'continue_roundtable': True,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': False}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'Historian perspective completed.',
                     'artifact_path': 'reports/experts/1/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Systems analyst perspective completed.',
                     'artifact_path': 'reports/experts/1/systems_analyst.md'}],
 'evidence_registry': ['[1] source-a',
                       '[2] source-b',
                       '[3] source-c',
                       '[4] source-d — new historian claim']},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_unused_over_budget(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'One expert returned more than three unused retrieved items.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md',
                                           'new_evidence': ['source-e — unused claim one',
                                                            'source-f — unused claim two',
                                                            'source-g — unused claim three',
                                                            'source-h — unused claim four']},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a',
                                             '[2] source-b',
                                             '[3] source-c',
                                             '[4] source-e — unused claim one',
                                             '[5] source-f — unused claim two',
                                             '[6] source-g — unused claim three',
                                             '[7] source-h — unused claim four']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_rejects_malformed_new_evidence(self):
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'A new_evidence item omitted the locator-claim separator.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md',
                                           'new_evidence': ['source-d new historian claim without '
                                                            'dash']},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a',
                                             '[2] source-b',
                                             '[3] source-c',
                                             '[4] source-d new historian claim without dash']}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
 'constraints': {'max_rounds': 8}},
        )
        self.assertIs(result['passed'], False)

    def test_expert_results_verifier_failed_goes_to_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'constraints': {'max_rounds': 8},
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}),
            current_step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'All expert results completed.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            verifier_result={'passed': False, 'message': 'expert-result merge contract failed', 'details': {}},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_expert_results_missing_verifier_fails_closed(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'constraints': {'max_rounds': 8},
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}),
            current_step_id='launch_expert_subagents',
            observation={'status': 'succeeded',
 'summary': 'All expert results completed.',
 'structured_output': {'expert_round_index': 1,
                       'expert_results': [{'expert_id': 'historian',
                                           'summary': 'Historian perspective completed with '
                                                      'evidence [1].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md',
                                           'new_evidence': []},
                                          {'expert_id': 'systems_analyst',
                                           'summary': 'Systems analyst perspective completed with '
                                                      'evidence [2].',
                                           'artifact_path': 'skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md',
                                           'new_evidence': []}],
                       'expert_results_complete': True,
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'repair')

    def test_expert_results_blocked_goes_to_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 0,
 'constraints': {'max_rounds': 8},
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']}),
            current_step_id='launch_expert_subagents',
            observation={'status': 'blocked',
 'summary': 'An expert artifact was unavailable.',
 'structured_output': {'blocked_reason': 'missing expert artifact',
                       'missing_expert_ids': ['historian']}},
            verifier_result={'passed': False, 'message': 'expert-result stage blocked', 'details': {}},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'repair')

    def test_repair_and_resume_returns_to_expert_results(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state({'return_stage_id': 'launch_expert_subagents'}),
            current_step_id='repair_and_resume',
            observation={'status': 'succeeded',
 'summary': 'Repair completed.',
 'structured_output': {'retry_reason': 'Retry is safe after the repair.',
                       'retry_notes': 'The missing expert artifact was restored.',
                       'repair_actions': ['Retry the expert-result stage.']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'launch_expert_subagents')
        self.assertEqual(result.branch_kind, 'continue')

    def test_roundtable_accepts_semantically_complete_report(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'The Moderator found every required topic semantically covered.',
 'structured_output': {'last_turn_summary': 'All required topics are grounded.',
                       'conversation_transcript': ['prior turn', 'coverage decision'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'coverage_assessment': [{'topic_id': 'history',
                                                'status': 'covered',
                                                'evidence_refs': ['[1]'],
                                                'open_gaps': [],
                                                'next_validation_metrics': []},
                                               {'topic_id': 'mechanism',
                                                'status': 'covered',
                                                'evidence_refs': ['[2]', '[3]'],
                                                'open_gaps': [],
                                                'next_validation_metrics': []}],
                       'coverage_decision_rationale': 'Both required topics have traceable '
                                                      'evidence and no unresolved gaps.',
                       'next_round_validation_plan': [],
                       'report_scope_status': 'complete',
                       'knowledge_map_summary': 'complete supported map',
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 2,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': True,
                       'ready_for_report': True}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 1,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3, 'coverage_threshold': 2},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'History complete.',
                     'artifact_path': 'reports/experts/2/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Mechanism complete.',
                     'artifact_path': 'reports/experts/2/systems_analyst.md'}],
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']},
        )
        self.assertIs(result['passed'], True)

    def test_roundtable_rejects_threshold_only_completion(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'The topic count met the threshold but one topic remains missing.',
 'structured_output': {'last_turn_summary': 'Mechanism evidence is still missing.',
                       'conversation_transcript': ['prior turn', 'coverage decision'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'coverage_assessment': [{'topic_id': 'history',
                                                'status': 'covered',
                                                'evidence_refs': ['[1]'],
                                                'open_gaps': [],
                                                'next_validation_metrics': []},
                                               {'topic_id': 'mechanism',
                                                'status': 'missing',
                                                'evidence_refs': [],
                                                'open_gaps': ['No causal evidence.'],
                                                'next_validation_metrics': ['Find two independent '
                                                                            'causal sources.']}],
                       'coverage_decision_rationale': 'The numeric threshold is met but semantic '
                                                      'coverage is not.',
                       'next_round_validation_plan': [],
                       'report_scope_status': 'complete',
                       'knowledge_map_summary': 'incomplete map',
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 2,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': True,
                       'ready_for_report': True}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 1,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3, 'coverage_threshold': 2},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'History complete.',
                     'artifact_path': 'reports/experts/2/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Mechanism incomplete.',
                     'artifact_path': 'reports/experts/2/systems_analyst.md'}],
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']},
        )
        self.assertIs(result['passed'], False)

    def test_roundtable_accepts_forced_partial_report_at_max_rounds(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'The round budget ended with an explicit partial handoff.',
 'structured_output': {'last_turn_summary': 'Mechanism evidence remains unresolved at the round '
                                            'limit.',
                       'conversation_transcript': ['prior turn', 'forced stop decision'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'coverage_assessment': [{'topic_id': 'history',
                                                'status': 'covered',
                                                'evidence_refs': ['[1]'],
                                                'open_gaps': [],
                                                'next_validation_metrics': []},
                                               {'topic_id': 'mechanism',
                                                'status': 'missing',
                                                'evidence_refs': [],
                                                'open_gaps': ['No causal evidence.'],
                                                'next_validation_metrics': ['Find two independent '
                                                                            'causal sources.']}],
                       'coverage_decision_rationale': 'The budget is exhausted, so unresolved work '
                                                      'must be handed off explicitly.',
                       'next_round_validation_plan': ['mechanism — Find two independent causal '
                                                      'sources.'],
                       'report_scope_status': 'partial',
                       'knowledge_map_summary': 'partial supported map',
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 3,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': True}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 2,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3, 'coverage_threshold': 2},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'History complete.',
                     'artifact_path': 'reports/experts/3/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Mechanism incomplete.',
                     'artifact_path': 'reports/experts/3/systems_analyst.md'}],
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']},
        )
        self.assertIs(result['passed'], True)

    def test_roundtable_rejects_complete_label_for_forced_stop(self):
        result = verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='autonomous_roundtable',
            observation={'status': 'succeeded',
 'summary': 'The round budget ended but the report was incorrectly labeled complete.',
 'structured_output': {'last_turn_summary': 'Mechanism evidence remains unresolved at the round '
                                            'limit.',
                       'conversation_transcript': ['prior turn', 'forced stop decision'],
                       'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c'],
                       'coverage_map': ['history', 'mechanism'],
                       'coverage_assessment': [{'topic_id': 'history',
                                                'status': 'covered',
                                                'evidence_refs': ['[1]'],
                                                'open_gaps': [],
                                                'next_validation_metrics': []},
                                               {'topic_id': 'mechanism',
                                                'status': 'missing',
                                                'evidence_refs': [],
                                                'open_gaps': ['No causal evidence.'],
                                                'next_validation_metrics': ['Find two independent '
                                                                            'causal sources.']}],
                       'coverage_decision_rationale': 'The budget is exhausted, but unresolved '
                                                      'work remains.',
                       'next_round_validation_plan': ['mechanism — Find two independent causal '
                                                      'sources.'],
                       'report_scope_status': 'complete',
                       'knowledge_map_summary': 'partial supported map',
                       'expert_roster': [{'id': 'historian',
                                          'role': 'historian',
                                          'brief': 'Trace origins and chronology.'},
                                         {'id': 'systems_analyst',
                                          'role': 'systems analyst',
                                          'brief': 'Trace mechanisms and trade-offs.'}],
                       'round_index': 3,
                       'round_decision': 'report',
                       'continue_roundtable': False,
                       'should_reorganize': False,
                       'coverage_sufficient': False,
                       'ready_for_report': True}},
            state={'expert_roster': [{'id': 'historian',
                    'role': 'historian',
                    'brief': 'Trace origins and chronology.'},
                   {'id': 'systems_analyst',
                    'role': 'systems analyst',
                    'brief': 'Trace mechanisms and trade-offs.'}],
 'round_index': 2,
 'conversation_transcript': ['prior turn'],
 'constraints': {'max_rounds': 3, 'coverage_threshold': 2},
 'expert_results_complete': True,
 'expert_results': [{'expert_id': 'historian',
                     'summary': 'History complete.',
                     'artifact_path': 'reports/experts/3/historian.md'},
                    {'expert_id': 'systems_analyst',
                     'summary': 'Mechanism incomplete.',
                     'artifact_path': 'reports/experts/3/systems_analyst.md'}],
 'evidence_registry': ['[1] source-a', '[2] source-b', '[3] source-c']},
        )
        self.assertIs(result['passed'], False)

    def test_generated_request_unblocking_input_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'warm_start_shared_space'
        state.repair_context = {'source_stage_id': 'request_unblocking_input'}
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {'blocking_reason': 'Approval was missing.', 'user_action_needed': 'Confirm the approval.', 'suggested_next_input': 'Approval confirmed.'}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'warm_start_shared_space')
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
        state.return_stage_id = 'warm_start_shared_space'
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
        state.return_stage_id = 'warm_start_shared_space'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {'retry_reason': 'Retry is safe after the repair.', 'retry_notes': 'The missing dependency was refreshed.', 'repair_actions': ['Retry the original stage.']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'warm_start_shared_space')
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
        self.assertEqual(result.step_id, 'finalize_collaborative_report')
        self.assertEqual(result.branch_kind, 'partial')
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
