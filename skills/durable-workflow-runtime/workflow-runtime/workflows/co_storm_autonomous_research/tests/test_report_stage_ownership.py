"""Regression tests pinning report-stage ownership and hardened path helpers.

These tests exist because two classes of change are invisible to the
generated behavioural suite (`tests/test_workflow.py`, rendered from
`spec.json:regression_tests`), yet have silently regressed before:

1. **Report-stage skill ownership.** The three report stages
   (`synthesize_report`, `verify_report`, `repair_report`) are owned by
   `report-nex`. The generated regression tests exercise transitions and
   verifiers, never `contract.skill_routing`, so a regeneration that
   reverted the owner (or a hand edit that dropped it) would still pass.
   This file fails loudly instead.

2. **Hardened repo-path helpers in `verifiers.py`.** `workflow-creator`
   regenerates `verifiers.py` from its own template, which reverts two
   hand-hardened behaviours:
     - `_safe_repo_path` must accept an absolute POSIX path that resolves
       inside the repository root (the generator's template rejects every
       absolute path). `spec.json` boundaries and the rendered prompts both
       promise absolute `output_dir` / `report_path` support, so the
       reverted helper breaks a documented contract.
     - `_repo_path_policy_error` / `_artifact_list_policy_error` wrap
       `Path.relative_to` in `try/except ValueError` so a hostile path
       yields the verifier's failure message instead of raising.
   Nothing else in the repo pins this behaviour, so re-running
   `create_workflow.py --force` used to reintroduce the regression
   unnoticed. These tests make that regeneration fail loudly.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


WORKFLOW_DIR = Path(__file__).resolve().parents[1]
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

from workflows.co_storm_autonomous_research import citation_locators, contract, verifiers


REPORT_STAGES = ("synthesize_report", "verify_report", "repair_report")
REPORT_STAGE_OWNER = "report-nex"
RETIRED_OWNER = "content-research-writer"


def _report_stage_boundaries(step_id):
    spec = json.loads((WORKFLOW_DIR / "spec.json").read_text(encoding="utf-8"))
    for stage in spec["stages"]:
        if stage["step_id"] == step_id:
            return stage["prompt_sections"]["boundaries"]
    raise AssertionError(f"stage {step_id} not found in spec.json")


class ReportStageOwnershipTests(unittest.TestCase):
    """The three report stages stay owned by report-nex."""

    def test_report_stages_route_to_report_nex(self):
        for step_id in REPORT_STAGES:
            with self.subTest(step_id=step_id):
                step_contract = contract.get_step_contract(step_id)
                routed = {route.skill for route in step_contract.skill_routing}
                self.assertEqual(
                    routed,
                    {REPORT_STAGE_OWNER},
                    f"{step_id} must route only to {REPORT_STAGE_OWNER}, got {sorted(routed)}",
                )

    def test_no_stage_routes_to_the_retired_owner(self):
        routed = {
            route.skill
            for step_id in contract.list_step_contract_ids()
            for route in contract.get_step_contract(step_id).skill_routing
        }
        self.assertNotIn(RETIRED_OWNER, routed)

    def test_manifest_declares_report_nex_dependency(self):
        manifest = json.loads((WORKFLOW_DIR / "manifest.json").read_text(encoding="utf-8"))
        skill_ids = {
            dependency["id"]
            for dependency in manifest["dependencies"]
            if dependency["type"] == "skill"
        }
        self.assertIn(REPORT_STAGE_OWNER, skill_ids)
        self.assertNotIn(RETIRED_OWNER, skill_ids)

    def test_manifest_covers_every_routed_skill(self):
        """Mirror of the runtime's preflight consistency gate."""
        manifest = json.loads((WORKFLOW_DIR / "manifest.json").read_text(encoding="utf-8"))
        declared = {
            dependency["id"]
            for dependency in manifest["dependencies"]
            if dependency["type"] in {"skill", "mcp"}
        }
        missing = {
            step_id: sorted(
                {
                    route.skill
                    for route in contract.get_step_contract(step_id).skill_routing
                    if route.skill not in declared
                }
            )
            for step_id in contract.list_step_contract_ids()
        }
        self.assertEqual(
            {step: skills for step, skills in missing.items() if skills},
            {},
        )

    def test_report_prompt_assets_invoke_report_nex(self):
        for step_id in REPORT_STAGES:
            with self.subTest(step_id=step_id):
                prompt_path = WORKFLOW_DIR / "prompts" / f"{step_id}.md"
                first_line = prompt_path.read_text(encoding="utf-8").splitlines()[0]
                self.assertTrue(
                    first_line.startswith(f"/{REPORT_STAGE_OWNER} "),
                    f"{step_id}.md must open with /{REPORT_STAGE_OWNER}, got {first_line[:80]!r}",
                )

    def test_retired_owner_absent_from_generated_surfaces(self):
        tracked = [
            WORKFLOW_DIR / "spec.json",
            WORKFLOW_DIR / "contract.py",
            WORKFLOW_DIR / "manifest.json",
            WORKFLOW_DIR / "prompts" / "synthesize_report.md",
            WORKFLOW_DIR / "prompts" / "verify_report.md",
            WORKFLOW_DIR / "prompts" / "repair_report.md",
            WORKFLOW_DIR / "references" / "flowchart.md",
        ]
        for path in tracked:
            with self.subTest(path=path.name):
                self.assertNotIn(RETIRED_OWNER, path.read_text(encoding="utf-8"))

    def test_report_stages_keep_autonomy_boundary(self):
        """The workflow owns the no-mid-stage-interaction policy.

        The routed skill gates long documents behind user confirmation and
        can ask a 'please select' mode question; an autonomous run must not
        stall on either.
        """
        for step_id in REPORT_STAGES:
            with self.subTest(step_id=step_id):
                boundaries = _report_stage_boundaries(step_id)
                joined = " ".join(boundaries)
                self.assertIn("autonomously", joined)
                self.assertIn("please select", joined)

    def test_synthesize_report_authorizes_the_artifact_write(self):
        """The routed skill declares itself read-only; the stage must write."""
        joined = " ".join(_report_stage_boundaries("synthesize_report"))
        self.assertIn("sanctioned write", joined)
        self.assertIn("read-only", joined)

    def test_report_stages_map_evidence_registry_to_claim_ledger(self):
        """The routed skill's hard gates need a ledger the workflow lacks."""
        for step_id in REPORT_STAGES:
            with self.subTest(step_id=step_id):
                joined = " ".join(_report_stage_boundaries(step_id))
                self.assertIn("claim-ledger", joined)
                self.assertIn("claim_evidence_map", joined)


