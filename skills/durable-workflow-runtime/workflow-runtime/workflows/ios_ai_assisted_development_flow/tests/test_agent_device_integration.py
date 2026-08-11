import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


RUNTIME_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = RUNTIME_ROOT.parent
REPO_ROOT = SKILL_ROOT.parents[1]
for _lib_root in (REPO_ROOT / '.venv' / 'lib', SKILL_ROOT / '.venv' / 'lib', REPO_ROOT.parent / '.venv' / 'lib'):
    _site_packages = next(_lib_root.glob('python*/site-packages'), None)
    if _site_packages is not None and str(_site_packages) not in sys.path:
        sys.path.insert(0, str(_site_packages))
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))


from workflows.ios_ai_assisted_development_flow import contract as workflow_contract
from workflows.ios_ai_assisted_development_flow import graphbuilder_runtime, state as workflow_state


class AgentDeviceIntegrationTests(unittest.TestCase):
    def _make_state(self):
        return workflow_state.make_initial_state(
            {
                "task_input": {"goal": "agent-device integration regression"},
                "context": {
                    "agent_device_mode": "required",
                    "agent_device_expected_version": "0.4.0",
                    "agent_device_app_id": "com.zoom.Zoom",
                    "agent_device_artifact_path": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json",
                    "agent_device_device": "iPhone 15",
                    "agent_device_evidence_dir": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references",
                },
                "constraints": {},
            }
        )

    def _valid_required_output(self):
        return {
            "release_qa_verdict": "ship",
            "release_qa_summary": "Device smoke passed.",
            "release_qa_executed_checks": ["agent-device snapshot"],
            "release_qa_blocked_checks": [],
            "release_qa_risk_next_steps": ["Proceed to review."],
            "release_qa_artifacts": [],
            "release_qa_target_scope": "com.zoom.Zoom on iPhone 15",
            "agent_device_status": "succeeded",
            "agent_device_commands": [
                "agent-device prepare ios-runner --platform ios",
                "agent-device snapshot -i",
            ],
            "agent_device_artifacts": [
                "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/flowchart.md",
            ],
            "agent_device_execution_receipt": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json",
            "agent_device_cli_version": "0.4.0",
            "agent_device_observed_device": "iPhone 15",
            "agent_device_observed_app_id": "com.zoom.Zoom",
            "agent_device_runner_status": "succeeded",
        }

    def test_release_qa_promotes_and_round_trips_device_evidence(self):
        state = self._make_state()
        workflow_state.record_observation(
            state,
            current_step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "Required device QA passed.",
                "structured_output": {
                    "release_qa_verdict": "ship",
                    "release_qa_summary": "Device smoke passed.",
                    "release_qa_executed_checks": ["agent-device snapshot"],
                    "release_qa_blocked_checks": [],
                    "release_qa_risk_next_steps": ["Continue to review."],
                    "release_qa_artifacts": ["artifacts/release-qa/agent-device/session.json"],
                    "release_qa_target_scope": "com.zoom.Zoom on iPhone 15",
                    "agent_device_status": "succeeded",
                    "agent_device_commands": [
                        "agent-device prepare ios-runner --platform ios",
                        "agent-device snapshot -i",
                    ],
                    "agent_device_artifacts": [
                        "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-review.md",
                    ],
                    "agent_device_cli_version": "0.4.0",
                    "agent_device_observed_device": "iPhone 15",
                    "agent_device_observed_app_id": "com.zoom.Zoom",
                    "agent_device_runner_status": "succeeded",
                    "agent_device_execution_receipt": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json",
                },
            },
            verifier_result={"passed": True, "message": "ok", "details": {}},
        )

        self.assertEqual(state.agent_device_status, "succeeded")
        self.assertEqual(state.agent_device_commands, [
            "agent-device prepare ios-runner --platform ios",
            "agent-device snapshot -i",
        ])
        restored = workflow_state.deserialize_state(workflow_state.serialize_state(state))
        self.assertEqual(restored.agent_device_artifacts, [
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-review.md",
        ])
        self.assertEqual(restored.agent_device_cli_version, "0.4.0")
        self.assertEqual(restored.agent_device_observed_device, "iPhone 15")
        self.assertEqual(restored.agent_device_observed_app_id, "com.zoom.Zoom")
        self.assertEqual(restored.agent_device_runner_status, "succeeded")
        self.assertEqual(
            restored.agent_device_execution_receipt,
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json",
        )

    def test_failed_release_qa_does_not_promote_device_evidence(self):
        state = self._make_state()
        workflow_state.record_observation(
            state,
            current_step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "Device evidence failed its verifier.",
                "structured_output": {
                    "release_qa_verdict": "ship",
                    "release_qa_summary": "Invalid device evidence.",
                    "release_qa_executed_checks": ["agent-device snapshot"],
                    "release_qa_blocked_checks": [],
                    "release_qa_risk_next_steps": ["Rerun device QA."],
                    "release_qa_artifacts": [],
                    "release_qa_target_scope": "com.zoom.Zoom",
                    "agent_device_status": "succeeded",
                    "agent_device_commands": ["agent-device snapshot"],
                    "agent_device_artifacts": ["../unsafe.json"],
                },
            },
            verifier_result={"passed": False, "message": "unsafe artifact", "details": {}},
        )

        self.assertIsNone(state.agent_device_status)
        self.assertEqual(state.agent_device_commands, [])
        self.assertEqual(state.agent_device_artifacts, [])

    def test_prompt_context_carries_device_inputs_and_evidence(self):
        state = self._make_state()
        state.agent_device_status = "succeeded"
        state.agent_device_commands = ["agent-device snapshot -i"]
        state.agent_device_artifacts = [
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/flowchart.md"
        ]
        context = graphbuilder_runtime.build_template_context(
            step_id="run_agentic_release_qa",
            run_state=SimpleNamespace(
                graph_state=workflow_state.serialize_state(state),
                terminal_reason="",
                artifacts_degraded=False,
            ),
        )

        self.assertEqual(context["agent_device_mode"], "required")
        self.assertEqual(context["agent_device_expected_version"], "0.4.0")
        self.assertEqual(context["agent_device_status"], "succeeded")
        self.assertIn("flowchart.md", context["agent_device_artifacts"])

    def test_rendered_prompts_carry_device_evidence_into_qa_repair_and_final_summary(self):
        state = self._make_state()
        state.agent_device_status = "succeeded"
        state.agent_device_commands = ["agent-device prepare ios-runner --platform ios"]
        state.agent_device_artifacts = [
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/flowchart.md"
        ]
        state.agent_device_session = "qa-session-123"
        state.agent_device_replay_suite = "smoke.ad"
        state.agent_device_cli_version = "0.4.0"
        state.agent_device_observed_device = "iPhone 15"
        state.agent_device_observed_app_id = "com.zoom.Zoom"
        state.agent_device_runner_status = "succeeded"
        state.agent_device_execution_receipt = (
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json"
        )
        context = graphbuilder_runtime.build_template_context(
            step_id="run_agentic_release_qa",
            run_state=SimpleNamespace(
                graph_state=workflow_state.serialize_state(state),
                terminal_reason="",
                artifacts_degraded=False,
            ),
        )

        qa_prompt = graphbuilder_runtime.load_prompt_body(
            "run_agentic_release_qa", template_context=context
        )
        repair_prompt = graphbuilder_runtime.load_prompt_body(
            "repair_and_resume", template_context=context
        )
        final_prompt = graphbuilder_runtime.load_prompt_body(
            "finalize_delivery_summary", template_context=context
        )

        for prompt in (qa_prompt, repair_prompt, final_prompt):
            self.assertIn("qa-session-123", prompt)
            self.assertIn("smoke.ad", prompt)
            self.assertIn("flowchart.md", prompt)
            self.assertNotIn("{{agent_device_", prompt)
            self.assertIn("Agent-device observed CLI version:", prompt)
            self.assertIn("Agent-device execution receipt:", prompt)
        for prompt in (qa_prompt, repair_prompt):
            self.assertIn("Agent-device mode:", prompt)
        for value in (
            "0.4.0",
            "iPhone 15",
            "com.zoom.Zoom",
            "succeeded",
            "agent-device-receipt.json",
        ):
            self.assertIn(value, qa_prompt)
            self.assertIn(value, repair_prompt)
            self.assertIn(value, final_prompt)
        for value in (
            "required",
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json",
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references",
        ):
            self.assertIn(value, qa_prompt)
            self.assertIn(value, repair_prompt)
        self.assertIn("agent-device expected version", repair_prompt.lower())

    def test_device_session_and_replay_output_are_promoted(self):
        state = self._make_state()
        workflow_state.record_observation(
            state,
            current_step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "Required device QA passed.",
                "structured_output": {
                    "release_qa_verdict": "ship",
                    "release_qa_summary": "Device smoke passed.",
                    "release_qa_executed_checks": ["agent-device replay"],
                    "release_qa_blocked_checks": [],
                    "release_qa_risk_next_steps": ["Proceed to review."],
                    "release_qa_artifacts": [],
                    "release_qa_target_scope": "com.zoom.Zoom on iPhone 15",
                    "agent_device_status": "succeeded",
                    "agent_device_commands": [
                        "agent-device prepare ios-runner --platform ios",
                        "agent-device replay smoke.ad",
                    ],
                    "agent_device_artifacts": [
                        "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/flowchart.md",
                    ],
                    "agent_device_session": "qa-session-123",
                    "agent_device_replay_suite": "smoke.ad",
                    "agent_device_cli_version": "0.4.0",
                    "agent_device_observed_device": "iPhone 15",
                    "agent_device_observed_app_id": "com.zoom.Zoom",
                    "agent_device_runner_status": "succeeded",
                    "agent_device_execution_receipt": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json",
                },
            },
            verifier_result={"passed": True, "message": "ok", "details": {}},
        )
        self.assertEqual(state.agent_device_session, "qa-session-123")
        self.assertEqual(state.agent_device_replay_suite, "smoke.ad")
        self.assertEqual(state.agent_device_cli_version, "0.4.0")
        self.assertEqual(state.agent_device_observed_device, "iPhone 15")
        self.assertEqual(state.agent_device_observed_app_id, "com.zoom.Zoom")
        self.assertEqual(state.agent_device_runner_status, "succeeded")
        self.assertEqual(
            state.agent_device_execution_receipt,
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json",
        )

    def test_deserialize_rejects_malformed_device_state(self):
        with self.assertRaises(ValueError):
            workflow_state.deserialize_state({"agent_device_commands": "snapshot"})
        with self.assertRaises(ValueError):
            workflow_state.deserialize_state({"repair_blocked_attempts": "3"})
        with self.assertRaises(ValueError):
            workflow_state.deserialize_state(
                {"context": {"agent_device_app_id": {"bundle": "com.zoom.Zoom"}}}
            )
        with self.assertRaises(ValueError):
            workflow_state.deserialize_state({"agent_device_cli_version": 0.4})
        with self.assertRaises(ValueError):
            workflow_state.deserialize_state({"agent_device_execution_receipt": {"path": "receipt.json"}})

    def test_missing_verifier_preserves_return_stage_and_repair_payload(self):
        state = self._make_state()
        workflow_state.record_observation(
            state,
            current_step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "QA completed but the verifier result was unavailable.",
                "structured_output": {},
            },
            verifier_result=None,
        )
        self.assertEqual(state.return_stage_id, "run_agentic_release_qa")
        self.assertEqual(state.repair_context["repair_payload"]["category"], "verifier_missing")

    def test_required_device_rejects_runner_preparation_after_snapshot(self):
        from workflows.ios_ai_assisted_development_flow import verifiers

        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="agent-device-test-run",
            step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "Runner preparation was recorded too late.",
                "structured_output": {
                    "release_qa_verdict": "do_not_ship",
                    "release_qa_summary": "Invalid operation order.",
                    "release_qa_executed_checks": ["agent-device snapshot"],
                    "release_qa_blocked_checks": ["runner order"],
                    "release_qa_risk_next_steps": ["Prepare the runner first."],
                    "release_qa_artifacts": [],
                    "release_qa_target_scope": "com.zoom.Zoom on iPhone 15",
                    "agent_device_status": "succeeded",
                    "agent_device_commands": [
                        "agent-device snapshot -i",
                        "agent-device prepare ios-runner --platform ios",
                    ],
                    "agent_device_artifacts": [
                        "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/flowchart.md",
                    ],
                    "agent_device_cli_version": "0.4.0",
                    "agent_device_observed_device": "iPhone 15",
                    "agent_device_observed_app_id": "com.zoom.Zoom",
                    "agent_device_runner_status": "succeeded",
                    "agent_device_execution_receipt": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json",
                },
            },
            state={
                "context": {
                    "agent_device_mode": "required",
                    "agent_device_expected_version": "0.4.0",
                    "agent_device_app_id": "com.zoom.Zoom",
                    "agent_device_artifact_path": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json",
                    "agent_device_device": "iPhone 15",
                    "agent_device_evidence_dir": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references",
                }
            },
        )
        self.assertFalse(result["passed"])

    def test_required_device_rejects_symlinked_artifact_path(self):
        from workflows.ios_ai_assisted_development_flow import verifiers

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / ".tmp") as temp_dir:
            temp_root = Path(temp_dir)
            evidence_dir = temp_root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "real.json").write_text("{}", encoding="utf-8")
            (evidence_dir / "alias.json").symlink_to(evidence_dir / "real.json")
            evidence_relative = evidence_dir.relative_to(REPO_ROOT).as_posix()
            result = verifiers.verify_run_agentic_release_qa(
                repo_root=str(REPO_ROOT),
                run_id="agent-device-test-run",
                step_id="run_agentic_release_qa",
                observation={
                    "status": "succeeded",
                    "summary": "Device evidence used a symlinked artifact path.",
                    "structured_output": {
                        "release_qa_verdict": "do_not_ship",
                        "release_qa_summary": "Unsafe evidence path.",
                        "release_qa_executed_checks": ["agent-device snapshot"],
                        "release_qa_blocked_checks": ["unsafe path"],
                        "release_qa_risk_next_steps": ["Use a regular evidence file."],
                        "release_qa_artifacts": [],
                        "release_qa_target_scope": "com.zoom.Zoom on iPhone 15",
                        "agent_device_status": "succeeded",
                        "agent_device_commands": [
                            "agent-device prepare ios-runner --platform ios",
                            "agent-device snapshot",
                        ],
                        "agent_device_artifacts": [
                            f"{evidence_relative}/alias.json",
                        ],
                        "agent_device_cli_version": "0.4.0",
                        "agent_device_observed_device": "iPhone 15",
                        "agent_device_observed_app_id": "com.zoom.Zoom",
                        "agent_device_runner_status": "succeeded",
                        "agent_device_execution_receipt": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/agent-device-receipt.json",
                    },
                },
                state={
                    "context": {
                        "agent_device_mode": "required",
                        "agent_device_expected_version": "0.4.0",
                        "agent_device_app_id": "com.zoom.Zoom",
                        "agent_device_artifact_path": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json",
                        "agent_device_device": "iPhone 15",
                        "agent_device_evidence_dir": evidence_relative,
                    }
                },
            )
            self.assertFalse(result["passed"])

    def test_required_device_rejects_mismatched_host_observation(self):
        from workflows.ios_ai_assisted_development_flow import verifiers

        output = self._valid_required_output()
        output["agent_device_cli_version"] = "0.3.0"
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="agent-device-test-run",
            step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "The host reported an unexpected CLI version.",
                "structured_output": output,
            },
            state=workflow_state.serialize_state(self._make_state()),
        )
        self.assertFalse(result["passed"])

    def test_required_device_rejects_missing_evidence_file(self):
        from workflows.ios_ai_assisted_development_flow import verifiers

        output = self._valid_required_output()
        output["agent_device_artifacts"] = [
            "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/references/missing-agent-device.json",
        ]
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="agent-device-test-run",
            step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "The host reported an artifact that is not present.",
                "structured_output": output,
            },
            state=workflow_state.serialize_state(self._make_state()),
        )
        self.assertFalse(result["passed"])

    def test_required_device_accepts_open_handshake_before_runner_prepare(self):
        from workflows.ios_ai_assisted_development_flow import verifiers

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / ".tmp") as temp_dir:
            temp_root = Path(temp_dir)
            evidence_dir = temp_root / "evidence"
            evidence_dir.mkdir()
            (evidence_dir / "trace.json").write_text("{}", encoding="utf-8")
            evidence_relative = evidence_dir.relative_to(REPO_ROOT).as_posix()
            receipt_relative = f"{evidence_relative}/receipt.json"
            artifact_relative = f"{evidence_relative}/trace.json"
            commands = [
                "agent-device open --app com.zoom.Zoom",
                "agent-device prepare ios-runner --platform ios",
                "agent-device snapshot -i",
            ]
            Path(REPO_ROOT / receipt_relative).write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": "agent-device-open-run",
                        "status": "succeeded",
                        "cli_version": "0.4.0",
                        "device": "iPhone 15",
                        "app_id": "com.zoom.Zoom",
                        "runner_status": "succeeded",
                        "commands": commands,
                        "build_artifact": "skills/durable-workflow-runtime/workflow-runtime/workflows/ios_ai_assisted_development_flow/spec.json",
                        "artifacts": [artifact_relative],
                    }
                ),
                encoding="utf-8",
            )
            output = self._valid_required_output()
            output["agent_device_commands"] = commands
            output["agent_device_artifacts"] = [artifact_relative]
            output["agent_device_execution_receipt"] = receipt_relative
            open_state = self._make_state()
            open_state.context["agent_device_evidence_dir"] = evidence_relative
            result = verifiers.verify_run_agentic_release_qa(
                repo_root=str(REPO_ROOT),
                run_id="agent-device-open-run",
                step_id="run_agentic_release_qa",
                observation={
                    "status": "succeeded",
                    "summary": "Open handshake followed by runner preparation and snapshot.",
                    "structured_output": output,
                },
                state=workflow_state.serialize_state(open_state),
            )
            self.assertTrue(result["passed"])

    def test_required_device_rejects_receipt_from_another_run(self):
        from workflows.ios_ai_assisted_development_flow import verifiers

        output = self._valid_required_output()
        output["agent_device_commands"] = [
            "agent-device prepare ios-runner --platform ios",
            "agent-device replay smoke.ad",
        ]
        result = verifiers.verify_run_agentic_release_qa(
            repo_root=str(REPO_ROOT),
            run_id="agent-device-different-run",
            step_id="run_agentic_release_qa",
            observation={
                "status": "succeeded",
                "summary": "The receipt belongs to a different workflow run.",
                "structured_output": output,
            },
            state=workflow_state.serialize_state(self._make_state()),
        )
        self.assertFalse(result["passed"])

    def test_repair_prompt_context_carries_blocked_attempt_count(self):
        state = self._make_state()
        state.repair_blocked_attempts = 2
        context = graphbuilder_runtime.build_template_context(
            step_id="repair_and_resume",
            run_state=SimpleNamespace(
                graph_state=workflow_state.serialize_state(state),
                terminal_reason="",
                artifacts_degraded=False,
            ),
        )

        self.assertEqual(context["repair_blocked_attempts"], "2")

    def test_contract_declares_agent_device_supporting_route_and_outputs(self):
        contract = workflow_contract.get_step_contract("run_agentic_release_qa")
        route_skills = {route.skill for route in contract.skill_routing}
        self.assertIn("agent-device", route_skills)
        self.assertEqual(contract.output_schema["agent_device_status"], "string?")
        self.assertEqual(contract.output_schema["agent_device_commands"], "string[]?")
        self.assertEqual(contract.output_schema["agent_device_artifacts"], "string[]?")
        self.assertEqual(contract.output_schema["agent_device_cli_version"], "string?")
        self.assertEqual(contract.output_schema["agent_device_observed_device"], "string?")
        self.assertEqual(contract.output_schema["agent_device_observed_app_id"], "string?")
        self.assertEqual(contract.output_schema["agent_device_runner_status"], "string?")
        self.assertEqual(contract.output_schema["agent_device_execution_receipt"], "string?")


if __name__ == "__main__":
    unittest.main()
