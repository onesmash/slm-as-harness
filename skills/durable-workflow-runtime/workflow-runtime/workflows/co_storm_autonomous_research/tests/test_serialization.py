"""Regression tests for lossless Co-STORM graph-state serialization."""

import json
import os
import sys
import unittest

WORKFLOW_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
RUNTIME_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(WORKFLOW_DIR)))
SKILL_ROOT = os.path.dirname(RUNTIME_ROOT)
REPO_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
for _lib_root in (
    os.path.join(REPO_ROOT, ".venv", "lib"),
    os.path.join(SKILL_ROOT, ".venv", "lib"),
    os.path.join(os.path.dirname(REPO_ROOT), ".venv", "lib"),
):
    if os.path.isdir(_lib_root):
        _site_packages = next(
            (
                os.path.join(_lib_root, name)
                for name in sorted(os.listdir(_lib_root))
                if name.startswith("python")
            ),
            None,
        )
        if _site_packages is not None and _site_packages not in sys.path:
            sys.path.insert(0, _site_packages)
if RUNTIME_ROOT not in sys.path:
    sys.path.insert(0, RUNTIME_ROOT)

from workflows.co_storm_autonomous_research import state as wf_state  # noqa: E402


def _roundtrip(payload: dict) -> dict:
    st = wf_state.deserialize_state(payload)
    return wf_state.serialize_state(st)