class HardenedRepoPathHelperTests(unittest.TestCase):
    """Pin the hand-hardened path helpers against generator regeneration."""

    def setUp(self):
        # resolve() keeps the root symlink-free, so an absolute path under it
        # exercises path handling rather than /var -> /private/var aliasing.
        self.repo_root = Path(tempfile.mkdtemp()).resolve()
        (self.repo_root / "out").mkdir()
        self.report_file = self.repo_root / "out" / "r.md"
        self.report_file.write_text("# Title\n\n## Executive summary\n\nbody [1]\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def test_safe_repo_path_accepts_absolute_path_inside_root(self):
        resolved = verifiers._safe_repo_path(str(self.repo_root), str(self.report_file))
        self.assertIsNotNone(
            resolved,
            "absolute report_path support was lost; the generator's "
            "_safe_repo_path rejects every absolute path",
        )
        self.assertEqual(resolved, self.report_file)

    def test_safe_repo_path_accepts_equivalent_relative_path(self):
        self.assertEqual(
            verifiers._safe_repo_path(str(self.repo_root), "out/r.md"),
            self.report_file,
        )

    def test_absolute_report_path_is_within_output_dir(self):
        self.assertTrue(
            citation_locators.report_path_is_within_output_dir(
                str(self.repo_root), str(self.report_file), "out"
            )
        )
        self.assertTrue(
            citation_locators.report_path_is_within_output_dir(
                str(self.repo_root), "out/r.md", "out"
            )
        )

    def test_safe_repo_path_rejects_hostile_paths(self):
        for raw in ("../../etc/hosts", "a\\b.md", "/etc/hosts", "", "out/../r.md"):
            with self.subTest(raw=raw):
                self.assertIsNone(verifiers._safe_repo_path(str(self.repo_root), raw))

    def test_repo_path_policy_returns_message_instead_of_raising(self):
        template = {"required_prefix": "out/", "forbidden_prefixes": [], "required_suffix": None}
        for actual in ("", None, 123, "../../etc/hosts", "a\\b.md", "/etc/hosts"):
            with self.subTest(actual=actual):
                try:
                    result = verifiers._repo_path_policy_error(
                        actual, template, str(self.repo_root), "MESSAGE"
                    )
                except ValueError as exc:  # pragma: no cover - regression guard
                    self.fail(f"hostile path raised instead of failing closed: {exc}")
                self.assertEqual(result, "MESSAGE")

    def test_repo_path_policy_accepts_path_inside_root(self):
        template = {"required_prefix": "out/", "forbidden_prefixes": [], "required_suffix": None}
        self.assertIsNone(
            verifiers._repo_path_policy_error(
                str(self.report_file), template, str(self.repo_root), "MESSAGE"
            )
        )

    def test_safe_repo_path_delegates_to_shared_citation_locators(self):
        """The hardened helper must reuse the shared module, not re-inline it."""
        source = (WORKFLOW_DIR / "verifiers.py").read_text(encoding="utf-8")
        self.assertIn("citation_locators.resolve_safe_repo_file", source)
        self.assertIn("citation_locators.resolve_safe_repo_directory", source)


class CitationLocatorRegressionTests(unittest.TestCase):
    """Pin the three citation_locators defects fixed alongside the skill swap."""

    def test_evidence_index_heading_accepts_common_numeric_prefixes(self):
        """The spec promises a numeric heading prefix; the regex must match it.

        Only ASCII 'N.' used to match, so '## 7) Evidence index' and
        '## 7、证据索引' failed and surfaced as a misleading report_sections error.
        """
        for heading in (
            "## Evidence index",
            "## 证据索引",
            "## 7. Evidence index",
            "## 7) Evidence index",
            "## 7、证据索引",
            "## 7. 证据索引",
        ):
            with self.subTest(heading=heading):
                self.assertTrue(
                    citation_locators._INDEX_HEADING.search(heading),
                    f"Evidence index heading not recognized: {heading!r}",
                )

    def test_bare_autolink_is_not_an_unclosed_html_block(self):
        for line in (
            "<https://example.com/plain>",
            "<http://a.b/c>",
            "<br/>",
            '<a href="x">y</a>',
        ):
            with self.subTest(line=line):
                _, error = citation_locators._mask_raw_html_blocks(line + "\n")
                self.assertIsNone(error, f"valid line rejected as raw HTML: {line!r}")

    def test_genuine_unclosed_html_block_is_still_rejected(self):
        _, error = citation_locators._mask_raw_html_blocks("<div>\nunclosed\n")
        self.assertIsNotNone(error)

    def test_absolute_path_under_symlinked_ancestor_is_accepted(self):
        """An absolute path may legitimately traverse /tmp -> /private/tmp.

        The path is deliberately NOT resolved here, so one of its ancestors is
        a symlink; that used to be rejected while the relative form passed.
        """
        repo_root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo_root, ignore_errors=True)
        (repo_root / "out").mkdir()
        report_file = repo_root / "out" / "r.md"
        report_file.write_text("# Title\n", encoding="utf-8")

        self.assertIsNotNone(
            citation_locators.resolve_safe_repo_file(str(repo_root), str(report_file))
        )
        self.assertIsNotNone(
            citation_locators.resolve_safe_repo_file(str(repo_root), "out/r.md")
        )
        self.assertTrue(
            citation_locators.report_path_is_within_output_dir(
                str(repo_root), str(report_file), "out"
            )
        )


