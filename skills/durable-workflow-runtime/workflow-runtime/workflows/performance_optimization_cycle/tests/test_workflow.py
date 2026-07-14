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

from workflows.performance_optimization_cycle import graphbuilder_runtime, state as workflow_state, verifiers


class PerformanceOptimizationCycleWorkflowGeneratedTests(unittest.TestCase):
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
            verifier_result=None,
        )
        self.assertEqual(result.step_id, 'diagnose_performance')
        self.assertEqual(result.branch_kind, 'continue')

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
            verifier_result=None,
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

    def test_implementation_rejects_changed_tests_path(self):
        result = verifiers.verify_implement_optimization(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id='implement_optimization',
            observation={'status': 'succeeded',
 'summary': 'Claimed candidate completed.',
 'structured_output': {'implementation_summary': 'candidate',
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

    def test_generated_repair_and_resume_blocked_records_knowledge_without_requesting_user_input(self):
        state = self._make_state(None)
        state.return_stage_id = 'update_optimization_knowledge_base'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "capture_blocked_cycle_knowledge")
        self.assertEqual(result.branch_kind, "continue")
        self.assertEqual(state.return_stage_id, 'update_optimization_knowledge_base')

    def test_generated_repair_and_resume_blocked_after_prior_attempts_still_records_knowledge(self):
        state = self._make_state({'attempt_counts': {'repair_and_resume': 2}})
        state.return_stage_id = 'update_optimization_knowledge_base'
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={'status': 'blocked', 'summary': 'Repair still needs external input.', 'structured_output': {'missing_inputs': ['approval']}},
            verifier_result=None,
        )
        self.assertEqual(result.step_id, "capture_blocked_cycle_knowledge")
        self.assertEqual(result.branch_kind, "continue")
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
