import copy
import sys
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = RUNTIME_ROOT.parent
REPO_ROOT = SKILL_ROOT.parents[1]
for _lib_root in (
    REPO_ROOT / ".venv" / "lib",
    SKILL_ROOT / ".venv" / "lib",
    REPO_ROOT.parent / ".venv" / "lib",
):
    _site_packages = next(_lib_root.glob("python*/site-packages"), None)
    if _site_packages is not None and str(_site_packages) not in sys.path:
        sys.path.insert(0, str(_site_packages))
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from workflows.co_storm_autonomous_research import verifiers


ROSTER = [
    {"id": "historian", "role": "historian", "brief": "Trace history."},
    {"id": "systems_analyst", "role": "systems analyst", "brief": "Trace mechanisms."},
]
REGISTRY = ["[1] source-a", "[2] source-b", "[3] source-c"]
FIXTURE_ROOT = (
    "skills/durable-workflow-runtime/workflow-runtime/workflows/"
    "co_storm_autonomous_research/tests/fixtures"
)


class SemanticCoverageReviewTests(unittest.TestCase):
    def _roundtable_state(self):
        return {
            "expert_roster": copy.deepcopy(ROSTER),
            "round_index": 0,
            "conversation_transcript": ["prior turn"],
            "constraints": {"max_rounds": 3, "coverage_threshold": 2},
            "coverage_map": ["history", "mechanism"],
            "expert_results_complete": True,
            "expert_results": [
                {"expert_id": "historian", "summary": "done", "artifact_path": "history.md"},
                {"expert_id": "systems_analyst", "summary": "done", "artifact_path": "mechanism.md"},
            ],
            "evidence_registry": list(REGISTRY),
        }

    def _bounded_gap_continue_output(self):
        return {
            "last_turn_summary": "The mechanism gap remains material.",
            "conversation_transcript": ["prior turn", "bounded-gap decision"],
            "evidence_registry": list(REGISTRY),
            "coverage_map": ["history", "mechanism"],
            "coverage_assessment": [
                {
                    "topic_id": "history",
                    "status": "covered",
                    "evidence_refs": ["[1]"],
                    "open_gaps": [],
                    "next_validation_metrics": [],
                },
                {
                    "topic_id": "mechanism",
                    "status": "bounded_gap",
                    "evidence_refs": ["[2]"],
                    "open_gaps": ["Causal direction remains uncertain."],
                    "next_validation_metrics": ["Find two independent causal sources."],
                },
            ],
            "coverage_decision_rationale": "The Moderator judges the bounded gap material.",
            "next_round_validation_plan": [
                "mechanism — Find two independent causal sources."
            ],
            "report_scope_status": "in_progress",
            "knowledge_map_summary": "supported map with a bounded mechanism gap",
            "expert_roster": copy.deepcopy(ROSTER),
            "round_index": 1,
            "round_decision": "continue",
            "continue_roundtable": True,
            "should_reorganize": False,
            "coverage_sufficient": False,
            "ready_for_report": False,
        }

    def _verify_roundtable(self, output, state=None):
        return verifiers.verify_autonomous_roundtable(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="autonomous_roundtable",
            observation={
                "status": "succeeded",
                "summary": "Moderator completed a semantic decision.",
                "structured_output": output,
            },
            state=state or self._roundtable_state(),
        )

    def test_moderator_can_continue_for_material_bounded_gap(self):
        result = self._verify_roundtable(self._bounded_gap_continue_output())
        self.assertIs(result["passed"], True, result["message"])

    def test_covered_topic_cannot_retain_gap_or_metric(self):
        output = self._bounded_gap_continue_output()
        output["coverage_assessment"][1]["status"] = "covered"
        output["coverage_sufficient"] = True
        output["next_round_validation_plan"] = []
        output["round_decision"] = "report"
        output["continue_roundtable"] = False
        output["ready_for_report"] = True
        output["report_scope_status"] = "complete"
        result = self._verify_roundtable(output)
        self.assertIs(result["passed"], False)
        self.assertIn("must not retain open gaps", result["message"])

    def test_first_round_cannot_replace_warm_start_topics(self):
        output = self._bounded_gap_continue_output()
        output["coverage_assessment"][0]["topic_id"] = "unrelated-a"
        output["coverage_assessment"][1]["topic_id"] = "unrelated-b"
        output["next_round_validation_plan"] = [
            "unrelated-b — Find two independent causal sources."
        ]
        result = self._verify_roundtable(output)
        self.assertIs(result["passed"], False)
        self.assertIn("dropped required topic ids", result["message"])

    def test_validation_plan_must_match_unresolved_topic_metrics(self):
        output = self._bounded_gap_continue_output()
        output["next_round_validation_plan"] = ["mechanism — Buy milk."]
        result = self._verify_roundtable(output)
        self.assertIs(result["passed"], False)
        self.assertIn("must exactly match", result["message"])

    def test_coverage_assessment_over_durable_limit_is_rejected(self):
        state = self._roundtable_state()
        topic_ids = [f"topic-{index}" for index in range(129)]
        state["coverage_map"] = topic_ids
        output = self._bounded_gap_continue_output()
        output["coverage_map"] = topic_ids
        output["coverage_assessment"] = [
            {
                "topic_id": topic_id,
                "status": "covered",
                "evidence_refs": ["[1]"],
                "open_gaps": [],
                "next_validation_metrics": [],
            }
            for topic_id in topic_ids
        ]
        output["coverage_sufficient"] = True
        output["next_round_validation_plan"] = []
        output["report_scope_status"] = "complete"
        output["round_decision"] = "report"
        output["continue_roundtable"] = False
        output["ready_for_report"] = True
        result = self._verify_roundtable(output, state)
        self.assertIs(result["passed"], False)
        self.assertIn("exceeds durable state limits", result["message"])

    def test_reorganization_cannot_rewrite_or_append_evidence(self):
        result = verifiers.verify_reorganize_knowledge_space(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="reorganize_knowledge_space",
            observation={
                "status": "succeeded",
                "summary": "Reorganization attempted to rewrite evidence.",
                "structured_output": {
                    "knowledge_map_summary": "reorganized map",
                    "coverage_map": ["history", "mechanism"],
                    "evidence_registry": [
                        "[1] rewritten-source",
                        "[2] source-b",
                        "[3] source-c",
                        "[99] injected-source",
                    ],
                    "reorganization_summary": "Reorganized topics.",
                    "reorganization_count": 1,
                    "reorganized": True,
                },
            },
            state={
                "constraints": {"max_reorganizations": 2},
                "evidence_registry": list(REGISTRY),
            },
        )
        self.assertIs(result["passed"], False)
        self.assertIn("preserve evidence_registry exactly", result["message"])

    def _report_output(self, path):
        return {
            "quality_verdict": "pass",
            "quality_findings": [],
            "citation_coverage_summary": "All citations resolve.",
            "report_ready": True,
            "verified_report_path": path,
        }

    def _complete_report_state(self):
        path = f"{FIXTURE_ROOT}/complete_report.md"
        return {
            "report_path": path,
            "report_summary": "A complete grounded report.",
            "evidence_registry": list(REGISTRY),
            "report_scope_status": "complete",
            "coverage_sufficient": True,
            "next_round_validation_plan": [],
            "coverage_assessment": [
                {"topic_id": "history", "status": "covered"},
                {"topic_id": "mechanism", "status": "covered"},
            ],
        }

    def _partial_report_state(self, report_name="partial_report.md"):
        path = f"{FIXTURE_ROOT}/{report_name}"
        return {
            "report_path": path,
            "report_summary": "A validated partial report.",
            "evidence_registry": list(REGISTRY),
            "report_scope_status": "partial",
            "coverage_sufficient": False,
            "next_round_validation_plan": [
                "mechanism — Find two independent causal sources."
            ],
            "coverage_assessment": [
                {"topic_id": "history", "status": "covered"},
                {
                    "topic_id": "mechanism",
                    "status": "missing",
                    "open_gaps": ["No causal evidence."],
                    "next_validation_metrics": ["Find two independent causal sources."],
                },
            ],
        }

    def _verify_report(self, state):
        return verifiers.verify_verify_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="verify_report",
            observation={
                "status": "succeeded",
                "summary": "Report verification completed.",
                "structured_output": self._report_output(state["report_path"]),
            },
            state=state,
        )

    def test_complete_report_scope_gate_accepts_consistent_report(self):
        result = self._verify_report(self._complete_report_state())
        self.assertIs(result["passed"], True, result["message"])

    def test_partial_report_scope_gate_accepts_full_disclosure(self):
        result = self._verify_report(self._partial_report_state())
        self.assertIs(result["passed"], True, result["message"])

    def test_partial_report_scope_gate_rejects_missing_disclosure(self):
        state = self._partial_report_state("complete_report.md")
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("Report scope: partial", result["message"])

    def test_partial_report_scope_gate_rejects_hidden_html_comment_disclosure(self):
        state = self._partial_report_state("hidden_partial_report.md")
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("numeric inline citation", result["message"])

    def test_partial_report_scope_gate_rejects_case_changed_marker(self):
        state = self._partial_report_state("case_changed_partial_report.md")
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("exact `Report scope: partial`", result["message"])

    def test_partial_report_scope_gate_rejects_one_omitted_metric(self):
        state = self._partial_report_state("partial_report_missing_metric.md")
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("Find two independent causal sources.", result["message"])

    def test_complete_report_scope_gate_rejects_insufficient_coverage(self):
        state = self._complete_report_state()
        state["coverage_sufficient"] = False
        state["next_round_validation_plan"] = ["mechanism — Find more evidence."]
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("requires coverage_sufficient=true", result["message"])

    def test_failed_verify_report_persists_fail_closed_audit_fields(self):
        from workflows.co_storm_autonomous_research import state as workflow_state

        path = f"{FIXTURE_ROOT}/number_only_report.md"
        persisted = self._complete_report_state()
        persisted["report_path"] = path
        observation = {
            "status": "succeeded",
            "summary": "LLM claimed the number-only report passed.",
            "structured_output": {
                "quality_verdict": "pass",
                "quality_findings": ["Minor duplication"],
                "citation_coverage_summary": "Numeric markers exist.",
                "report_ready": True,
                "verified_report_path": path,
            },
        }
        result = verifiers.verify_verify_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="verify_report",
            observation=observation,
            state=persisted,
        )
        self.assertIs(result["passed"], False)
        workflow = workflow_state.make_initial_state(
            {"task_input": {"goal": "persist failed audit"}, "context": {}, "constraints": {}}
        )
        workflow_state.record_observation(
            workflow,
            current_step_id="verify_report",
            observation=observation,
            verifier_result=result,
        )
        self.assertEqual(workflow.quality_verdict, "repair")
        self.assertIs(workflow.report_ready, False)
        self.assertIn("Minor duplication", workflow.quality_findings)
        self.assertTrue(
            any("in-place source locator" in str(item) for item in workflow.quality_findings)
        )

    def test_failed_synthesize_report_persists_report_path(self):
        from workflows.co_storm_autonomous_research import state as workflow_state

        path = f"{FIXTURE_ROOT}/number_only_report.md"
        observation = {
            "status": "succeeded",
            "summary": "Number-only report.",
            "structured_output": {
                "outline": "History and mechanism",
                "report_path": path,
                "report_summary": "A complete grounded report.",
                "report_sections": ["History", "Mechanism"],
                "report_ready_for_verification": True,
            },
        }
        result = verifiers.verify_synthesize_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="synthesize_report",
            observation=observation,
            state={"evidence_registry": list(REGISTRY)},
        )
        self.assertIs(result["passed"], False)
        workflow = workflow_state.make_initial_state(
            {"task_input": {"goal": "persist failed report path"}, "context": {}, "constraints": {}}
        )
        workflow_state.record_observation(
            workflow,
            current_step_id="synthesize_report",
            observation=observation,
            verifier_result=result,
        )
        self.assertEqual(workflow.report_path, path)
        self.assertEqual(workflow.report_sections, ["History", "Mechanism"])
        state = self._complete_report_state()
        state["report_path"] = f"{FIXTURE_ROOT}/number_only_report.md"
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("in-place source locator", result["message"])

    def test_synthesize_report_rejects_number_only_citations(self):
        result = self._synthesize_report(f"{FIXTURE_ROOT}/number_only_report.md")
        self.assertIs(result["passed"], False)
        self.assertIn("in-place source locator", result["message"])

    def test_synthesize_report_rejects_distant_locators(self):
        result = self._synthesize_report(f"{FIXTURE_ROOT}/distant_locator_report.md")
        self.assertIs(result["passed"], False)
        self.assertIn("in-place source locator", result["message"])

    def test_verify_report_rejects_distant_locators(self):
        state = self._complete_report_state()
        state["report_path"] = f"{FIXTURE_ROOT}/distant_locator_report.md"
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("in-place source locator", result["message"])

    def _synthesize_report(self, path: str):
        return verifiers.verify_synthesize_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="synthesize_report",
            observation={
                "status": "succeeded",
                "summary": "Report synthesis completed.",
                "structured_output": {
                    "outline": "History and mechanism",
                    "report_path": path,
                    "report_summary": "A complete grounded report.",
                    "report_sections": ["History", "Mechanism"],
                    "report_ready_for_verification": True,
                },
            },
            state={"evidence_registry": list(REGISTRY)},
        )


if __name__ == "__main__":
    unittest.main()