class HiddenCitationMaskingTests(unittest.TestCase):
    """Citations hidden in code or HTML must not count as visible citations.

    Every masker pattern is line-anchored (`^[ ]{0,3}```, `^[ ]{0,3}<tag`,
    four-space indent), and none of them used to look past a blockquote marker.
    A report whose only markers sat in `>     [1] [2] [3]` therefore passed the
    whole citation gate with nothing readable in the body, while the identical
    unquoted form failed. `_blockquote_view` closes that hole.
    """

    SECTIONS = ("History", "Mechanism", "Evidence quality", "Limitations")

    def _verify(self, hidden_line):
        repo_root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, repo_root, ignore_errors=True)
        sections = "".join(
            f"## {name}\n\nprose without any marker.\n\n" for name in self.SECTIONS
        )
        (repo_root / "r.md").write_text(
            "# T\n\nReport scope: complete\n\n"
            + sections
            + hidden_line
            + "\n## Evidence index\n\n- [1] source-a\n- [2] source-b\n- [3] source-c\n",
            encoding="utf-8",
        )
        return verifiers.verify_synthesize_report(
            repo_root=str(repo_root),
            run_id="hidden-citation",
            step_id="synthesize_report",
            observation={
                "status": "succeeded",
                "summary": "Markers live only inside a code or HTML region.",
                "structured_output": {
                    "outline": "History and mechanism",
                    "report_path": "r.md",
                    "report_summary": "A grounded report.",
                    "report_sections": list(self.SECTIONS),
                    "report_ready_for_verification": True,
                },
            },
            state={"evidence_registry": ["[1] source-a", "[2] source-b", "[3] source-c"]},
        )

    def test_hidden_citations_never_satisfy_the_gate(self):
        for label, hidden in (
            ("indented code", "    [1] [2] [3]\n"),
            ("blockquoted indented code", ">     [1] [2] [3]\n"),
            ("nested blockquoted indented code", "> >     [1] [2] [3]\n"),
            ("fenced code", "```\n[1] [2] [3]\n```\n"),
            ("blockquoted fence", "> ```\n> [1] [2] [3]\n> ```\n"),
            ("blockquoted html block", "> <div>\n> [1] [2] [3]\n> </div>\n"),
        ):
            with self.subTest(hidden=label):
                result = self._verify(hidden)
                self.assertIs(
                    result["passed"],
                    False,
                    f"{label} let hidden markers satisfy the citation gate",
                )

    def test_visible_blockquoted_citation_still_counts(self):
        result = self._verify("> visible prose [1] [2] [3]\n")
        self.assertIs(result["passed"], True, result["message"])

    def test_blockquote_view_strips_repeated_markers(self):
        self.assertEqual(citation_locators._blockquote_view(">     x"), "    x")
        self.assertEqual(citation_locators._blockquote_view("> >   x"), "  x")
        self.assertEqual(citation_locators._blockquote_view("   > x"), "x")
        self.assertEqual(citation_locators._blockquote_view("plain"), "plain")
        self.assertEqual(citation_locators._blockquote_view("a > b"), "a > b")

    def test_absolute_path_safety_still_enforced(self):
        repo_root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, repo_root, ignore_errors=True)
        self.assertIsNone(citation_locators.resolve_safe_repo_file(str(repo_root), "/etc/hosts"))
        self.assertIsNone(
            citation_locators.resolve_safe_repo_file(str(repo_root), "../../etc/hosts")
        )
        self.assertIsNone(citation_locators.resolve_safe_repo_file(str(repo_root), "a\\b.md"))


