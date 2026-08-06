import sys
import tempfile
import unittest
from pathlib import Path


RUNTIME_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = RUNTIME_ROOT.parent
REPO_ROOT = SKILL_ROOT.parents[1]
for _lib_root in (REPO_ROOT / ".venv" / "lib", SKILL_ROOT / ".venv" / "lib", REPO_ROOT.parent / ".venv" / "lib"):
    _site_packages = next(_lib_root.glob("python*/site-packages"), None)
    if _site_packages is not None and str(_site_packages) not in sys.path:
        sys.path.insert(0, str(_site_packages))
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from runtime.models import Observation
from workflows.co_storm_autonomous_research import state as workflow_state, verifiers


class FanoutContractTests(unittest.TestCase):
    def _roster(self):
        return [
            {"id": "historian", "role": "historian", "brief": "Trace origins and chronology."},
            {"id": "systems_analyst", "role": "systems analyst", "brief": "Trace mechanisms and trade-offs."},
        ]

    def _output(self, artifact_paths):
        experts = [item["id"] for item in self._roster()]
        run_ids = ["run-historian-1", "run-systems-analyst-1"]
        summaries = ["historian result", "systems result"]
        return {
            "execution_mode": "parallel_fanout",
            "fanout_round_index": 1,
            "subagent_expert_ids": experts,
            "subagent_run_ids": run_ids,
            "subagent_result_summaries": summaries,
            "subagent_artifact_paths": artifact_paths,
            "subagent_binding_records": [
                {
                    "expert_id": experts[0],
                    "subagent_run_id": run_ids[0],
                    "summary": summaries[0],
                    "artifact_path": artifact_paths[0],
                    "spawn_receipt": "spawn-historian-1",
                    "completion_receipt": "join-round-1",
                },
                {
                    "expert_id": experts[1],
                    "subagent_run_id": run_ids[1],
                    "summary": summaries[1],
                    "artifact_path": artifact_paths[1],
                    "spawn_receipt": "spawn-systems-analyst-1",
                    "completion_receipt": "join-round-1",
                },
            ],
            "fanout_complete": True,
        }

    def _raw_observation(self, artifact_paths):
        return {
            "status": "succeeded",
            "structured_output": self._output(artifact_paths),
            "tool_trace": [
                {
                    "tool_name": "host.subagent.spawn",
                    "status": "succeeded",
                    "phase": "spawn",
                    "expert_id": "historian",
                    "subagent_run_id": "run-historian-1",
                    "fanout_round_index": 1,
                    "receipt_id": "spawn-historian-1",
                },
                {
                    "tool_name": "host.subagent.spawn",
                    "status": "succeeded",
                    "phase": "spawn",
                    "expert_id": "systems_analyst",
                    "subagent_run_id": "run-systems-analyst-1",
                    "fanout_round_index": 1,
                    "receipt_id": "spawn-systems-analyst-1",
                },
                {
                    "tool_name": "host.subagent.wait",
                    "status": "completed",
                    "phase": "wait",
                    "expert_id": "historian",
                    "subagent_run_id": "run-historian-1",
                    "fanout_round_index": 1,
                    "receipt_id": "wait-historian-1",
                },
                {
                    "tool_name": "host.subagent.wait",
                    "status": "completed",
                    "phase": "wait",
                    "expert_id": "systems_analyst",
                    "subagent_run_id": "run-systems-analyst-1",
                    "fanout_round_index": 1,
                    "receipt_id": "wait-systems-analyst-1",
                },
                {
                    "tool_name": "host.subagent.join",
                    "status": "completed",
                    "phase": "join",
                    "expert_ids": ["historian", "systems_analyst"],
                    "subagent_run_ids": ["run-historian-1", "run-systems-analyst-1"],
                    "fanout_round_index": 1,
                    "receipt_id": "join-round-1",
                },
            ],
        }

    def test_flat_tool_trace_metadata_is_promoted_before_verifier_reads_it(self):
        observation = Observation.from_dict(
            {
                "run_id": "run-test",
                "step_id": "launch_expert_subagents",
                "status": "succeeded",
                "summary": "fan-out completed",
                "structured_output": {},
                "tool_trace": [
                    {
                        "tool_name": "host.subagent.spawn",
                        "status": "succeeded",
                        "phase": "spawn",
                        "expert_id": "historian",
                        "subagent_run_id": "run-historian-1",
                        "fanout_round_index": 1,
                        "receipt_id": "spawn-historian-1",
                        "operation_id": "host-op-1",
                    }
                ],
            }
        )

        self.assertEqual(
            observation.tool_trace[0].metadata,
            {
                "phase": "spawn",
                "expert_id": "historian",
                "subagent_run_id": "run-historian-1",
                "fanout_round_index": 1,
                "receipt_id": "spawn-historian-1",
                "operation_id": "host-op-1",
            },
        )

    def test_conflicting_flat_and_nested_trace_metadata_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "flat and nested metadata conflict"):
            Observation.from_dict(
                {
                    "run_id": "run-test",
                    "step_id": "launch_expert_subagents",
                    "status": "succeeded",
                    "summary": "conflicting trace",
                    "structured_output": {},
                    "tool_trace": [
                        {
                            "tool_name": "host.subagent.spawn",
                            "status": "succeeded",
                            "phase": "spawn",
                            "metadata": {"phase": "wait"},
                        }
                    ],
                }
            )

    def test_structured_bindings_and_batch_join_trace_pass(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_paths = ["reports/subagents/1/historian.md", "reports/subagents/1/systems.md"]
            for path, content in zip(artifact_paths, ("historian result", "systems result")):
                artifact = root / path
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text(content, encoding="utf-8")

            raw = self._raw_observation(artifact_paths)
            normalized_observation = Observation.from_dict(
                {
                    "run_id": "run-test",
                    "step_id": "launch_expert_subagents",
                    "status": raw["status"],
                    "summary": "fan-out completed",
                    "structured_output": raw["structured_output"],
                    "tool_trace": raw["tool_trace"],
                }
            ).to_dict()
            result = verifiers.verify_launch_expert_subagents(
                repo_root=str(root),
                run_id="run-test",
                step_id="launch_expert_subagents",
                observation=normalized_observation,
                state={
                    "expert_roster": self._roster(),
                    "round_index": 0,
                    "constraints": {"max_rounds": 8},
                    "subagent_run_history": [],
                },
            )

            self.assertTrue(result["passed"], result)

    def test_five_expert_batch_join_trace_passes_without_synthetic_receipts(self):
        roster = [
            {"id": f"expert-{index}", "role": f"role-{index}", "brief": f"Brief {index}."}
            for index in range(5)
        ]
        expert_ids = [record["id"] for record in roster]
        run_ids = [f"run-{expert_id}-1" for expert_id in expert_ids]
        summaries = [f"{expert_id} result" for expert_id in expert_ids]
        artifact_paths = [
            f"reports/subagents/1/{expert_id}.md" for expert_id in expert_ids
        ]
        bindings = [
            {
                "expert_id": expert_id,
                "subagent_run_id": run_id,
                "summary": summary,
                "artifact_path": artifact_path,
                "spawn_receipt": f"spawn-{run_id}",
                "completion_receipt": "join-round-1",
            }
            for expert_id, run_id, summary, artifact_path in zip(
                expert_ids, run_ids, summaries, artifact_paths
            )
        ]
        tool_trace = []
        for expert_id, run_id in zip(expert_ids, run_ids):
            tool_trace.extend(
                [
                    {
                        "tool_name": "host.subagent.spawn",
                        "status": "succeeded",
                        "phase": "spawn",
                        "expert_id": expert_id,
                        "subagent_run_id": run_id,
                        "fanout_round_index": 1,
                        "receipt_id": f"spawn-{run_id}",
                    },
                    {
                        "tool_name": "host.subagent.wait",
                        "status": "completed",
                        "phase": "wait",
                        "expert_id": expert_id,
                        "subagent_run_id": run_id,
                        "fanout_round_index": 1,
                        "receipt_id": f"wait-{run_id}",
                    },
                ]
            )
        tool_trace.append(
            {
                "tool_name": "host.subagent.join",
                "status": "completed",
                "phase": "join",
                "expert_ids": expert_ids,
                "subagent_run_ids": run_ids,
                "fanout_round_index": 1,
                "receipt_id": "join-round-1",
            }
        )
        output = {
            "execution_mode": "parallel_fanout",
            "fanout_round_index": 1,
            "subagent_expert_ids": expert_ids,
            "subagent_run_ids": run_ids,
            "subagent_result_summaries": summaries,
            "subagent_artifact_paths": artifact_paths,
            "subagent_binding_records": bindings,
            "fanout_complete": True,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for path in artifact_paths:
                artifact = root / path
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("grounded result", encoding="utf-8")
            observation = Observation.from_dict(
                {
                    "run_id": "run-test",
                    "step_id": "launch_expert_subagents",
                    "status": "succeeded",
                    "summary": "five-expert fan-out completed",
                    "structured_output": output,
                    "tool_trace": tool_trace,
                }
            ).to_dict()
            result = verifiers.verify_launch_expert_subagents(
                repo_root=str(root),
                run_id="run-test",
                step_id="launch_expert_subagents",
                observation=observation,
                state={
                    "expert_roster": roster,
                    "round_index": 0,
                    "constraints": {"max_rounds": 8},
                    "subagent_run_history": [],
                },
            )

        self.assertTrue(result["passed"], result)

    def test_separate_join_events_cannot_reuse_one_batch_receipt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_paths = ["reports/subagents/1/historian.md", "reports/subagents/1/systems.md"]
            for path in artifact_paths:
                artifact = root / path
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("grounded result", encoding="utf-8")

            raw = self._raw_observation(artifact_paths)
            raw["tool_trace"].append(
                {
                    "tool_name": "host.subagent.join",
                    "status": "completed",
                    "phase": "join",
                    "expert_id": "historian",
                    "subagent_run_id": "run-historian-1",
                    "fanout_round_index": 1,
                    "receipt_id": "join-round-1",
                }
            )
            observation = Observation.from_dict(
                {
                    "run_id": "run-test",
                    "step_id": "launch_expert_subagents",
                    "status": raw["status"],
                    "summary": "fan-out completed",
                    "structured_output": raw["structured_output"],
                    "tool_trace": raw["tool_trace"],
                }
            ).to_dict()
            result = verifiers.verify_launch_expert_subagents(
                repo_root=str(root),
                run_id="run-test",
                step_id="launch_expert_subagents",
                observation=observation,
                state={
                    "expert_roster": self._roster(),
                    "round_index": 0,
                    "constraints": {"max_rounds": 8},
                    "subagent_run_history": [],
                },
            )

            self.assertFalse(result["passed"])
            self.assertIn("one real join event", result["message"])

    def test_artifact_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_paths = ["reports/subagents/1/historian.md", "reports/subagents/1/systems.md"]
            for path in artifact_paths:
                artifact = root / path
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("x" * (1_048_576 + 1), encoding="utf-8")

            raw = self._raw_observation(artifact_paths)
            observation = Observation.from_dict(
                {
                    "run_id": "run-test",
                    "step_id": "launch_expert_subagents",
                    "status": raw["status"],
                    "summary": "fan-out completed",
                    "structured_output": raw["structured_output"],
                    "tool_trace": raw["tool_trace"],
                }
            ).to_dict()
            result = verifiers.verify_launch_expert_subagents(
                repo_root=str(root),
                run_id="run-test",
                step_id="launch_expert_subagents",
                observation=observation,
                state={
                    "expert_roster": self._roster(),
                    "round_index": 0,
                    "constraints": {"max_rounds": 8},
                    "subagent_run_history": [],
                },
            )

            self.assertFalse(result["passed"])
            self.assertIn("size limit", result["message"])

    def test_failed_fanout_records_attempt_without_promoting_canonical_history(self):
        state = workflow_state.make_initial_state(
            {
                "task_input": {"goal": "fanout contract test"},
                "context": {},
                "constraints": {},
            }
        )
        state.expert_roster = self._roster()
        state.round_index = 0
        output = self._output(["historian.md", "systems.md"])

        workflow_state.record_observation(
            state,
            current_step_id="launch_expert_subagents",
            observation={"status": "succeeded", "structured_output": output},
            verifier_result={"passed": False, "message": "trace mismatch", "details": {}},
        )

        self.assertEqual(state.subagent_run_history, [])
        self.assertEqual(len(state.subagent_attempt_history), 1)
        self.assertEqual(state.current_fanout_attempt["fanout_round_index"], 1)

        restored = workflow_state.deserialize_state(workflow_state.serialize_state(state))
        self.assertEqual(restored.subagent_run_history, [])
        self.assertEqual(len(restored.subagent_attempt_history), 1)
        self.assertEqual(restored.current_fanout_attempt["fanout_round_index"], 1)

    def test_successful_fanout_builds_canonical_history_without_model_echo(self):
        state = workflow_state.make_initial_state(
            {
                "task_input": {"goal": "fanout contract test"},
                "context": {},
                "constraints": {},
            }
        )
        state.expert_roster = self._roster()
        state.round_index = 0
        output = self._output(["historian.md", "systems.md"])

        workflow_state.record_observation(
            state,
            current_step_id="launch_expert_subagents",
            observation={"status": "succeeded", "structured_output": output},
            verifier_result={"passed": True, "message": "ok", "details": {}},
        )

        self.assertEqual(
            state.subagent_run_history,
            [
                {
                    "round_index": 1,
                    "expert_id": "historian",
                    "subagent_run_id": "run-historian-1",
                    "artifact_path": "historian.md",
                },
                {
                    "round_index": 1,
                    "expert_id": "systems_analyst",
                    "subagent_run_id": "run-systems-analyst-1",
                    "artifact_path": "systems.md",
                },
            ],
        )
        restored = workflow_state.deserialize_state(workflow_state.serialize_state(state))
        self.assertEqual(restored.subagent_run_history, state.subagent_run_history)
        self.assertEqual(restored.current_fanout_attempt, {})

    def test_model_cannot_echo_runtime_owned_history_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_paths = [
                "reports/subagents/1/historian.md",
                "reports/subagents/1/systems.md",
            ]
            for path in artifact_paths:
                artifact = root / path
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text("grounded result", encoding="utf-8")

            output = self._output(artifact_paths)
            output["subagent_run_history"] = []
            raw = self._raw_observation(artifact_paths)
            raw["structured_output"] = output
            observation = Observation.from_dict(
                {
                    "run_id": "run-test",
                    "step_id": "launch_expert_subagents",
                    "status": raw["status"],
                    "summary": "fan-out echoed runtime state",
                    "structured_output": raw["structured_output"],
                    "tool_trace": raw["tool_trace"],
                }
            ).to_dict()

            result = verifiers.verify_launch_expert_subagents(
                repo_root=str(root),
                run_id="run-test",
                step_id="launch_expert_subagents",
                observation=observation,
                state={
                    "expert_roster": self._roster(),
                    "round_index": 0,
                    "constraints": {"max_rounds": 8},
                    "subagent_run_history": [],
                },
            )

            self.assertFalse(result["passed"])
            self.assertIn("runtime-owned", result["message"])

    def test_persisted_history_requires_complete_contiguous_rounds(self):
        base = {
            "expert_roster": self._roster(),
            "round_index": 0,
            "constraints": {"max_rounds": 8},
        }
        incomplete = dict(base)
        incomplete["subagent_run_history"] = [
            {
                "round_index": 1,
                "expert_id": "historian",
                "subagent_run_id": "run-historian-1",
                "artifact_path": "reports/subagents/1/historian.md",
            }
        ]
        with self.assertRaisesRegex(ValueError, "must cover the persisted roster exactly"):
            workflow_state.deserialize_state(incomplete)

        skipped = dict(base)
        skipped["subagent_run_history"] = [
            {
                "round_index": 1,
                "expert_id": "historian",
                "subagent_run_id": "run-historian-1",
                "artifact_path": "reports/subagents/1/historian.md",
            },
            {
                "round_index": 1,
                "expert_id": "systems_analyst",
                "subagent_run_id": "run-systems-analyst-1",
                "artifact_path": "reports/subagents/1/systems.md",
            },
            {
                "round_index": 3,
                "expert_id": "historian",
                "subagent_run_id": "run-historian-3",
                "artifact_path": "reports/subagents/3/historian.md",
            },
            {
                "round_index": 3,
                "expert_id": "systems_analyst",
                "subagent_run_id": "run-systems-analyst-3",
                "artifact_path": "reports/subagents/3/systems.md",
            },
        ]
        with self.assertRaisesRegex(ValueError, "contiguous from round 1"):
            workflow_state.deserialize_state(skipped)


if __name__ == "__main__":
    unittest.main()
