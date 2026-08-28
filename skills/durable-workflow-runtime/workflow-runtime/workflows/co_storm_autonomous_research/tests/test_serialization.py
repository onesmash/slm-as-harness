"""Regression tests for graph_state serialization capacity behavior.

Covers the failure mode observed in run_892c80896e: a large launch
observation (84-entry registry + 88-topic assessment + expert results)
exceeded the old 64 KiB dict compaction budget, and `_compact_value`'s
`break` silently dropped every field after the oversized one — including
small int fields such as `round_index` — which dead-locked the
autonomous_roundtable verifier's "persisted expert_results must contain
completed results" check.

These tests pin the fixes:
1. oversized fields are dropped individually, later fields survive;
2. the compaction budget is large enough for a full expert round;
3. serialize_state records `serialization_diagnostics` when a top-level
   field is dropped, so verifiers can surface a root cause.
"""

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
from workflows.co_storm_autonomous_research.state import _compact_value  # noqa: E402


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

    def test_oversized_single_field_drops_only_itself(self):
        """A field that pushes the cumulative dict budget over the limit is
        dropped individually; later fields (including a small one that fits
        after the oversized one) survive because compaction continues."""
        big = "x" * (15 * 1024)  # bounded_text keeps strings under 16 KiB
        # 17 big fields (~255 KiB) fit; the 18th pushes over the 256 KiB budget
        # and is dropped; the small field after it fits again and survives.
        fields = {f"f_{i:02d}": big for i in range(18)}
        fields["f_18"] = "kept-after-overflow"
        fields["round_index"] = 7
        payload = _compact_value(fields)
        self.assertNotIn("f_17", payload, "overflowing field must be dropped")
        self.assertEqual(payload.get("f_18"), "kept-after-overflow",
                         "fields after the dropped one must survive (no hard break)")
        self.assertEqual(payload.get("round_index"), 7)

    def test_serialization_diagnostics_recorded_on_drop(self):
        """serialize_state records which top-level field was dropped."""
        # A large coverage_assessment fills most of the budget; expert_results
        # then pushes the cumulative dict over the limit and is dropped, while
        # the small round_index field later in key order survives.
        big_gap = "g" * (15 * 1024)  # bounded_text keeps strings under 16 KiB
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
                for i in range(88)
            ],
            "expert_results": [
                {"expert_id": "e", "summary": "s" * 3000, "artifact_path": "a",
                 "new_evidence": ["n" * (15 * 1024)]}
            ],
        })
        diag = payload.get("serialization_diagnostics")
        self.assertIsInstance(diag, dict, "diagnostics must be recorded on drop")
        self.assertIn("expert_results", diag.get("dropped_fields", []))
        self.assertEqual(payload.get("round_index"), 3,
                         "fields after the dropped one must survive")

    def test_diagnostics_absent_when_nothing_dropped(self):
        payload = _roundtrip({"round_index": 1, "small": "ok"})
        self.assertNotIn("serialization_diagnostics", payload)


if __name__ == "__main__":
    unittest.main()