class SerializationCapacityTests(unittest.TestCase):
    def test_large_expert_results_survive_serialization(self):
        """A full second-round expert payload must round-trip intact."""
        payload = _roundtrip({
            "round_index": 2,
            "expert_round_index": 2,
            "expert_results_complete": True,
            "expert_results": [
                {
                    "expert_id": f"e{i}",
                    "summary": "s" * 3000,
                    "artifact_path": f"./artifacts/e{i}.md",
                    "new_evidence": [
                        f"https://example.com/{i}/{j} — claim {j} about the robot" * 3
                        for j in range(11)
                    ],
                }
                for i in range(4)
            ],
            "expert_roster": [
                {"id": f"e{i}", "role": f"role{i}", "brief": "brief"}
                for i in range(4)
            ],
            "evidence_registry": [
                f"[{i}] https://example.com/{i} — entry {i}" for i in range(1, 85)
            ],
            "coverage_map": [f"topic {i}" for i in range(88)],
            "coverage_assessment": [
                {
                    "topic_id": f"topic {i}",
                    "status": "covered",
                    "evidence_refs": ["[1]"],
                    "open_gaps": [],
                    "next_validation_metrics": [],
                }
                for i in range(88)
            ],
            "conversation_transcript": ["turn"] * 11,
        })
        self.assertEqual(len(payload["expert_results"]), 4)
        self.assertEqual(payload["expert_round_index"], 2)
        self.assertEqual(len(payload["evidence_registry"]), 84)
        self.assertNotIn("serialization_diagnostics", payload)

    def test_expert_reports_accumulate_across_rounds_and_round_trip(self):
        state = wf_state.make_initial_state({"task_input": {"goal": "research"}})
        for round_index in (1, 2):
            wf_state.record_observation(
                state,
                current_step_id="launch_expert_subagents",
                observation={
                    "status": "succeeded",
                    "structured_output": {
                        "expert_round_index": round_index,
                        "expert_results": [
                            {
                                "expert_id": f"expert-{i}",
                                "summary": f"round {round_index} summary {i}",
                                "artifact_path": f"artifacts/round-{round_index}-expert-{i}.md",
                            }
                            for i in range(2)
                        ],
                        "expert_results_complete": True,
                    },
                },
                verifier_result={"passed": True},
            )

        reports = _roundtrip(wf_state.serialize_state(state))["expert_reports"]
        self.assertEqual(len(reports), 4)
        self.assertEqual({item["expert_round_index"] for item in reports}, {1, 2})
        self.assertEqual(
            {item["artifact_path"] for item in reports},
            {
                f"artifacts/round-{round_index}-expert-{expert_index}.md"
                for round_index in (1, 2)
                for expert_index in range(2)
            },
        )

    def test_legacy_artifact_journal_reconstructs_expert_reports(self):
        payload = _roundtrip({
            "artifacts_by_stage": {
                "launch_expert_subagents": [
                    {
                        "expert_round_index": 1,
                        "expert_results": [
                            {"expert_id": "e1", "summary": "s1", "artifact_path": "r1.md"}
                        ],
                    },
                    {
                        "expert_round_index": 2,
                        "expert_results": [
                            {"expert_id": "e2", "summary": "s2", "artifact_path": "r2.md"}
                        ],
                    },
                ]
            }
        })
        self.assertEqual(
            [row["artifact_path"] for row in payload["expert_reports"]],
            ["r1.md", "r2.md"],
        )

    def test_expert_and_topic_lists_are_not_capped_at_128_items(self):
        expert_count = 140
        topic_count = 140
        registry_count = 300
        payload = _roundtrip({
            "expert_roster": [
                {"id": f"e{i}", "role": f"role{i}", "brief": "brief"}
                for i in range(expert_count)
            ],
            "coverage_map": [f"topic {i}" for i in range(topic_count)],
            "coverage_assessment": [
                {
                    "topic_id": f"topic {i}",
                    "status": "covered",
                    "evidence_refs": ["[1]"],
                    "open_gaps": [],
                    "next_validation_metrics": [],
                }
                for i in range(topic_count)
            ],
            "evidence_registry": [f"[{i}] source-{i} — claim {i}" for i in range(1, registry_count + 1)],
        })
        self.assertEqual(len(payload["expert_roster"]), expert_count)
        self.assertEqual(len(payload["coverage_map"]), topic_count)
        self.assertEqual(len(payload["coverage_assessment"]), topic_count)
        self.assertEqual(len(payload["evidence_registry"]), registry_count)
        self.assertNotIn("serialization_diagnostics", payload)

    def test_large_state_fields_are_not_truncated_or_dropped(self):
        big = "x" * (15 * 1024)
        payload = _roundtrip({
            "evidence_registry": [f"[{i}] {big}" for i in range(35)],
            "coverage_map": [f"topic {i}" for i in range(140)],
            "round_index": 7,
        })
        self.assertEqual(len(payload["evidence_registry"]), 35)
        self.assertTrue(all(big in entry for entry in payload["evidence_registry"]))
        self.assertEqual(len(payload["coverage_map"]), 140)
        self.assertEqual(payload["round_index"], 7)

    def test_large_coverage_and_results_roundtrip_without_truncation(self):
        big_gap = "g" * (14 * 1024)
        payload = _roundtrip({
            "round_index": 3,
            "expert_results_complete": True,
            "evidence_registry": ["[1] a", "[2] b", "[3] c"],
            "coverage_assessment": [
                {
                    "topic_id": f"topic {i}",
                    "status": "bounded_gap",
                    "evidence_refs": ["[1]"],
                    "open_gaps": [big_gap],
                    "next_validation_metrics": [big_gap],
                }
                for i in range(18)
            ],
            "expert_results": [
                {"expert_id": "e", "summary": "s" * 3000, "artifact_path": "a",
                 "new_evidence": ["n" * (15 * 1024)]}
            ],
        })
        self.assertEqual(len(payload["coverage_assessment"]), 18)
        self.assertTrue(all(
            item["open_gaps"] == [big_gap]
            and item["next_validation_metrics"] == [big_gap]
            for item in payload["coverage_assessment"]
        ))
        self.assertEqual(payload["expert_results"][0]["new_evidence"][0], "n" * (15 * 1024))
        self.assertEqual(payload["round_index"], 3)

    def test_no_synthetic_serialization_diagnostics_are_added(self):
        payload = _roundtrip({"round_index": 1, "small": "ok"})
        self.assertNotIn("serialization_diagnostics", payload)


if __name__ == "__main__":
    unittest.main()