class ReportLoopBoundTests(unittest.TestCase):
    """Pin the report-loop bound and the recovery fail-closed condition."""

    def _spec(self):
        return json.loads((WORKFLOW_DIR / "spec.json").read_text(encoding="utf-8"))

    def _stage(self, step_id):
        return next(s for s in self._spec()["stages"] if s["step_id"] == step_id)

    def test_report_sections_floor_lives_in_the_shared_helper(self):
        """The floor must not sit in a template that runs before the real checks.

        A `min_count` template is evaluated before the custom requirements, so
        with fewer than four sections it masked every concrete defect (a
        mismatched index row, a repeated locator, an unclosed fence) behind
        "must contain at least four substantive sections". The floor now lives
        in `missing_substantive_report_sections`, next to the index checks.
        """
        from workflows.co_storm_autonomous_research import citation_locators

        self.assertEqual(citation_locators._MIN_SUBSTANTIVE_SECTIONS, 4)
        template_ids = {
            template.get("id")
            for template in self._stage("synthesize_report")["verifier_templates"]
        }
        self.assertNotIn("report_requires_multiple_sections", template_ids)
        report = "# Report\n\n## A\n\nx\n\n## B\n\ny\n\n## C\n\nz\n"
        message = citation_locators.missing_substantive_report_sections(
            report, ["A", "B", "C"]
        )
        self.assertIsNotNone(message)
        self.assertIn("at least 4 substantive", message)

    def test_section_and_index_defects_are_reported_together(self):
        """One repair pass must see both defects, not just the first one.

        Driving the real verifier, not grepping it: a report that is short of
        the section floor AND has a mismatched index row used to report only the
        section count, so the next repair pass spent a cycle rediscovering the
        concrete citation defect.
        """
        repo_root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, repo_root, ignore_errors=True)
        (repo_root / "r.md").write_text(
            "# T\n\nReport scope: complete\n\n"
            "## History\n\nbody [1]\n\n"
            "## Mechanism\n\nbody [2]\n\n"
            "## Evidence index\n\n- [1] wrong-locator\n- [2] source-b\n",
            encoding="utf-8",
        )
        result = verifiers.verify_synthesize_report(
            repo_root=str(repo_root),
            run_id="combined-defect",
            step_id="synthesize_report",
            observation={
                "status": "succeeded",
                "summary": "Two defects at once.",
                "structured_output": {
                    "outline": "History and mechanism",
                    "report_path": "r.md",
                    "report_summary": "A grounded report.",
                    "report_sections": ["History", "Mechanism"],
                    "report_ready_for_verification": True,
                },
            },
            state={"evidence_registry": ["[1] source-a", "[2] source-b"]},
        )
        self.assertIs(result["passed"], False)
        self.assertIn("at least 4 substantive", result["message"])
        self.assertIn("does not match", result["message"])

    def _verify_report_message(self, report_body, declared_sections):
        repo_root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, repo_root, ignore_errors=True)
        (repo_root / "r.md").write_text(report_body, encoding="utf-8")
        state = {
            "report_path": "r.md",
            "evidence_registry": ["[1] source-a", "[2] source-b"],
            "report_scope_status": "complete",
            "coverage_sufficient": True,
            "next_round_validation_plan": [],
            "coverage_assessment": [
                {"topic_id": "history", "status": "covered"},
                {"topic_id": "mechanism", "status": "covered"},
            ],
        }
        if declared_sections is not None:
            state["report_sections"] = declared_sections
        return verifiers.verify_verify_report(
            repo_root=str(repo_root),
            run_id="verify-message",
            step_id="verify_report",
            observation={
                "status": "succeeded",
                "summary": "Report audit completed.",
                "structured_output": {
                    "quality_verdict": "pass",
                    "quality_findings": [],
                    "citation_coverage_summary": "All citations resolve.",
                    "report_ready": True,
                    "verified_report_path": "r.md",
                },
            },
            state=state,
        )

    def test_verify_report_states_each_defect_once(self):
        """Two requirements must not both report the same section defect.

        `report_citation_integrity` used to early-return the bare section error
        while its sibling returned "section; index", so the joined message
        repeated the section text; whole-message dedupe cannot collapse a
        superstring.
        """
        result = self._verify_report_message(
            "# T\n\nReport scope: complete\n\n"
            "## History\n\nbody [1]\n\n"
            "## Mechanism\n\nbody [2]\n\n"
            "## Evidence index\n\n- [1] wrong-locator\n- [2] source-b\n",
            ["History", "Mechanism"],
        )
        self.assertIs(result["passed"], False)
        self.assertEqual(result["message"].count("at least 4 substantive"), 1, result["message"])
        self.assertIn("does not match", result["message"])

    def test_verify_report_fails_closed_without_persisted_sections(self):
        """Every sibling signal fails closed; the section signal must too."""
        result = self._verify_report_message(
            "# T\n\nReport scope: complete\n\n"
            "## History\n\nbody [1]\n\n"
            "## Mechanism\n\nbody [2]\n\n"
            "## Evidence index\n\n- [1] source-a\n- [2] source-b\n",
            None,
        )
        self.assertIs(result["passed"], False)
        self.assertIn("report_sections is required", result["message"])

    def test_repair_report_does_not_retry_on_a_missing_verifier_result(self):
        """A missing verifier result must not spin the recovery stage.

        require_passing_verifier=True made a missing result retry repair_report
        for ever, bounded only by max_steps.
        """
        self.assertFalse(self._stage("repair_report")["require_passing_verifier"])
        policy = (WORKFLOW_DIR / "policy.py").read_text(encoding="utf-8")
        self.assertIn(
            "if verifier_result is not None and not _verifier_is_passed(verifier_result):",
            policy,
        )

    def test_report_loop_declares_an_enforced_cycle_limit(self):
        cycle_limit = self._stage("synthesize_report")["cycle_limit"]
        self.assertIsNotNone(cycle_limit, "report loop has no declared cycle limit")
        policy = (WORKFLOW_DIR / "policy.py").read_text(encoding="utf-8")
        self.assertIn(cycle_limit["constraint_key"], policy)
        self.assertIn(cycle_limit["next_node"], policy)
        self.assertIn(
            cycle_limit["constraint_key"],
            self._spec()["runtime_defaults"],
        )

    def test_spec_runtime_defaults_match_the_effective_state_defaults(self):
        """spec.runtime_defaults is documentation; state.py is what runs.

        state_mode is custom, so the generator PRESERVES state.py instead of
        rendering it from the spec. Raising max_steps in spec.json alone is
        therefore inert, which is exactly how a false "default 36" claim once
        reached four published surfaces.
        """
        from workflows.co_storm_autonomous_research import state as workflow_state

        spec_defaults = self._spec()["runtime_defaults"]
        effective = dict(workflow_state.RUNTIME_DEFAULTS)
        self.assertEqual(
            spec_defaults,
            effective,
            "spec.json runtime_defaults drifted from state.py RUNTIME_DEFAULTS; "
            "custom state.py is preserved by regeneration, so both must be edited",
        )
        initial = workflow_state.make_initial_state(
            {"task_input": {"goal": "defaults guard"}, "context": {}, "constraints": {}}
        )
        for key, value in spec_defaults.items():
            self.assertEqual(dict(initial.constraints).get(key), value)

    def test_max_steps_covers_the_workflow_worst_case(self):
        from workflows.co_storm_autonomous_research import state as workflow_state

        defaults = dict(workflow_state.RUNTIME_DEFAULTS)
        # warm start + (launch + roundtable) per round + reorganizations
        # + the bounded report loop (attempts + verify + repair) + finalize
        attempts = defaults["max_report_synthesis_attempts"]
        report_loop = attempts + (attempts - 1) * 2
        worst_case = (
            1
            + defaults["max_rounds"] * 2
            + defaults["max_reorganizations"]
            + report_loop
            + 1
        )
        self.assertGreaterEqual(defaults["max_steps"], worst_case)


if __name__ == "__main__":
    unittest.main()
