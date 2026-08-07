import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


RUNTIME_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = RUNTIME_ROOT.parent
REPO_ROOT = SKILL_ROOT.parents[1]
for _lib_root in (REPO_ROOT / '.venv' / 'lib', SKILL_ROOT / '.venv' / 'lib', REPO_ROOT.parent / '.venv' / 'lib'):
    _site_packages = next(_lib_root.glob('python*/site-packages'), None)
    if _site_packages is not None and str(_site_packages) not in sys.path:
        sys.path.insert(0, str(_site_packages))
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from workflows.performance_optimization_cycle import graphbuilder_runtime, policy, state as workflow_state, verifiers


class PerformanceOptimizationCycleWorkflowGeneratedTests(unittest.TestCase):
    def test_artifact_journal_compacts_repeated_large_observations(self):
        state = self._make_state(None)
        for _ in range(100):
            workflow_state.record_observation(
                state,
                current_step_id="diagnose_performance",
                observation={
                    "status": "succeeded",
                    "summary": "large diagnostic output",
                    "structured_output": {"diagnostic": "x" * 100_000},
                },
                verifier_result={"passed": True, "message": "ok", "details": {}},
            )
        serialized = workflow_state.serialize_state(state)
        self.assertLess(len(json.dumps(serialized).encode("utf-8")), 1_000_000)
        self.assertLessEqual(len(serialized["artifacts_by_stage"]["diagnose_performance"]), 32)

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

    def test_performance_diagnosis_feeds_brainstorming(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='diagnose_performance',
            observation={'status': 'succeeded',
 'summary': 'Baseline and bottleneck identified.',
 'structured_output': {'baseline_metrics': 'P99 2.0s; throughput 40 rps',
                       'bottleneck_summary': 'Database fan-out dominates P99 latency.',
                       'performance_report_path': '.tmp/performance-nex/diagnosis.md',
                       'ready_for_brainstorm': True}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'brainstorm_optimization')
        self.assertEqual(result.branch_kind, 'continue')

    def test_starts_with_brainstorming(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='brainstorm_optimization',
            observation={'status': 'succeeded',
 'summary': 'Hypothesis ready.',
 'structured_output': {'optimization_hypotheses': ['reduce dependency pressure'],
                       'success_criteria': 'fewer cycles',
                       'brainstorm_artifact_path': '.tmp/brainstorming-nex/brainstorm_output.md',
                       'ready_for_research': True}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'research_optimization')
        self.assertEqual(result.branch_kind, 'continue')

    def test_submission_test_failure_routes_to_repair(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='implement_optimization',
            observation={'status': 'succeeded',
 'summary': 'Submission test failed.',
 'structured_output': {'implementation_summary': 'candidate',
                       'planned_change_summary': 'reduce dependency pressure',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'changed_paths': ['perf_takehome.py'],
                       'submission_test_output': 'failed',
                       'submission_tests_passed': False,
                       'ready_for_review': False}},
            verifier_result={'passed': False, 'messages': ['python tests/submission_tests.py must pass before review']},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_knowledge_base_continues_to_performance_diagnosis(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='update_optimization_knowledge_base',
            observation={'status': 'succeeded',
 'summary': 'KB updated; continue.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded result.',
                       'knowledge_base_artifacts': ['knowledge-base/topics/applied-optimization-log.md'],
                       'continue_optimization': True}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'diagnose_performance')
        self.assertEqual(result.branch_kind, 'continue')

    def test_verified_knowledge_base_update_counts_a_completed_cycle(self):
        state = self._make_state(None)
        observation = {
            'status': 'succeeded',
            'summary': 'KB update verified.',
            'structured_output': {
                'knowledge_base_update_summary': 'Recorded result.',
                'knowledge_base_artifacts': ['knowledge-base/topics/applied-optimization-log.md'],
                'continue_optimization': True,
            },
        }
        workflow_state.record_observation(
            state,
            current_step_id='update_optimization_knowledge_base',
            observation=observation,
            verifier_result={'passed': True},
        )
        self.assertEqual(state.completed_optimization_cycles, 1)

        workflow_state.record_observation(
            state,
            current_step_id='update_optimization_knowledge_base',
            observation=observation,
            verifier_result=None,
        )
        self.assertEqual(state.completed_optimization_cycles, 1)

    def test_performance_budget_routes_to_repair(self):
        state = self._make_state({
            'constraints': {'max_steps': 1},
            'attempt_counts': {'diagnose_performance': 1},
        })
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id='diagnose_performance',
            observation={'status': 'succeeded', 'summary': 'Budget reached.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'repair')

    def test_deserialize_rejects_unknown_return_stage(self):
        with self.assertRaises(ValueError):
            self._make_state({'return_stage_id': 'not_a_declared_stage'})
        with self.assertRaises(ValueError):
            self._make_state({'current_stage_id': ''})

    def test_deserialize_rejects_malformed_persisted_collections(self):
        with self.assertRaises(ValueError):
            self._make_state({'attempt_counts': {'diagnose_performance': True}})
        with self.assertRaises(ValueError):
            self._make_state({'completed_stages': ['unknown_stage']})
        with self.assertRaises(ValueError):
            self._make_state({'task_input': []})

    def test_repair_policy_does_not_coerce_malformed_attempt_count(self):
        state = self._make_state(None)
        state.attempt_counts = {'repair_and_resume': '3'}
        result = policy.choose_next_node(
            state=workflow_state.serialize_state(state),
            current_step_id='repair_and_resume',
            observation={'status': 'blocked', 'summary': 'Repair remains blocked.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.next_node, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_research_directly_feeds_implementation_without_plan_stage(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='research_optimization',
            observation={'status': 'succeeded',
 'summary': 'Research produced an evidence-backed brief.',
 'structured_output': {'research_brief_path': '.tmp/research-nex/brief.md',
                       'evidence_summary': 'Measured improvement opportunity.',
                       'open_risks': [],
                       'planned_change_summary': 'Reduce dependency pressure in the hot path.',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'ready_for_implementation': True}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'implement_optimization')
        self.assertEqual(result.branch_kind, 'continue')

    def test_research_action_line_renders_exactly(self):
        prompt = graphbuilder_runtime.load_prompt_body(
            'research_optimization',
            {
                'optimization_hypotheses': '["reduce dependency pressure"]',
                'goal': 'reduce latency',
                'repo_root': '/repo',
                'success_criteria': 'lower P99',
                'brainstorm_artifact_path': '.tmp/brainstorm.md',
            },
        )
        self.assertEqual(
            prompt.splitlines()[0],
            '/research-nex investigate ["reduce dependency pressure"] for reduce latency in /repo',
        )

    def test_research_promotes_implementation_handoff_into_prompt_context(self):
        state = self._make_state(None)
        workflow_state.record_observation(
            state,
            current_step_id='research_optimization',
            observation={'status': 'succeeded',
                         'summary': 'Research produced an implementation-ready handoff.',
                         'structured_output': {'research_brief_path': '.tmp/research-nex/brief.md',
                                               'evidence_summary': 'Measured improvement opportunity.',
                                               'open_risks': [],
                                               'planned_change_summary': 'Reduce dependency pressure in the hot path.',
                                               'verification_plan': ['python tests/submission_tests.py'],
                                               'ready_for_implementation': True}},
            verifier_result={'passed': True},
        )
        prompt = graphbuilder_runtime.load_prompt_body(
            'implement_optimization',
            graphbuilder_runtime.build_template_context(
                step_id='implement_optimization',
                run_state=SimpleNamespace(graph_state=workflow_state.serialize_state(state)),
            ),
        )
        self.assertIn('Reduce dependency pressure in the hot path.', prompt)
        self.assertIn('python tests/submission_tests.py', prompt)

    def test_final_prompt_marks_max_steps_handoff_as_partial(self):
        state = self._make_state(None)
        prompt = graphbuilder_runtime.load_prompt_body(
            'finalize_optimization_cycle',
            graphbuilder_runtime.build_template_context(
                step_id='finalize_optimization_cycle',
                run_state=SimpleNamespace(
                    graph_state=workflow_state.serialize_state(state),
                    terminal_reason='max_steps_exceeded',
                    artifacts_degraded=False,
                ),
            ),
        )
        self.assertIn('true', prompt)
        self.assertIn('max_steps_exceeded', prompt)

    def test_flowchart_does_not_claim_a_handled_recovery_self_loop(self):
        flowchart = (Path(__file__).resolve().parents[1] / 'references' / 'flowchart.md').read_text(
            encoding='utf-8'
        )
        self.assertNotIn(
            'capture_blocked_cycle_knowledge -.->|partial / failed / verifier| capture_blocked_cycle_knowledge',
            flowchart,
        )

    def test_research_rejects_missing_brief_path(self):
        result = verifiers.verify_research_optimization(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='research_optimization',
            observation={'status': 'succeeded',
 'summary': 'Research completed without a saved brief.',
 'structured_output': {'research_brief_path': '.tmp/research-nex/missing.md',
                       'evidence_summary': 'Measured improvement opportunity.',
                       'open_risks': [],
                       'planned_change_summary': 'Reduce dependency pressure in the hot path.',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_research_rejects_unrelated_json_artifact(self):
        result = verifiers.verify_research_optimization(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='research_optimization',
            observation={'status': 'succeeded',
 'summary': 'Research returned an unrelated existing file.',
 'structured_output': {'research_brief_path': 'skills/durable-workflow-runtime/workflow-binding.json',
                       'evidence_summary': 'Measured improvement opportunity.',
                       'open_risks': [],
                       'planned_change_summary': 'Reduce dependency pressure in the hot path.',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'ready_for_implementation': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_research_accepts_non_empty_markdown_brief(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / 'brief.md'
            brief_path.write_text('# Research brief\nMeasured opportunity.\n', encoding='utf-8')
            result = verifiers.verify_research_optimization(
                repo_root=tmpdir,
                run_id="generated-test-run",
                step_id='research_optimization',
                observation={'status': 'succeeded',
 'summary': 'Research produced an implementation-ready handoff.',
 'structured_output': {'research_brief_path': 'brief.md',
                       'evidence_summary': 'Measured improvement opportunity.',
                       'open_risks': [],
                       'planned_change_summary': 'Reduce dependency pressure in the hot path.',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'ready_for_implementation': True}},
                state={},
            )
        self.assertIs(result['passed'], True)

    def test_research_rejects_absolute_and_traversal_brief_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / 'brief.md'
            brief_path.write_text('# Research brief\nMeasured opportunity.\n', encoding='utf-8')
            for path_value in (str(brief_path), '../brief.md'):
                with self.subTest(path_value=path_value):
                    result = verifiers.verify_research_optimization(
                        repo_root=tmpdir,
                        run_id='generated-test-run',
                        step_id='research_optimization',
                        observation={'status': 'succeeded',
 'summary': 'Research returned an unsafe path.',
 'structured_output': {'research_brief_path': path_value,
                       'evidence_summary': 'Measured improvement opportunity.',
                       'open_risks': [],
                       'planned_change_summary': 'Reduce dependency pressure in the hot path.',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'ready_for_implementation': True}},
                        state={},
                    )
                    self.assertIs(result['passed'], False)

    def test_research_rejects_oversized_markdown_brief(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / 'brief.md'
            brief_path.write_bytes(b'# Research brief\n' + b'x' * (512 * 1024))
            result = verifiers.verify_research_optimization(
                repo_root=tmpdir,
                run_id='generated-test-run',
                step_id='research_optimization',
                observation={'status': 'succeeded',
 'summary': 'Research returned an oversized brief.',
 'structured_output': {'research_brief_path': 'brief.md',
                       'evidence_summary': 'Measured opportunity.',
                       'open_risks': [],
                       'planned_change_summary': 'Reduce dependency pressure in the hot path.',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'ready_for_implementation': True}},
                state={},
            )
        self.assertIs(result['passed'], False)

    def test_blocked_main_stage_records_knowledge_without_requesting_user_input(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='implement_optimization',
            observation={'status': 'blocked',
 'summary': 'Required benchmark environment is unavailable.',
 'structured_output': {'blocked_reason': 'benchmark environment unavailable',
                       'missing_inputs': ['benchmark environment']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'capture_blocked_cycle_knowledge')
        self.assertEqual(result.branch_kind, 'continue')

    def test_blocked_cycle_knowledge_capture_starts_fresh_diagnosis(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='capture_blocked_cycle_knowledge',
            observation={'status': 'succeeded',
 'summary': 'Recorded blocked benchmark environment as a next-cycle constraint.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded the blocker and a next-cycle '
                                                        'lead.',
                       'knowledge_base_artifacts': ['knowledge-base/topics/applied-optimization-log.md'],
                       'next_cycle_lead': 'Use an available local benchmark to re-establish the '
                                          'baseline.'}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'diagnose_performance')
        self.assertEqual(result.branch_kind, 'continue')

    def test_blocked_cycle_knowledge_capture_never_requests_user_input(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='capture_blocked_cycle_knowledge',
            observation={'status': 'blocked',
 'summary': 'Knowledge base is temporarily unavailable.',
 'structured_output': {'blocked_reason': 'knowledge base unavailable',
                       'missing_inputs': ['knowledge base access']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'diagnose_performance')
        self.assertEqual(result.branch_kind, 'continue')

    def test_performance_diagnosis_rejects_missing_report_path(self):
        result = verifiers.verify_diagnose_performance(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='diagnose_performance',
            observation={'status': 'succeeded',
 'summary': 'Diagnosis completed.',
 'structured_output': {'baseline_metrics': 'P99 2.0s; throughput 40 rps',
                       'bottleneck_summary': 'Database fan-out dominates P99 latency.',
                       'performance_report_path': '.tmp/performance-nex/missing.md',
                       'ready_for_brainstorm': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_diagnosis_rejects_external_report_path(self):
        result = verifiers.verify_diagnose_performance(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='diagnose_performance',
            observation={'status': 'succeeded',
 'summary': 'Diagnosis returned an external path.',
 'structured_output': {'baseline_metrics': 'P99 2.0s',
                       'bottleneck_summary': 'Database fan-out dominates.',
                       'performance_report_path': '/etc/hosts',
                       'ready_for_brainstorm': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_implementation_rejects_changed_tests_path(self):
        result = verifiers.verify_implement_optimization(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='implement_optimization',
            observation={'status': 'succeeded',
 'summary': 'Claimed candidate completed.',
 'structured_output': {'implementation_summary': 'candidate',
                       'planned_change_summary': 'reduce dependency pressure',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'changed_paths': ['tests/submission_tests.py'],
                       'submission_test_command': 'python tests/submission_tests.py',
                       'submission_test_output': 'passed',
                       'submission_test_exit_code': 0,
                       'submission_tests_passed': True,
                       'ready_for_review': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_implementation_requires_submission_tests(self):
        result = verifiers.verify_implement_optimization(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='implement_optimization',
            observation={'status': 'succeeded',
 'summary': 'Candidate built.',
 'structured_output': {'implementation_summary': 'candidate',
                       'changed_paths': ['perf_takehome.py'],
                       'submission_test_output': 'not run',
                       'submission_tests_passed': False,
                       'ready_for_review': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_implementation_rejects_non_integer_or_nested_n_cores(self):
        for assignment in ('N_CORES = True\n', 'N_CORES = 1.0\n', 'def configure():\n    N_CORES = 1\n'):
            with self.subTest(assignment=assignment), tempfile.TemporaryDirectory() as tmpdir:
                (Path(tmpdir) / 'problem.py').write_text(assignment, encoding='utf-8')

                def fake_run(command, **kwargs):
                    if command[1:3] == ['diff', '--quiet']:
                        return SimpleNamespace(returncode=0, stdout='', stderr='')
                    if command[1:3] == ['diff', '--name-only']:
                        return SimpleNamespace(returncode=0, stdout='perf_takehome.py\n', stderr='')
                    return SimpleNamespace(returncode=0, stdout='submission passed\n', stderr='')

                with patch.object(verifiers.subprocess, 'run', side_effect=fake_run):
                    result = verifiers.verify_implement_optimization(
                        repo_root=tmpdir,
                        run_id='generated-test-run',
                        step_id='implement_optimization',
                        observation={'status': 'succeeded',
 'summary': 'Candidate built.',
 'structured_output': {'implementation_summary': 'candidate',
                       'planned_change_summary': 'reduce dependency pressure',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'changed_paths': ['perf_takehome.py'],
                       'submission_test_command': 'python tests/submission_tests.py',
                       'submission_test_output': 'submission passed',
                       'submission_test_exit_code': 0,
                       'submission_tests_passed': True,
                       'ready_for_review': True}},
                        state={},
                    )
                self.assertIs(result['passed'], False)

    def test_implementation_requires_all_declared_changed_paths_in_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / 'problem.py').write_text('N_CORES = 1\n', encoding='utf-8')

            def fake_run(command, **kwargs):
                if command[1:3] == ['diff', '--quiet']:
                    return SimpleNamespace(returncode=0, stdout='', stderr='')
                if command[1:3] == ['diff', '--name-only']:
                    return SimpleNamespace(returncode=0, stdout='perf_takehome.py\n', stderr='')
                return SimpleNamespace(returncode=0, stdout='submission passed\n', stderr='')

            with patch.object(verifiers.subprocess, 'run', side_effect=fake_run):
                result = verifiers.verify_implement_optimization(
                    repo_root=tmpdir,
                    run_id='generated-test-run',
                    step_id='implement_optimization',
                    observation={'status': 'succeeded',
 'summary': 'Candidate built.',
 'structured_output': {'implementation_summary': 'candidate',
                       'planned_change_summary': 'reduce dependency pressure',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'changed_paths': ['perf_takehome.py', 'missing.py'],
                       'submission_test_command': 'python tests/submission_tests.py',
                       'submission_test_output': 'submission passed',
                       'submission_test_exit_code': 0,
                       'submission_tests_passed': True,
                       'ready_for_review': True}},
                    state={},
                )
        self.assertIs(result['passed'], False)

    def test_implementation_rejects_undeclared_changed_paths_in_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / 'problem.py').write_text('N_CORES = 1\n', encoding='utf-8')

            def fake_run(command, **kwargs):
                if command[1:3] == ['diff', '--quiet']:
                    return SimpleNamespace(returncode=0, stdout='', stderr='')
                if command[1:3] == ['diff', '--name-only']:
                    return SimpleNamespace(returncode=0, stdout='perf_takehome.py\nextra.py\n', stderr='')
                return SimpleNamespace(returncode=0, stdout='submission passed\n', stderr='')

            with patch.object(verifiers.subprocess, 'run', side_effect=fake_run):
                result = verifiers.verify_implement_optimization(
                    repo_root=tmpdir,
                    run_id='generated-test-run',
                    step_id='implement_optimization',
                    observation={'status': 'succeeded',
 'summary': 'Candidate built.',
 'structured_output': {'implementation_summary': 'candidate',
                       'planned_change_summary': 'reduce dependency pressure',
                       'verification_plan': ['python tests/submission_tests.py'],
                       'changed_paths': ['perf_takehome.py'],
                       'submission_test_command': 'python tests/submission_tests.py',
                       'submission_test_output': 'submission passed',
                       'submission_test_exit_code': 0,
                       'submission_tests_passed': True,
                       'ready_for_review': True}},
                    state={},
                )
        self.assertIs(result['passed'], False)

    def test_failed_verifier_does_not_promote_performance_state(self):
        state = self._make_state(None)
        workflow_state.record_observation(
            state,
            current_step_id='diagnose_performance',
            observation={'status': 'succeeded',
                         'summary': 'Diagnosis was not verified.',
                         'structured_output': {'baseline_metrics': 'P99 2.0s',
                                               'bottleneck_summary': 'unverified',
                                               'performance_report_path': 'report.md',
                                               'ready_for_brainstorm': True}},
            verifier_result={'passed': False},
        )
        self.assertIsNone(state.baseline_metrics)
        self.assertEqual(state.artifacts_by_stage, {})

    def test_review_rejects_unresolved_high_finding(self):
        result = verifiers.verify_review_optimization(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='review_optimization',
            observation={'status': 'succeeded',
 'summary': 'Review completed.',
 'structured_output': {'review_summary': 'Candidate reviewed.',
                       'review_findings': ['High: regression remains in the hot path.'],
                       'ready_for_knowledge_base': True}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_knowledge_base_rejects_missing_artifact(self):
        result = verifiers.verify_update_optimization_knowledge_base(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_optimization_knowledge_base',
            observation={'status': 'succeeded',
 'summary': 'Knowledge base update claimed.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded result.',
                       'knowledge_base_artifacts': ['knowledge-base/missing.md'],
                       'continue_optimization': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_knowledge_base_rejects_existing_non_knowledge_base_artifact(self):
        result = verifiers.verify_update_optimization_knowledge_base(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='update_optimization_knowledge_base',
            observation={'status': 'succeeded',
 'summary': 'Knowledge base update claimed.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded result.',
                       'knowledge_base_artifacts': ['skills/durable-workflow-runtime/workflow-binding.json'],
                       'continue_optimization': False}},
            state={},
        )
        self.assertIs(result['passed'], False)

    def test_knowledge_base_accepts_existing_markdown_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / 'knowledge-base' / 'topics' / 'optimization.md'
            artifact.parent.mkdir(parents=True)
            artifact.write_text('# Optimization\nMeasured evidence.\n', encoding='utf-8')
            result = verifiers.verify_update_optimization_knowledge_base(
                repo_root=tmpdir,
                run_id='generated-test-run',
                step_id='update_optimization_knowledge_base',
                observation={'status': 'succeeded',
 'summary': 'Knowledge base update recorded.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded result.',
                       'knowledge_base_artifacts': ['knowledge-base/topics/optimization.md'],
                       'continue_optimization': False}},
                state={},
            )
        self.assertIs(result['passed'], True)

    def test_knowledge_base_transition_requires_passing_verifier(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='update_optimization_knowledge_base',
            observation={'status': 'succeeded',
 'summary': 'KB update claimed.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded result.',
                       'knowledge_base_artifacts': ['knowledge-base/topics/applied-optimization-log.md'],
                       'continue_optimization': False}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_knowledge_base_transition_rejects_malformed_verifier(self):
        result = graphbuilder_runtime.run_transition_preview(
            state=self._make_state(None),
            current_step_id='update_optimization_knowledge_base',
            observation={'status': 'succeeded',
 'summary': 'KB update claimed.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded result.',
                       'knowledge_base_artifacts': ['knowledge-base/topics/applied-optimization-log.md'],
                       'continue_optimization': False}},
            verifier_result={},
        )
        self.assertEqual(result.step_id, 'repair_and_resume')
        self.assertEqual(result.branch_kind, 'retry')

    def test_cycle_limit_routes_to_finalization(self):
        state = self._make_state({'constraints': {'max_cycles': 1},
                                  'completed_optimization_cycles': 1})
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id='update_optimization_knowledge_base',
            observation={'status': 'succeeded',
 'summary': 'KB updated; continue was requested.',
 'structured_output': {'knowledge_base_update_summary': 'Recorded result.',
                       'knowledge_base_artifacts': ['knowledge-base/topics/applied-optimization-log.md'],
                       'continue_optimization': True}},
            verifier_result={'passed': True},
        )
        self.assertEqual(result.step_id, 'finalize_optimization_cycle')
        self.assertEqual(result.branch_kind, 'complete')

    def test_generated_request_unblocking_input_resumes_to_return_stage(self):
        state = self._make_state(None)
        state.return_stage_id = 'diagnose_performance'
        state.repair_context = {'source_stage_id': 'request_unblocking_input'}
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="request_unblocking_input",
            observation={'status': 'succeeded', 'summary': 'Missing input supplied.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'diagnose_performance')
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
        state.return_stage_id = 'diagnose_performance'
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
        state.return_stage_id = 'diagnose_performance'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'succeeded', 'summary': 'Repair completed.', 'structured_output': {}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'diagnose_performance')
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
        state.return_stage_id = 'update_optimization_knowledge_base'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "retry")
        self.assertEqual(state.return_stage_id, 'update_optimization_knowledge_base')

    def test_generated_repair_and_resume_blocked_after_threshold_requests_unblocking(self):
        state = self._make_state({'attempt_counts': {'repair_and_resume': 2}})
        state.return_stage_id = 'update_optimization_knowledge_base'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(state.return_stage_id, 'update_optimization_knowledge_base')

    def test_generated_blocked_repair_context_preserves_host_visible_summary(self):
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        response = engine.start('performance_optimization_cycle', {
            "task_input": {"goal": "generated workflow regression"},
            "context": {"repo_root": str(REPO_ROOT)},
            "constraints": {"max_steps": 5},
        })
        run_id = response['run_id']
        response = engine.resume(run_id, {
            'run_id': run_id,
            'step_id': 'diagnose_performance',
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
