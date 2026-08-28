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
        self.assertIn("Evidence index", result["message"])

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
            any("Evidence index" in str(item) for item in workflow.quality_findings)
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
        self.assertIn("Evidence index", result["message"])

    def test_synthesize_report_accepts_compact_evidence_index(self):
        result = self._synthesize_report(f"{FIXTURE_ROOT}/complete_report.md")
        self.assertIs(result["passed"], True, result["message"])

    def test_synthesize_report_rejects_declared_sections_not_in_artifact(self):
        result = verifiers.verify_synthesize_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="synthesize_report",
            observation={
                "status": "succeeded",
                "summary": "Report synthesis completed.",
                "structured_output": {
                    "outline": "History and mechanism",
                    "report_path": f"{FIXTURE_ROOT}/complete_report.md",
                    "report_summary": "A complete grounded report.",
                    "report_sections": ["Wrong heading", "Mechanism"],
                    "report_ready_for_verification": True,
                },
            },
            state={"evidence_registry": list(REGISTRY)},
        )
        self.assertIs(result["passed"], False)
        self.assertIn("rendered Markdown section headings", result["message"])

    def test_report_path_output_directory_guard_is_fail_closed(self):
        from workflows.co_storm_autonomous_research.citation_locators import (
            report_path_is_within_output_dir,
        )

        report_path = f"{FIXTURE_ROOT}/complete_report.md"
        self.assertTrue(
            report_path_is_within_output_dir(
                str(REPO_ROOT),
                report_path,
                FIXTURE_ROOT,
            )
        )
        self.assertFalse(
            report_path_is_within_output_dir(
                str(REPO_ROOT),
                report_path,
                ".git",
            )
        )
        state = self._complete_report_state()
        state["context"] = {"output_dir": ".git"}
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("configured context.output_dir", result["message"])

    def test_report_sections_accept_numbered_headings_and_nested_details(self):
        from workflows.co_storm_autonomous_research.citation_locators import (
            missing_substantive_report_sections,
        )

        report = (
            "# Report\n\n"
            "## 1. History\n\n"
            "Historical finding.\n\n"
            "## 2. Mechanism (implementation detail)\n\n"
            "Mechanism finding.\n\n"
            "### 2.1 Detail\n\n"
            "Nested detail.\n\n"
            "## Review card\n\n"
            "Review metadata.\n\n"
            "## Evidence index\n\n"
            "- [1] source-a\n"
        )
        self.assertIsNone(
            missing_substantive_report_sections(
                report,
                ["History", "Mechanism"],
            )
        )

    def test_synthesize_report_rejects_missing_evidence_index(self):
        result = self._synthesize_report(f"{FIXTURE_ROOT}/number_only_report.md")
        self.assertIs(result["passed"], False)
        self.assertIn("Evidence index", result["message"])

    def test_synthesize_report_rejects_missing_index_for_distant_locators(self):
        result = self._synthesize_report(f"{FIXTURE_ROOT}/distant_locator_report.md")
        self.assertIs(result["passed"], False)
        self.assertIn("Evidence index", result["message"])

    def test_synthesize_report_rejects_mismatched_evidence_index(self):
        result = self._synthesize_report(f"{FIXTURE_ROOT}/mismatched_evidence_index.md")
        self.assertIs(result["passed"], False)
        self.assertIn("does not match", result["message"])

    def test_synthesize_report_rejects_locator_repeated_in_body(self):
        result = self._synthesize_report(f"{FIXTURE_ROOT}/body_locator_report.md")
        self.assertIs(result["passed"], False)
        self.assertIn("without repeating its source locator", result["message"])

    def test_verify_report_rejects_missing_index_for_distant_locators(self):
        state = self._complete_report_state()
        state["report_path"] = f"{FIXTURE_ROOT}/distant_locator_report.md"
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("Evidence index", result["message"])

    def test_verify_report_rejects_locator_repeated_in_body(self):
        state = self._complete_report_state()
        state["report_path"] = f"{FIXTURE_ROOT}/body_locator_report.md"
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("without repeating its source locator", result["message"])

    def test_evidence_index_rejects_duplicate_rows_and_trailing_content(self):
        from workflows.co_storm_autonomous_research.citation_locators import missing_evidence_index

        duplicate_rows = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "## Evidence index\n\n"
            "- [1] source-a\n"
            "- [1] source-a\n"
        )
        duplicate_result = missing_evidence_index(duplicate_rows, REGISTRY)
        self.assertIsNotNone(duplicate_result)
        self.assertIn("duplicate", duplicate_result)

        trailing_content = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "## Evidence index\n\n"
            "- [1] source-a\n\n"
            "## Notes\n\n"
            "This content must not follow the index.\n"
        )
        trailing_result = missing_evidence_index(trailing_content, REGISTRY)
        self.assertIsNotNone(trailing_result)
        self.assertIn("final section", trailing_result)

    def test_evidence_index_rejects_markdown_code_pseudo_index(self):
        from workflows.co_storm_autonomous_research.citation_locators import missing_evidence_index

        indented_code = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "    ## Evidence index\n"
            "    - [1] source-a\n"
        )
        indented_result = missing_evidence_index(indented_code, REGISTRY)
        self.assertIsNotNone(indented_result)
        self.assertIn("Evidence index", indented_result)

        fenced_code = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "```markdown\n"
            "## Evidence index\n"
            "- [1] source-a\n"
            "```\n"
        )
        fenced_result = missing_evidence_index(fenced_code, REGISTRY)
        self.assertIsNotNone(fenced_result)
        self.assertIn("Evidence index", fenced_result)

        raw_html = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "<pre>\n"
            "## Evidence index\n"
            "- [1] source-a\n"
            "</pre>\n"
        )
        raw_html_result = missing_evidence_index(raw_html, REGISTRY)
        self.assertIsNotNone(raw_html_result)
        self.assertIn("Evidence index", raw_html_result)

        custom_raw_html = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "<custom-block>\n"
            "## Evidence index\n"
            "- [1] source-a\n"
            "</custom-block>\n"
        )
        custom_result = missing_evidence_index(custom_raw_html, REGISTRY)
        self.assertIsNotNone(custom_result)
        self.assertIn("Evidence index", custom_result)

        unclosed_raw_html = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "<pre>\n"
            "## Evidence index\n"
            "- [1] source-a\n"
        )
        unclosed_result = missing_evidence_index(unclosed_raw_html, REGISTRY)
        self.assertIsNotNone(unclosed_result)
        self.assertIn("raw HTML", unclosed_result)

    def test_evidence_index_rejects_inline_code_and_oversized_ids(self):
        from workflows.co_storm_autonomous_research.citation_locators import missing_evidence_index

        inline_code = (
            "# Report\n\n"
            "`[1]`\n\n"
            "## Evidence index\n"
            "- [1] source-a\n"
        )
        inline_result = missing_evidence_index(inline_code, REGISTRY)
        self.assertIsNotNone(inline_result)
        self.assertIn("numeric inline citation", inline_result)

        oversized_id = "9" * 700
        oversized_report = (
            "# Report\n\n"
            f"The finding cites [{oversized_id}].\n\n"
            "## Evidence index\n"
            f"- [{oversized_id}] source-a\n"
        )
        oversized_result = missing_evidence_index(oversized_report, REGISTRY)
        self.assertIsNotNone(oversized_result)
        self.assertIn("exceeds the supported size", oversized_result)

    def test_evidence_index_accepts_crlf_and_rejects_claim_suffix(self):
        from workflows.co_storm_autonomous_research.citation_locators import missing_evidence_index

        crlf_report = (
            "# Report\r\n\r\n"
            "The finding is grounded in evidence [1].\r\n\r\n"
            "## Evidence index\r\n"
            "- [1] source-a\r\n"
        )
        self.assertIsNone(missing_evidence_index(crlf_report, REGISTRY))

        claim_suffix = (
            "# Report\n\n"
            "The finding is grounded in evidence [1].\n\n"
            "## Evidence index\n"
            "- [1] source-a — historical claim\n"
        )
        claim_result = missing_evidence_index(claim_suffix, REGISTRY)
        self.assertIsNotNone(claim_result)
        self.assertIn("does not match", claim_result)

    def test_evidence_index_rejects_unused_registry_locator_in_body(self):
        from workflows.co_storm_autonomous_research.citation_locators import missing_evidence_index

        report = (
            "# Report\n\n"
            "The finding is grounded in evidence [1], while source-b is not cited.\n\n"
            "## Evidence index\n"
            "- [1] source-a\n"
        )
        result = missing_evidence_index(report, REGISTRY)
        self.assertIsNotNone(result)
        self.assertIn("unused evidence source locator", result)

    def test_failed_or_blocked_report_stage_preserves_artifact_paths(self):
        from workflows.co_storm_autonomous_research import state as workflow_state

        report_path = f"{FIXTURE_ROOT}/body_locator_report.md"
        workflow = workflow_state.make_initial_state(
            {"task_input": {"goal": "preserve report paths"}, "context": {}, "constraints": {}}
        )
        synth_observation = {
            "status": "blocked",
            "summary": "Report synthesis was blocked after writing an artifact.",
            "structured_output": {"report_path": report_path},
        }
        workflow_state.record_observation(
            workflow,
            current_step_id="synthesize_report",
            observation=synth_observation,
            verifier_result=None,
        )
        self.assertEqual(workflow.report_path, report_path)

        verify_observation = {
            "status": "failed",
            "summary": "Report verification failed after reading an artifact.",
            "structured_output": {"verified_report_path": report_path},
        }
        workflow_state.record_observation(
            workflow,
            current_step_id="verify_report",
            observation=verify_observation,
            verifier_result=None,
        )
        self.assertEqual(workflow.quality_verdict, "repair")
        self.assertIs(workflow.report_ready, False)
        self.assertEqual(workflow.verified_report_path, report_path)
        self.assertIn("repair is required", workflow.citation_coverage_summary)

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

    def test_expert_verifier_rejects_oversized_citation_id_without_exception(self):
        oversized_id = "9" * 700
        result = verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="launch_expert_subagents",
            observation={
                "status": "succeeded",
                "summary": "An expert returned an oversized citation identifier.",
                "structured_output": {
                    "expert_round_index": 1,
                    "expert_results": [
                        {
                            "expert_id": "historian",
                            "summary": f"Historian evidence [{oversized_id}].",
                            "artifact_path": f"{FIXTURE_ROOT}/historian.md",
                            "new_evidence": [],
                        },
                        {
                            "expert_id": "systems_analyst",
                            "summary": "Systems evidence [2].",
                            "artifact_path": f"{FIXTURE_ROOT}/systems_analyst.md",
                            "new_evidence": [],
                        },
                    ],
                    "expert_results_complete": True,
                    "evidence_registry": list(REGISTRY),
                },
            },
            state={
                "expert_roster": copy.deepcopy(ROSTER),
                "round_index": 0,
                "evidence_registry": list(REGISTRY),
                "constraints": {"max_rounds": 3},
            },
        )
        self.assertIs(result["passed"], False)
        self.assertIn("invalid citation markers", result["message"])

    def test_repair_report_blocked_resumes_to_origin_after_shared_repair(self):
        """HIGH-1 regression: repair_report blocked -> repair_and_resume must preserve
        return_stage_id so shared repair can still resume to the originating report stage.
        Before the fix, apply_transition wiped return_stage_id on that hop and the
        workflow got stuck retrying repair_and_resume (only escape: 3 blocked attempts
        -> partial handoff)."""
        from workflows.co_storm_autonomous_research import (
            graphbuilder_runtime,
            state as workflow_state,
        )

        persisted = workflow_state.deserialize_state(
            {
                "current_stage_id": "repair_report",
                "return_stage_id": "verify_report",
                "repair_context": {"source_stage_id": "verify_report"},
            }
        )

        # Hop 1: repair_report blocked -> triaged by shared repair.
        hop1 = graphbuilder_runtime.run_transition_preview(
            state=persisted,
            current_step_id="repair_report",
            observation={
                "status": "blocked",
                "summary": "Cannot derive concrete repair actions.",
                "structured_output": {"blocked_reason": "missing audit context"},
            },
            verifier_result={"passed": False, "message": "repair_report blocked", "details": {}},
        )
        self.assertEqual(hop1.step_id, "repair_and_resume")
        self.assertEqual(hop1.branch_kind, "repair")
        self.assertEqual(
            persisted.return_stage_id,
            "verify_report",
            "return_stage_id must survive a repair_report block",
        )

        # Hop 2: shared repair succeeds -> resume to the originating report stage.
        hop2 = graphbuilder_runtime.run_transition_preview(
            state=persisted,
            current_step_id="repair_and_resume",
            observation={
                "status": "succeeded",
                "summary": "Shared repair produced actionable guidance.",
                "structured_output": {
                    "retry_reason": "safe to retry",
                    "retry_notes": "provided concrete actions",
                    "repair_actions": ["recheck citation index"],
                },
            },
            verifier_result=None,
        )
        self.assertEqual(
            hop2.step_id,
            "verify_report",
            "shared repair must resume to the originating report stage",
        )
        self.assertEqual(hop2.branch_kind, "continue")

    # ---- expert-result roster/artifact coverage (declared test intents) ----

    def _expert_state(self):
        return {
            "expert_roster": copy.deepcopy(ROSTER),
            "round_index": 0,
            "evidence_registry": list(REGISTRY),
            "constraints": {"max_rounds": 8},
        }

    def _expert_output(self, results=None):
        return {
            "expert_round_index": 1,
            "expert_results": results
            or [
                {
                    "expert_id": "historian",
                    "summary": "Historian completed with evidence [1].",
                    "artifact_path": f"{FIXTURE_ROOT}/historian.md",
                    "new_evidence": [],
                },
                {
                    "expert_id": "systems_analyst",
                    "summary": "Systems analyst completed with evidence [2].",
                    "artifact_path": f"{FIXTURE_ROOT}/systems_analyst.md",
                    "new_evidence": [],
                },
            ],
            "expert_results_complete": True,
            "evidence_registry": list(REGISTRY),
        }

    def _verify_expert(self, output, state=None):
        return verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="launch_expert_subagents",
            observation={
                "status": "succeeded",
                "summary": "Expert results completed.",
                "structured_output": output,
            },
            state=state or self._expert_state(),
        )

    def test_expert_results_rejects_duplicate_expert_id(self):
        output = self._expert_output()
        output["expert_results"][1]["expert_id"] = "historian"
        result = self._verify_expert(output)
        self.assertIs(result["passed"], False)
        self.assertIn("duplicate expert_id", result["message"])

    def test_expert_results_rejects_out_of_order_expert(self):
        output = self._expert_output()
        output["expert_results"].reverse()
        result = self._verify_expert(output)
        self.assertIs(result["passed"], False)
        self.assertIn("expert_results[0].expert_id must be", result["message"])

    def test_expert_results_rejects_skipped_expert_round(self):
        output = self._expert_output()
        output["expert_round_index"] = 2
        result = self._verify_expert(output)
        self.assertIs(result["passed"], False)
        self.assertIn("expert_round_index expected 1", result["message"])

    def test_expert_results_rejects_duplicate_artifact_path(self):
        output = self._expert_output()
        output["expert_results"][1]["artifact_path"] = output["expert_results"][0]["artifact_path"]
        result = self._verify_expert(output)
        self.assertIs(result["passed"], False)
        self.assertIn("duplicate artifact_path", result["message"])

    def test_expert_results_rejects_ungrounded_result(self):
        output = self._expert_output(
            [
                {
                    "expert_id": "historian",
                    "summary": "Plain summary without citations.",
                    "artifact_path": f"{FIXTURE_ROOT}/ungrounded_artifact.md",
                    "new_evidence": [],
                },
                {
                    "expert_id": "systems_analyst",
                    "summary": "Plain summary without citations.",
                    "artifact_path": f"{FIXTURE_ROOT}/uncited_report.md",
                    "new_evidence": [],
                },
            ]
        )
        result = self._verify_expert(output)
        self.assertIs(result["passed"], False)
        self.assertIn("must cite at least one merged evidence entry", result["message"])

    def test_expert_results_rejects_unsafe_artifact_path(self):
        output = self._expert_output()
        output["expert_results"][1]["artifact_path"] = "../../../etc/passwd"
        result = self._verify_expert(output)
        self.assertIs(result["passed"], False)
        self.assertIn("not repository-relative", result["message"])

    # ---- roundtable declared-test-intent coverage ----

    def test_roundtable_rejects_unresolvable_evidence_ref(self):
        output = self._bounded_gap_continue_output()
        output["coverage_assessment"][1]["evidence_refs"] = ["[99]"]
        result = self._verify_roundtable(output)
        self.assertIs(result["passed"], False)
        self.assertIn("unknown evidence id", result["message"])

    def test_roundtable_rejects_missing_expert_package(self):
        state = self._roundtable_state()
        state["expert_results_complete"] = False
        result = self._verify_roundtable(self._bounded_gap_continue_output(), state)
        self.assertIs(result["passed"], False)
        self.assertIn("completed expert-result package", result["message"])

    def test_roundtable_rejects_rewritten_transcript_prefix(self):
        output = self._bounded_gap_continue_output()
        output["conversation_transcript"] = ["rewritten prior turn", "bounded-gap decision"]
        result = self._verify_roundtable(output)
        self.assertIs(result["passed"], False)
        self.assertIn("preserve the prior transcript", result["message"])

    # ---- reorganization declared-test-intent coverage ----

    def test_reorganization_rejects_skipped_counter(self):
        result = verifiers.verify_reorganize_knowledge_space(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="reorganize_knowledge_space",
            observation={
                "status": "succeeded",
                "summary": "Reorganization skipped a counter value.",
                "structured_output": {
                    "knowledge_map_summary": "reorganized map",
                    "coverage_map": ["history", "mechanism"],
                    "evidence_registry": list(REGISTRY),
                    "reorganization_summary": "Reorganized topics.",
                    "reorganization_count": 3,
                    "reorganized": True,
                },
            },
            state={
                "constraints": {"max_reorganizations": 2},
                "reorganization_count": 1,
                "evidence_registry": list(REGISTRY),
            },
        )
        self.assertIs(result["passed"], False)
        self.assertIn("advance exactly one step", result["message"])

    def test_reorganization_rejects_reordered_registry(self):
        result = verifiers.verify_reorganize_knowledge_space(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="reorganize_knowledge_space",
            observation={
                "status": "succeeded",
                "summary": "Reorganization reordered registry rows.",
                "structured_output": {
                    "knowledge_map_summary": "reorganized map",
                    "coverage_map": ["history", "mechanism"],
                    "evidence_registry": ["[2] source-b", "[1] source-a", "[3] source-c"],
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

    # ---- verify_report declared-test-intent coverage ----

    def test_verify_report_rejects_unknown_marker(self):
        state = self._complete_report_state()
        state["report_path"] = f"{FIXTURE_ROOT}/unknown_citation_report.md"
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("absent from evidence_registry", result["message"])

    def test_verify_report_rejects_uncited_pass(self):
        state = self._complete_report_state()
        state["report_path"] = f"{FIXTURE_ROOT}/uncited_report.md"
        result = self._verify_report(state)
        self.assertIs(result["passed"], False)
        self.assertIn("at least one rendered numeric citation", result["message"])

    def test_verify_report_rejects_unresolved_critical_finding(self):
        output = self._report_output(f"{FIXTURE_ROOT}/complete_report.md")
        output["quality_findings"] = ["Unresolved critical issue in section two."]
        result = verifiers.verify_verify_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="verify_report",
            observation={
                "status": "succeeded",
                "summary": "Verifier reported an unresolved critical finding.",
                "structured_output": output,
            },
            state=self._complete_report_state(),
        )
        self.assertIs(result["passed"], False)
        self.assertIn("unresolved critical", result["message"])

    def test_verify_report_accepts_resolved_critical_finding(self):
        output = self._report_output(f"{FIXTURE_ROOT}/complete_report.md")
        output["quality_findings"] = ["Critical issue was resolved in this pass."]
        result = verifiers.verify_verify_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="verify_report",
            observation={
                "status": "succeeded",
                "summary": "The only critical finding was resolved.",
                "structured_output": output,
            },
            state=self._complete_report_state(),
        )
        self.assertIs(result["passed"], True, result["message"])

    def test_verify_report_accepts_bounded_gap_in_complete_sufficient_report(self):
        """B1 regression: a bounded_gap topic is handled when complete + coverage_sufficient + empty plan."""
        state = self._complete_report_state()
        assessment = state.get("coverage_assessment") or []
        assessment.append({
            "topic_id": "mechanism-gap",
            "status": "bounded_gap",
            "evidence_refs": ["[1]"],
            "open_gaps": ["Causal evidence still thin."],
            "next_validation_metrics": ["Find two independent causal sources."],
        })
        state["coverage_assessment"] = assessment
        output = self._report_output(f"{FIXTURE_ROOT}/complete_report.md")
        result = verifiers.verify_verify_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="verify_report",
            observation={
                "status": "succeeded",
                "summary": "Moderator judged the bounded gap immaterial with an empty plan.",
                "structured_output": output,
            },
            state=state,
        )
        self.assertIs(result["passed"], True, result["message"])

    def test_verify_report_accepts_assessed_topics_beyond_coverage_map(self):
        """B2 regression: assessed topic ids may be a superset of coverage_map."""
        state = self._complete_report_state()
        assessment = state.get("coverage_assessment") or []
        assessment.append({
            "topic_id": "extra-topic",
            "status": "covered",
            "evidence_refs": ["[1]"],
            "open_gaps": [],
            "next_validation_metrics": [],
        })
        state["coverage_assessment"] = assessment
        output = self._report_output(f"{FIXTURE_ROOT}/complete_report.md")
        result = verifiers.verify_verify_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="verify_report",
            observation={
                "status": "succeeded",
                "summary": "Assessment covers the map and one extra topic.",
                "structured_output": output,
            },
            state=state,
        )
        self.assertIs(result["passed"], True, result["message"])

    def test_verify_report_accepts_negated_critical_finding(self):
        """M1 regression: negated wording like 'No critical issues were found' is a pass, not an unresolved finding."""
        output = self._report_output(f"{FIXTURE_ROOT}/complete_report.md")
        output["quality_findings"] = ["No critical issues were found in the report."]
        result = verifiers.verify_verify_report(
            repo_root=str(REPO_ROOT),
            run_id="semantic-coverage-review",
            step_id="verify_report",
            observation={
                "status": "succeeded",
                "summary": "No critical issues found.",
                "structured_output": output,
            },
            state=self._complete_report_state(),
        )
        self.assertIs(result["passed"], True, result["message"])

    def test_expert_results_accepts_em_dash_inside_claim(self):
        """M2 regression: claim text may itself contain ' — '; only the first separator matters."""
        from workflows.co_storm_autonomous_research import verifiers as wf_verifiers
        state = {
            "expert_roster": [
                {"id": "historian", "role": "historian", "brief": "Trace origins."},
                {"id": "systems_analyst", "role": "systems analyst", "brief": "Trace mechanisms."},
            ],
            "round_index": 0,
            "constraints": {"max_rounds": 3, "max_reorganizations": 1},
            "evidence_registry": ["[1] source-a", "[2] source-b"],
        }
        output = {
            "expert_round_index": 1,
            "expert_results": [
                {
                    "expert_id": "historian",
                    "summary": "History complete [1].",
                    "artifact_path": "skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/historian.md",
                    "new_evidence": ["source-b — the main result — was replicated"],
                },
                {
                    "expert_id": "systems_analyst",
                    "summary": "Mechanism complete [1].",
                    "artifact_path": "skills/durable-workflow-runtime/workflow-runtime/workflows/co_storm_autonomous_research/tests/fixtures/systems_analyst.md",
                    "new_evidence": [],
                },
            ],
            "expert_results_complete": True,
            "evidence_registry": ["[1] source-a", "[2] source-b"],
        }
        result = wf_verifiers.verify_launch_expert_subagents(
            repo_root=str(REPO_ROOT),
            run_id="generated-test-run",
            step_id="launch_expert_subagents",
            observation={"status": "succeeded", "summary": "Experts done.", "structured_output": output},
            state=state,
        )
        self.assertIs(result["passed"], True, result["message"])



if __name__ == "__main__":
    unittest.main()
