from __future__ import annotations

import asyncio
import json
import os
import shlex
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = SKILL_ROOT / "workflow-runtime"
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))


class RuntimeHardeningTests(unittest.TestCase):
    def test_unlocked_concurrent_saves_have_atomic_compare_and_swap(self) -> None:
        from runtime.errors import StateConflictError
        from runtime.models import RunState
        from runtime.persistence import FileRunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileRunStateStore(tmpdir)
            initial = RunState(
                run_id="run_atomic_cas",
                workflow_id="demo-prompt-loop",
                workflow_version="v1",
                status="waiting_for_host",
                current_node="collect_context",
                graph_state={},
            )
            store.save(initial)
            original_load_path = store._load_path

            def slow_load_path(target):
                loaded = original_load_path(target)
                time.sleep(0.02)
                return loaded

            store._load_path = slow_load_path
            outcomes: list[object] = []
            barrier = threading.Barrier(3)

            def writer() -> None:
                candidate = RunState(
                    run_id="run_atomic_cas",
                    workflow_id="demo-prompt-loop",
                    workflow_version="v1",
                    status="waiting_for_host",
                    current_node="collect_context",
                    graph_state={},
                    revision=1,
                )
                barrier.wait()
                try:
                    store.save(candidate, expected_revision=0)
                except StateConflictError as exc:
                    outcomes.append(exc)
                else:
                    outcomes.append("saved")

            threads = [threading.Thread(target=writer) for _ in range(2)]
            for thread in threads:
                thread.start()
            barrier.wait()
            for thread in threads:
                thread.join(timeout=2)
            self.assertEqual(outcomes.count("saved"), 1)
            self.assertEqual(sum(isinstance(item, StateConflictError) for item in outcomes), 1)

    def test_retention_waits_for_run_lock_and_keeps_lock_inode(self) -> None:
        from runtime.persistence import FileRunStateStore
        from runtime.retention import RetentionPolicy, cleanup_expired_terminal_runs
        from runtime.models import RunState

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileRunStateStore(tmpdir)
            state = RunState(
                run_id="run_retention_lock",
                workflow_id="demo-prompt-loop",
                workflow_version="v1",
                status="done",
                current_node="finalize_summary",
                graph_state={},
                updated_at="2000-01-01T00:00:00Z",
            )
            store.save(state)
            cleanup_result: dict[str, object] = {}
            finished = threading.Event()

            def cleanup() -> None:
                cleanup_result.update(
                    cleanup_expired_terminal_runs(
                        tmpdir,
                        policy=RetentionPolicy(terminal_run_ttl_seconds=0),
                    )
                )
                finished.set()

            with store.lock(state.run_id):
                worker = threading.Thread(target=cleanup)
                worker.start()
                self.assertFalse(finished.wait(0.1))
            worker.join(timeout=2)
            self.assertTrue(finished.is_set())
            self.assertEqual(cleanup_result["removed_runs"], [state.run_id])
            self.assertTrue((store.runs_dir / f".{state.run_id}.json.lock").exists())

    def test_failed_terminal_run_rejects_new_resume(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine
        from runtime.errors import ProtocolError

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = GraphBuilderRuntimeEngine(tmpdir)
            started = engine.start(
                "demo-prompt-loop",
                {
                    "task_input": {"goal": "terminal guard"},
                    "context": {"repo_root": tmpdir},
                    "constraints": {},
                },
            )
            state = engine._store.load(started["run_id"])
            self.assertIsNotNone(state)
            state.status = "failed_terminal"
            engine._store.save(state, expected_revision=state.revision)
            with self.assertRaises(ProtocolError):
                engine.resume(
                    started["run_id"],
                    {
                        "run_id": started["run_id"],
                        "step_id": started["step_id"],
                        "status": "succeeded",
                        "summary": "must not run",
                        "structured_output": {
                            "runtime_exists": True,
                            "top_level_entries": [],
                            "missing_paths": [],
                        },
                    },
                )

    def test_observation_replay_retention_is_bounded(self) -> None:
        from runtime.models import RunState

        state = RunState(
            run_id="run_replay_retention",
            workflow_id="demo-prompt-loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        for index in range(100):
            state.record_observation_replay(
                f"attempt-{index}",
                f"fingerprint-{index}",
                {"kind": "yield", "step_id": "collect_context", "index": index},
            )
        self.assertLessEqual(len(state.observation_replays), 64)
        self.assertNotIn("attempt-0", state.observation_replays)
        self.assertEqual(
            state.observation_replays["attempt-99"]["response"]["index"],
            99,
        )

    def test_bridge_rejects_oversized_input_before_json_load(self) -> None:
        import bridge

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "oversized.json"
            path.write_bytes(b"{" + b"x" * (512 * 1024) + b"}")
            with self.assertRaisesRegex(ValueError, "exceeds"):
                bridge._load_json_object(
                    path,
                    required_fields=set(),
                    max_bytes=512 * 1024,
                )

    def test_artifact_reference_duplicate_is_validated_before_deduplication(self) -> None:
        from runtime.models import RunState

        artifact_id = "a" * 64
        reference = {
            "artifact_id": artifact_id,
            "relative_path": "artifacts/result.md",
            "size_bytes": 12,
            "sha256": artifact_id,
            "media_type": "text/markdown",
            "created_at": "2026-08-07T00:00:00Z",
            "kind": "result",
        }
        malformed_duplicate = {**reference, "relative_path": "../escape"}
        payload = RunState(
            run_id="run_duplicate_artifact",
            workflow_id="demo-prompt-loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
            artifact_refs=[reference, malformed_duplicate],
        ).to_dict()
        with self.assertRaises(ValueError):
            RunState.from_dict(payload)

    def test_python_verifier_result_is_normalized_and_bounded(self) -> None:
        from runtime.errors import VerifierExecutionError
        from runtime.verifier_runner import _normalize_verifier_result

        self.assertEqual(
            _normalize_verifier_result({"passed": True, "message": " ok ", "details": {}}),
            {"passed": True, "message": "ok", "details": {}},
        )
        with self.assertRaises(VerifierExecutionError):
            _normalize_verifier_result({"passed": 1, "message": "bad", "details": {}})
        with self.assertRaises(VerifierExecutionError):
            _normalize_verifier_result(
                {"passed": True, "message": "bad", "details": {"output": "x" * (64 * 1024)}}
            )

    def test_run_state_store_rejects_path_escape_and_symlink_escape(self) -> None:
        from runtime.models import RunState
        from runtime.persistence import FileRunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            store = FileRunStateStore(repo_root)
            with self.assertRaises(ValueError):
                store.load("../escape")
            with self.assertRaises(ValueError):
                store.load(str((repo_root / "absolute").resolve()))

            runs_dir = repo_root / ".durable-workflow-runtime" / "runs"
            runs_dir.mkdir(parents=True)
            outside = repo_root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            (runs_dir / "run_symlink.json").symlink_to(outside)
            with self.assertRaises(ValueError):
                store.load("run_symlink")

            state = RunState(
                run_id="run_safe",
                workflow_id="demo-prompt-loop",
                workflow_version="v1",
                status="waiting_for_host",
                current_node="collect_context",
                graph_state={},
            )
            saved_path = store.save(state)
            self.assertEqual(saved_path.parent.resolve(), runs_dir.resolve())
            self.assertEqual(saved_path.stat().st_mode & 0o077, 0)

            runtime_root = repo_root / ".durable-workflow-runtime"
            shutil.rmtree(runtime_root)
            outside_runtime = repo_root / "outside-runtime"
            outside_runtime.mkdir()
            runtime_root.symlink_to(outside_runtime, target_is_directory=True)
            with self.assertRaises(ValueError):
                FileRunStateStore(repo_root)
            from runtime.artifacts import ArtifactStore
            from runtime.telemetry import RuntimeTelemetry

            with self.assertRaises(ValueError):
                ArtifactStore(repo_root)
            with self.assertRaises(ValueError):
                RuntimeTelemetry(repo_root)

    def test_run_state_store_uses_compare_and_swap_and_migrates_legacy_state(self) -> None:
        from runtime.errors import StateConflictError
        from runtime.models import RunState
        from runtime.persistence import FileRunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = FileRunStateStore(tmpdir)
            state = RunState(
                run_id="run_cas",
                workflow_id="demo-prompt-loop",
                workflow_version="v1",
                status="waiting_for_host",
                current_node="collect_context",
                graph_state={},
            )
            store.save(state)
            first = store.load("run_cas")
            second = store.load("run_cas")
            assert first is not None
            assert second is not None
            first.revision = 1
            store.save(first, expected_revision=0)
            second.revision = 1
            with self.assertRaises(StateConflictError):
                store.save(second, expected_revision=0)

            legacy = state.to_dict()
            for field_name in (
                "state_version",
                "revision",
                "observation_replays",
                "history_degraded",
                "accepted_steps",
                "max_steps",
                "terminal_reason",
            ):
                legacy.pop(field_name, None)
            migrated = RunState.from_dict(legacy)
            self.assertEqual(migrated.state_version, 3)
            self.assertEqual(migrated.revision, 0)
            self.assertEqual(migrated.accepted_steps, 0)

    def test_observation_with_same_id_replays_exact_response(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            engine = GraphBuilderRuntimeEngine(repo_root)
            started = engine.start(
                "demo-prompt-loop",
                {
                    "task_input": {"goal": "idempotency"},
                    "context": {"repo_root": str(repo_root)},
                    "constraints": {},
                },
            )
            observation = {
                "run_id": started["run_id"],
                "step_id": "collect_context",
                "observation_id": "attempt-1",
                "status": "succeeded",
                "summary": "runtime scaffold checked",
                "structured_output": {
                    "runtime_exists": True,
                    "top_level_entries": [],
                    "missing_paths": [],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            }
            first = engine.resume(started["run_id"], observation)
            second = engine.resume(started["run_id"], observation)
            self.assertEqual(second, first)

    def test_observation_id_conflict_is_rejected(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine
        from runtime.errors import ProtocolError

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            engine = GraphBuilderRuntimeEngine(repo_root)
            started = engine.start(
                "demo-prompt-loop",
                {
                    "task_input": {"goal": "idempotency conflict"},
                    "context": {"repo_root": str(repo_root)},
                    "constraints": {},
                },
            )
            observation = {
                "run_id": started["run_id"],
                "step_id": "collect_context",
                "observation_id": "attempt-1",
                "status": "succeeded",
                "summary": "first payload",
                "structured_output": {
                    "runtime_exists": True,
                    "top_level_entries": [],
                    "missing_paths": [],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            }
            engine.resume(started["run_id"], observation)
            observation["summary"] = "different payload"
            with self.assertRaises(ProtocolError):
                engine.resume(started["run_id"], observation)

    def test_schema_validation_rejects_unknown_types_and_supports_numbers(self) -> None:
        from runtime.errors import WorkflowExecutionError
        from runtime.validation import validate_schema_value

        with self.assertRaises(WorkflowExecutionError):
            validate_schema_value("value", "not_a_schema_type", "value")
        validate_schema_value(1.5, "number", "value")
        validate_schema_value(
            [{"id": "expert-1", "score": 1.5}],
            {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id": "string", "score": "number"},
                },
            },
            "value",
        )
        with self.assertRaises(WorkflowExecutionError):
            validate_schema_value(float("nan"), "number", "value")

    def test_module_loader_rejects_import_path_injection(self) -> None:
        from runtime.errors import WorkflowExecutionError
        from runtime.module_loader import load_workflow_modules

        with self.assertRaisesRegex(WorkflowExecutionError, "invalid workflow_id"):
            load_workflow_modules("demo-prompt-loop.__class__")

    def test_observation_payload_limits_reject_large_raw_output(self) -> None:
        from runtime.errors import ObservationValidationError
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            engine = GraphBuilderRuntimeEngine(repo_root)
            started = engine.start(
                "demo-prompt-loop",
                {
                    "task_input": {"goal": "payload limit"},
                    "context": {"repo_root": str(repo_root)},
                    "constraints": {},
                },
            )
            observation = {
                "run_id": started["run_id"],
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "payload limit",
                "structured_output": {
                    "runtime_exists": True,
                    "top_level_entries": [],
                    "missing_paths": [],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "x" * (1024 * 1024),
            }
            with self.assertRaises(ObservationValidationError):
                engine.resume(started["run_id"], observation)

    def test_observation_model_rejects_non_string_raw_output_and_non_object_error(self) -> None:
        from runtime.models import Observation

        base = {
            "run_id": "run_observation_shape",
            "step_id": "collect_context",
            "status": "succeeded",
            "summary": "shape validation",
            "structured_output": {},
        }
        with self.assertRaises(ValueError):
            Observation.from_dict({**base, "raw_output": {}})
        with self.assertRaises(ValueError):
            Observation.from_dict({**base, "error": "not-an-error-object"})

    def test_prompt_envelope_has_a_runtime_owned_size_limit(self) -> None:
        from runtime.models import PromptEnvelope

        with self.assertRaises(ValueError):
            PromptEnvelope(
                run_id="run_prompt_limit",
                step_id="collect_context",
                prompt="x" * (512 * 1024 + 1),
                intent="collect_context",
                expected_artifact="bounded prompt",
                resume_instructions="Return a valid observation.",
            )

    def test_runtime_max_steps_ends_degraded_instead_of_yielding_another_step(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            engine = GraphBuilderRuntimeEngine(repo_root)
            started = engine.start(
                "demo-prompt-loop",
                {
                    "task_input": {"goal": "budget"},
                    "context": {"repo_root": str(repo_root)},
                    "constraints": {"max_steps": 1},
                },
            )
            response = engine.resume(
                started["run_id"],
                {
                    "run_id": started["run_id"],
                    "step_id": "collect_context",
                    "status": "blocked",
                    "summary": "access is unavailable",
                    "structured_output": {"blocked_reason": "missing access", "error_message": ""},
                    "artifacts": [],
                    "error": None,
                    "tool_trace": [],
                    "raw_output": "",
                },
            )

            self.assertEqual(response["kind"], "done")
            self.assertEqual(response["step_id"], "finalize_summary")
            self.assertTrue(response["final_prompt_envelope"]["metadata"]["degraded"])
            self.assertEqual(
                response["final_prompt_envelope"]["metadata"]["terminal_reason"],
                "max_steps_exceeded",
            )

    def test_budget_terminalizes_workflow_graph_state_when_schema_is_present(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        payload = {
            "current_stage_id": "repair_and_resume",
            "terminal_reason": None,
            "return_stage_id": "run_brainstorming",
            "repair_context": {"source_stage_id": "repair_and_resume"},
            "repair_category": "blocked",
            "repair_summary": "Needs external input.",
            "repair_requirements": ["approval"],
            "repair_evidence": ["blocked"],
            "repair_transition_reason": "blocked",
            "repair_blocked_attempts": 3,
        }
        terminal = GraphBuilderRuntimeEngine._terminalize_workflow_graph_state(
            payload,
            "finalize_delivery_summary",
        )
        self.assertEqual(terminal["current_stage_id"], "finalize_delivery_summary")
        self.assertEqual(terminal["terminal_reason"], "max_steps_exceeded")
        self.assertIsNone(terminal["return_stage_id"])
        self.assertEqual(terminal["repair_context"], {})
        self.assertEqual(terminal["repair_requirements"], [])
        self.assertEqual(terminal["repair_blocked_attempts"], 0)

    def test_async_engine_wrapper_works_inside_event_loop(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            engine = GraphBuilderRuntimeEngine(repo_root)

            async def run() -> dict:
                started = await engine.start_async(
                    "demo-prompt-loop",
                    {
                        "task_input": {"goal": "async"},
                        "context": {"repo_root": str(repo_root)},
                        "constraints": {},
                    },
                )
                return await engine.resume_async(
                    started["run_id"],
                    {
                        "run_id": started["run_id"],
                        "step_id": "collect_context",
                        "status": "blocked",
                        "summary": "access is unavailable",
                        "structured_output": {
                            "blocked_reason": "missing access",
                            "error_message": "",
                        },
                        "artifacts": [],
                        "error": None,
                        "tool_trace": [],
                        "raw_output": "",
                    },
                )

            response = asyncio.run(run())
            self.assertEqual(response["kind"], "yield")
            self.assertEqual(response["step_id"], "request_missing_access")

    def test_shell_verifier_rejects_shell_metacharacters(self) -> None:
        from runtime.errors import VerifierExecutionError
        from runtime.module_loader import load_workflow_modules
        from runtime.models import Observation, RunState
        from runtime.verifier_runner import run_step_verifier
        from workflows.common.contracts import StepVerifier

        modules = load_workflow_modules("demo-prompt-loop")
        run_state = RunState(
            run_id="run_shell_safe",
            workflow_id="demo-prompt-loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        observation = Observation.from_dict(
            {
                "run_id": "run_shell_safe",
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "shell safety",
                "structured_output": {},
            }
        )
        with self.assertRaises(VerifierExecutionError):
            run_step_verifier(
                repo_root=SKILL_ROOT,
                modules=modules,
                verifier=StepVerifier(
                    kind="shell_command",
                    ref="true; touch injected-marker",
                ),
                run_state=run_state,
                observation=observation,
            )
        self.assertFalse((SKILL_ROOT / "injected-marker").exists())

    def test_shell_verifier_caps_output_and_reports_truncation(self) -> None:
        from runtime.module_loader import load_workflow_modules
        from runtime.models import Observation, RunState
        from runtime.verifier_runner import run_step_verifier
        from workflows.common.contracts import StepVerifier

        modules = load_workflow_modules("demo-prompt-loop")
        run_state = RunState(
            run_id="run_shell_output",
            workflow_id="demo-prompt-loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        observation = Observation.from_dict(
            {
                "run_id": "run_shell_output",
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "shell output limit",
                "structured_output": {},
            }
        )
        result = run_step_verifier(
            repo_root=SKILL_ROOT,
            modules=modules,
            verifier=StepVerifier(
                kind="shell_command",
                ref="python3 -c 'print(\"x\" * 200000)'",
            ),
            run_state=run_state,
            observation=observation,
        )
        self.assertTrue(result["passed"])
        self.assertTrue(result["details"]["output_truncated"])
        self.assertLessEqual(len(result["details"]["stdout"].encode()), 64 * 1024)

    def test_shell_verifier_timeout_terminates_process_group(self) -> None:
        from runtime.module_loader import load_workflow_modules
        from runtime.models import Observation, RunState
        from runtime.verifier_runner import run_step_verifier
        from workflows.common.contracts import StepVerifier

        modules = load_workflow_modules("demo-prompt-loop")
        run_state = RunState(
            run_id="run_shell_timeout",
            workflow_id="demo-prompt-loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        observation = Observation.from_dict(
            {
                "run_id": "run_shell_timeout",
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "shell timeout",
                "structured_output": {},
            }
        )
        started_at = time.monotonic()
        result = run_step_verifier(
            repo_root=SKILL_ROOT,
            modules=modules,
            verifier=StepVerifier(
                kind="shell_command",
                ref="python3 -c 'import time; time.sleep(10)'",
                timeout_seconds=0.1,
            ),
            run_state=run_state,
            observation=observation,
        )

        self.assertFalse(result["passed"])
        self.assertTrue(result["details"]["timed_out"])
        self.assertLess(time.monotonic() - started_at, 3)

    def test_history_compacts_state_snapshots_and_applies_retention(self) -> None:
        from runtime.models import HistoryEntry, RunState

        state = RunState(
            run_id="run_history",
            workflow_id="demo-prompt-loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={"large": "state"},
        )
        state.append_history(
            HistoryEntry.create(
                event="verifier_failed",
                payload={
                    "state": {"secret_token": "do-not-persist"},
                    "details": {"large": "x" * 100_000},
                },
            )
        )
        payload = state.history[0].payload
        self.assertNotIn("state", payload)
        self.assertTrue(state.history_degraded)
        self.assertLess(len(json.dumps(payload).encode()), 20_000)

        for index in range(300):
            state.append_history(HistoryEntry.create(event=f"event_{index}"))
        self.assertLessEqual(len(state.history), 256)

    def test_history_redacts_sensitive_values_inside_compact_diagnostics(self) -> None:
        from runtime.models import HistoryEntry, RunState

        state = RunState(
            run_id="run_history_redaction",
            workflow_id="demo-prompt-loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        state.append_history(
            HistoryEntry.create(
                event="observation_received",
                payload={
                    "summary": "verifier saw token=secret-value",
                    "details": {"message": "Bearer another-secret"},
                },
            )
        )

        serialized = json.dumps(state.history[0].payload, ensure_ascii=False)
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("another-secret", serialized)

    def test_artifact_store_keeps_bounded_checksum_references(self) -> None:
        from runtime.artifacts import ArtifactStore
        from runtime.errors import ArtifactStoreError

        with tempfile.TemporaryDirectory() as tmpdir:
            store = ArtifactStore(tmpdir, max_artifact_bytes=1024, max_bytes_per_run=2048)
            reference = store.put_json(
                "run_artifacts",
                {"summary": "externalized", "secret_token": "not in state"},
                kind="observation",
            )
            self.assertEqual(store.read_bytes(reference), b'{"summary":"externalized","secret_token":"not in state"}')
            duplicate = store.put_json(
                "run_artifacts",
                {"summary": "externalized", "secret_token": "not in state"},
                kind="observation",
            )
            self.assertEqual(duplicate.artifact_id, reference.artifact_id)
            self.assertEqual(len(store.list_references("run_artifacts")), 1)
            with self.assertRaises(ArtifactStoreError):
                store.read_bytes({**reference.to_dict(), "relative_path": "../outside.bin"})

    def test_engine_externalizes_observation_artifacts_and_records_metrics(self) -> None:
        from runtime.artifacts import ArtifactStore
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine
        from runtime.models import RunState
        from runtime.persistence import FileRunStateStore
        from runtime.telemetry import RuntimeTelemetry

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            engine = GraphBuilderRuntimeEngine(repo_root)
            started = engine.start(
                "demo-prompt-loop",
                {
                    "task_input": {"goal": "artifact ref"},
                    "context": {"repo_root": str(repo_root)},
                    "constraints": {},
                },
            )
            engine.resume(
                started["run_id"],
                {
                    "run_id": started["run_id"],
                    "step_id": "collect_context",
                    "status": "blocked",
                    "summary": "needs access",
                    "structured_output": {
                        "blocked_reason": "missing access",
                        "error_message": "",
                    },
                    "artifacts": [{"receipt": "compact"}],
                    "error": None,
                    "tool_trace": [],
                    "raw_output": "raw diagnostic token=secret-value",
                },
            )
            state = FileRunStateStore(repo_root).load(started["run_id"])
            self.assertIsInstance(state, RunState)
            assert state is not None
            self.assertEqual(len(state.artifact_refs), 1)
            self.assertEqual(len(state.diagnostic_refs), 1)
            self.assertFalse(state.artifacts_degraded)
            stored_diagnostic = ArtifactStore(repo_root).read_bytes(state.diagnostic_refs[0])
            stored_artifact = ArtifactStore(repo_root).read_bytes(state.artifact_refs[0])
            self.assertNotIn(b"secret-value", stored_diagnostic)
            self.assertNotIn(b"not in state", stored_artifact)
            events = RuntimeTelemetry(repo_root).read_events()
            self.assertGreaterEqual(len(events), 2)
            self.assertIn("resume_accepted", {event["event"] for event in events})
            self.assertTrue(all("raw_output" not in event for event in events))

    def test_canonical_transport_maps_partial_and_rejects_duplicate_receipts(self) -> None:
        from runtime.errors import TransportValidationError
        from runtime.transport import canonicalize_native_receipts

        receipts = [
            {
                "receipt_id": "receipt-1",
                "tool_name": "agent.wait",
                "trace_id": "trace-1",
                "phase": "wait",
                "status": "partial",
                "summary": "one child timed out",
                "partial_failure": True,
                "artifact_refs": [],
            }
        ]
        trace, status = canonicalize_native_receipts(
            receipts,
            run_id="run_transport",
            step_id="fanout",
            base_status="succeeded",
        )
        self.assertEqual(status, "partial")
        self.assertEqual(trace[0]["metadata"]["trace_id"], "trace-1")
        missing_join_trace, missing_join_status = canonicalize_native_receipts(
            [
                {
                    "receipt_id": "receipt-join",
                    "tool_name": "agent.join",
                    "trace_id": "trace-join",
                    "phase": "join",
                    "status": "succeeded",
                    "summary": "",
                }
            ],
            run_id="run_transport",
            step_id="fanout",
            base_status="succeeded",
        )
        self.assertEqual(missing_join_status, "partial")
        self.assertEqual(missing_join_trace[0]["metadata"]["missing_fields"], ["join_id"])
        with self.assertRaises(TransportValidationError):
            canonicalize_native_receipts(
                receipts + receipts,
                run_id="run_transport",
                step_id="fanout",
                base_status="succeeded",
            )
        with self.assertRaises(TransportValidationError):
            canonicalize_native_receipts(
                [
                    {
                        **receipts[0],
                        "metadata": {"phase": "join"},
                    }
                ],
                run_id="run_transport",
                step_id="fanout",
                base_status="succeeded",
            )

    def test_host_io_artifact_reference_is_bounded_and_checksumed(self) -> None:
        import host_io

        with tempfile.TemporaryDirectory() as tmpdir:
            reference = host_io.write_artifact(
                tmpdir,
                "run_host_artifact",
                "reports/result.md",
                "# result",
                media_type="text/markdown",
            )
            self.assertEqual(host_io.read_artifact(tmpdir, "run_host_artifact", "reports/result.md"), b"# result")
            self.assertEqual(reference["size_bytes"], len(b"# result"))
            self.assertEqual(len(reference["sha256"]), 64)

    def test_explicit_retention_removes_only_old_terminal_run_and_artifacts(self) -> None:
        from datetime import UTC, datetime, timedelta

        import host_io
        from runtime.artifacts import ArtifactStore
        from runtime.models import RunState
        from runtime.persistence import FileRunStateStore
        from runtime.retention import RetentionPolicy, cleanup_expired_terminal_runs

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            store = FileRunStateStore(repo_root)
            state = RunState(
                run_id="run_expired",
                workflow_id="demo-prompt-loop",
                workflow_version="v1",
                status="done",
                current_node="finalize_summary",
                graph_state={},
            )
            state.updated_at = (datetime.now(UTC) - timedelta(days=10)).isoformat().replace("+00:00", "Z")
            store.save(state)
            ArtifactStore(repo_root).put_bytes("run_expired", b"old")
            host_io.ensure_run_layout(repo_root, "run_expired")
            host_io.write_artifact(repo_root, "run_expired", "notes/old.txt", "old")
            result = cleanup_expired_terminal_runs(
                repo_root,
                policy=RetentionPolicy(terminal_run_ttl_seconds=1),
            )
            self.assertEqual(result["removed_runs"], ["run_expired"])
            self.assertEqual(result["removed_host_io"], ["run_expired"])
            self.assertIsNone(store.load("run_expired"))
            self.assertFalse((repo_root / ".durable-workflow-runtime" / "artifacts" / "run_expired").exists())
            self.assertFalse((repo_root / ".durable-workflow-runtime" / "host-io" / "run_expired").exists())


if __name__ == "__main__":
    unittest.main()
