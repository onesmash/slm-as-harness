import json
import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace


SKILL_ROOT = Path(__file__).resolve().parents[1]
PACK_SKILL_ROOT = SKILL_ROOT / "pack"
REGISTER_SKILL_ROOT = SKILL_ROOT / "register"
DELETE_SKILL_ROOT = SKILL_ROOT / "delete"
INJECT_SKILL_ROOT = SKILL_ROOT / "inject"
WORKFLOW_CREATOR_SKILL_ROOT = SKILL_ROOT / "workflow-creator"
REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_ROOT = SKILL_ROOT / "workflow-runtime"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"
DEFAULT_BINDING_CONFIG_PATH = SKILL_ROOT / "workflow-binding.json"
BINDING_CONFIG_ENV_VAR = "DURABLE_WORKFLOW_RUNTIME_BINDING_CONFIG_PATH"
IOS_GOALS_WORKFLOW_DIR = RUNTIME_ROOT / "workflows" / "ios_goals"
SUPERPOWERS_DELIVERY_CHAIN_WORKFLOW_DIR = RUNTIME_ROOT / "workflows" / "superpowers_delivery_chain"
IOS_CLIENT_AI_DELIVERY_WORKFLOW_DIR = RUNTIME_ROOT / "workflows" / "ios_client_ai_delivery"
MATT_POCOCK_ENGINEERING_DELIVERY_WORKFLOW_DIR = (
    RUNTIME_ROOT / "workflows" / "matt_pocock_engineering_delivery"
)
BRIDGE_PATH = SKILL_ROOT / "scripts" / "bridge.py"
HOST_IO_PATH = SKILL_ROOT / "scripts" / "host_io.py"
PACK_PATH = PACK_SKILL_ROOT / "scripts" / "pack.py"
REGISTER_PATH = REGISTER_SKILL_ROOT / "scripts" / "register.py"
DELETE_PATH = DELETE_SKILL_ROOT / "scripts" / "delete_workflow.py"
INJECT_PATH = INJECT_SKILL_ROOT / "scripts" / "inject.py"
CREATE_WORKFLOW_PATH = WORKFLOW_CREATOR_SKILL_ROOT / "scripts" / "create_workflow.py"
WORKSPACE_ROOT = REPO_ROOT / ".durable-workflow-runtime"
VENV_SITE_PACKAGES = next(
    (REPO_ROOT / ".venv" / "lib").glob("python*/site-packages"),
    None,
)


if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if VENV_SITE_PACKAGES is not None and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_SITE_PACKAGES))


def binding_config_path() -> Path:
    override = os.environ.get(BINDING_CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_BINDING_CONFIG_PATH


class DurableWorkflowRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        shutil.rmtree(WORKSPACE_ROOT, ignore_errors=True)
        self._binding_config_env_backup = os.environ.get(BINDING_CONFIG_ENV_VAR)
        self._binding_config_path = WORKSPACE_ROOT / "config" / "workflow-binding.json"
        os.environ[BINDING_CONFIG_ENV_VAR] = str(self._binding_config_path)
        self._manifest_backups = {
            path: path.read_text(encoding="utf-8")
            for path in sorted((RUNTIME_ROOT / "workflows").glob("*/manifest.json"))
            if path.exists()
        }
        self._lockfile_backups = {
            path: path.read_text(encoding="utf-8")
            for path in sorted((RUNTIME_ROOT / "workflows").glob("*/.workflow-lock.json"))
            if path.exists()
        }
        self._project_skill_backups: dict[Path, str | None] = {}
        self._hidden_project_skill_dirs: list[tuple[Path, Path]] = []
        self._write_binding_config(
            {
                "default_workflow_id": "demo_prompt_loop",
                "workflows": [
                    {
                        "workflow_id": "demo_prompt_loop",
                        "flow_description": "demo",
                    },
                    *(
                        [
                            {
                                "workflow_id": "superpowers_delivery_chain",
                                "flow_description": "superpowers",
                            }
                        ]
                        if SUPERPOWERS_DELIVERY_CHAIN_WORKFLOW_DIR.is_dir()
                        else []
                    ),
                    *(
                        [
                            {
                                "workflow_id": "ios_goals",
                                "flow_description": "ios goals",
                            }
                        ]
                        if IOS_GOALS_WORKFLOW_DIR.is_dir()
                        else []
                    ),
                    *(
                        [
                            {
                                "workflow_id": "ios_client_ai_delivery",
                                "flow_description": "ios client ai delivery",
                            }
                        ]
                        if IOS_CLIENT_AI_DELIVERY_WORKFLOW_DIR.is_dir()
                        else []
                    ),
                    {
                        "workflow_id": "academic_research_pipeline",
                        "flow_description": "academic research pipeline",
                    },
                    *(
                        [
                            {
                                "workflow_id": "matt_pocock_engineering_delivery",
                                "flow_description": "matt pocock engineering delivery",
                            }
                        ]
                        if MATT_POCOCK_ENGINEERING_DELIVERY_WORKFLOW_DIR.is_dir()
                        else []
                    ),
                ],
            }
        )

    def tearDown(self) -> None:
        if self._binding_config_env_backup is None:
            os.environ.pop(BINDING_CONFIG_ENV_VAR, None)
        else:
            os.environ[BINDING_CONFIG_ENV_VAR] = self._binding_config_env_backup

        for path, text in self._manifest_backups.items():
            path.write_text(text, encoding="utf-8")
        for path in sorted((RUNTIME_ROOT / "workflows").glob("*/.workflow-lock.json")):
            if path not in self._lockfile_backups:
                path.unlink(missing_ok=True)
        for path, text in self._lockfile_backups.items():
            path.write_text(text, encoding="utf-8")

        for path, text in self._project_skill_backups.items():
            if text is None:
                if path.parent.exists():
                    self._remove_path(path.parent)
            else:
                path.write_text(text, encoding="utf-8")

        for original_dir, hidden_dir in reversed(self._hidden_project_skill_dirs):
            if original_dir.exists():
                self._remove_path(original_dir)
            if hidden_dir.exists():
                hidden_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(hidden_dir), str(original_dir))

    def _load_skill_host(self):
        from adapters import skill_host

        return skill_host

    def _load_create_workflow_module(self):
        spec = importlib.util.spec_from_file_location(
            "create_workflow_under_test",
            CREATE_WORKFLOW_PATH,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _write_binding_config(self, payload: dict | str) -> None:
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        self._binding_config_path.parent.mkdir(parents=True, exist_ok=True)
        self._binding_config_path.write_text(text, encoding="utf-8")

    def _extract_placeholders(self, path: Path) -> set[str]:
        from workflows.common.prompting import PLACEHOLDER_PATTERN

        return set(PLACEHOLDER_PATTERN.findall(path.read_text(encoding="utf-8")))

    def _workflow_manifest_path(self, workflow_id: str) -> Path:
        return RUNTIME_ROOT / "workflows" / workflow_id / "manifest.json"

    def _workflow_lockfile_path(self, workflow_id: str) -> Path:
        return RUNTIME_ROOT / "workflows" / workflow_id / ".workflow-lock.json"

    def _contract_start_input_schema(self, workflow_id: str) -> dict:
        from runtime.module_loader import load_workflow_modules

        modules = load_workflow_modules(workflow_id)
        return modules["contract"].WORKFLOW_INPUT_CONTRACT.to_start_input_schema()

    def _remove_path(self, path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
            return
        if path.exists():
            shutil.rmtree(path)

    def _pending_host_io_file(self, filename: str) -> Path:
        import host_io

        pending_dir = host_io.pending_start_request_path(REPO_ROOT, "test").parent
        return pending_dir / filename

    def _write_host_io_start_request(
        self,
        payload: dict,
        *,
        workflow_id: str = "demo_prompt_loop",
    ) -> tuple[Path, Path]:
        import host_io

        request_file = host_io.pending_start_request_path(REPO_ROOT, workflow_id)
        response_file = request_file.with_name(f"{workflow_id}-start-response.json")
        request_file.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return request_file, response_file

    def _write_test_flow_archive(self, path: Path, *, workflow_id: str) -> None:
        package_manifest = {
            "schema_version": 1,
            "package_type": "durable-workflow-runtime.flow",
            "container": "zip",
            "workflow_id": workflow_id,
            "binding_entry": "binding-entry.json",
            "workflow_root": "workflow/",
            "workflow_manifest": "workflow/manifest.json",
            "start_input_schema": {
                "task_input": {"goal": "string"},
                "context": {"repo_root": "string"},
                "constraints": {},
            },
        }
        binding_entry = {
            "workflow_id": workflow_id,
            "flow_description": "registered test workflow",
            "start_input_schema": package_manifest["start_input_schema"],
        }
        workflow_manifest = {
            "schema_version": 1,
            "workflow_id": workflow_id,
            "description": "Registered test workflow.",
            "start_input_schema": package_manifest["start_input_schema"],
            "dependencies": [],
        }
        workflow_lock = {
            "schema_version": 1,
            "workflow_id": workflow_id,
            "installed": [],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "package-manifest.json",
                json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n",
            )
            archive.writestr(
                "binding-entry.json",
                json.dumps(binding_entry, ensure_ascii=False, indent=2) + "\n",
            )
            archive.writestr(
                "workflow/manifest.json",
                json.dumps(workflow_manifest, ensure_ascii=False, indent=2) + "\n",
            )
            archive.writestr(
                "workflow/.workflow-lock.json",
                json.dumps(workflow_lock, ensure_ascii=False, indent=2) + "\n",
            )
            archive.writestr("workflow/contract.py", "WORKFLOW_ID = 'registered_test'\n")
            archive.writestr("workflow/prompts/collect_context.md", "Collect context.\n")

    def _write_test_runtime_binding(self, runtime_root: Path) -> None:
        (runtime_root / "workflow-runtime" / "workflows").mkdir(parents=True)
        (runtime_root / "workflow-binding.json").write_text(
            json.dumps(
                {
                    "default_workflow_id": "pdf-processing",
                    "workflows": [
                        {
                            "workflow_id": "pdf-processing",
                            "flow_description": "Extract PDF text, fill forms, merge files. Use when handling PDFs.",
                        },
                        {
                            "workflow_id": "data-analysis",
                            "flow_description": "Analyze datasets, generate charts, and create summary reports.",
                        },
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_test_creator_runtime(self, runtime_root: Path) -> None:
        workflows_root = runtime_root / "workflow-runtime" / "workflows"
        templates_root = runtime_root / "workflow-runtime" / "templates"
        workflows_root.mkdir(parents=True)
        templates_root.mkdir(parents=True)
        shutil.copytree(
            RUNTIME_ROOT / "templates" / "workflow_skeleton",
            templates_root / "workflow_skeleton",
        )
        (runtime_root / "workflow-binding.json").write_text(
            json.dumps(
                {
                    "default_workflow_id": "demo_prompt_loop",
                    "workflows": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _create_creator_workflow_scaffold(
        self,
        runtime_root: Path,
        *,
        workflow_id: str,
        flow_description: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKFLOW_PATH),
                "--runtime-skill-root",
                str(runtime_root),
                "--workflow-id",
                workflow_id,
                "--flow-description",
                flow_description,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def _regenerate_creator_workflow_from_spec(
        self,
        runtime_root: Path,
        *,
        workflow_id: str,
        spec_payload: dict,
    ) -> subprocess.CompletedProcess[str]:
        workflow_dir = runtime_root / "workflow-runtime" / "workflows" / workflow_id
        (workflow_dir / "spec.json").write_text(
            json.dumps(spec_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKFLOW_PATH),
                "--runtime-skill-root",
                str(runtime_root),
                "--workflow-id",
                workflow_id,
                "--force",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def _custom_verifier_workflow_spec(
        self,
        *,
        workflow_id: str,
        requirements: list[dict],
    ) -> dict:
        return {
            "workflow_id": workflow_id,
            "flow_description": "Exercise custom verifier incremental regeneration.",
            "stages": [
                {
                    "step_id": "review_design_doc",
                    "intent": "review_design_doc",
                    "expected_artifact": "design review summary",
                    "prompt": "Review the design document and capture the result.",
                    "done_when": ["The design review result is captured"],
                    "output_schema": {
                        "design_doc_path": "string",
                        "design_ready": "boolean",
                    },
                    "failure_schema": {"blocked_reason": "string?"},
                    "custom_verifier_requirements": requirements,
                }
            ],
        }

    def _install_project_skill(self, skill_name: str, *, root: str = ".agents/skills") -> None:
        skill_dir = REPO_ROOT / root / skill_name
        skill_file = skill_dir / "SKILL.md"
        if skill_dir.is_symlink() and skill_file.exists():
            return
        if skill_file not in self._project_skill_backups:
            self._project_skill_backups[skill_file] = (
                skill_file.read_text(encoding="utf-8") if skill_file.exists() else None
            )
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(
            "---\n"
            f"name: {skill_name}\n"
            f"description: Test fixture for {skill_name}.\n"
            "---\n\n"
            f"# {skill_name}\n",
            encoding="utf-8",
        )

    def _hide_project_skill(self, skill_name: str) -> None:
        hidden_root = WORKSPACE_ROOT / "hidden-project-skills"
        for relative_root in (".agents/skills", ".claude/skills"):
            skill_dir = REPO_ROOT / relative_root / skill_name
            if not skill_dir.exists():
                continue
            hidden_dir = hidden_root / relative_root.replace("/", "__") / skill_name
            hidden_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(skill_dir), str(hidden_dir))
            self._hidden_project_skill_dirs.append((skill_dir, hidden_dir))

    def _start_request(self) -> dict:
        return {
            "task_input": {
                "goal": "检查 skill bundle 自带的 workflow-runtime 骨架是否存在"
            },
            "context": {"repo_root": str(REPO_ROOT)},
            "constraints": {"max_steps": 5},
        }

    def test_start_returns_collect_context_yield(self) -> None:
        skill_host = self._load_skill_host()

        response = skill_host.start(str(REPO_ROOT), self._start_request())

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "collect_context")
        self.assertEqual(
            response["prompt_envelope"]["step_id"],
            "collect_context",
        )
        self.assertIn(str(RUNTIME_ROOT), response["prompt_envelope"]["prompt"])

    def test_start_uses_workflow_binding_config(self) -> None:
        skill_host = self._load_skill_host()
        self._write_binding_config(
            {
                "default_workflow_id": "demo_prompt_loop",
                "workflows": [
                    {
                        "workflow_id": "demo_prompt_loop",
                        "flow_description": "demo",
                    }
                ],
            }
        )

        response = skill_host.start(str(REPO_ROOT), self._start_request())

        self.assertEqual(
            response["prompt_envelope"]["metadata"]["workflow_id"],
            "demo_prompt_loop",
        )

    def test_start_registers_workflow_start_input_schema_in_binding_config(self) -> None:
        skill_host = self._load_skill_host()
        self._write_binding_config(
            {
                "default_workflow_id": "demo_prompt_loop",
                "workflows": [
                    {
                        "workflow_id": "demo_prompt_loop",
                        "flow_description": "demo",
                    }
                ],
            }
        )

        skill_host.start(str(REPO_ROOT), self._start_request())

        binding_payload = json.loads(binding_config_path().read_text(encoding="utf-8"))
        workflow_entry = binding_payload["workflows"][0]
        self.assertEqual(
            workflow_entry["start_input_schema"],
            self._contract_start_input_schema("demo_prompt_loop"),
        )

    def test_start_rejects_binding_start_input_schema_that_drifted_from_contract(self) -> None:
        skill_host = self._load_skill_host()
        self._write_binding_config(
            {
                "default_workflow_id": "demo_prompt_loop",
                "workflows": [
                    {
                        "workflow_id": "demo_prompt_loop",
                        "flow_description": "demo",
                        "start_input_schema": {
                            "task_input": {"unexpected": "string"},
                            "context": {},
                            "constraints": {},
                        },
                    }
                ],
            }
        )

        with self.assertRaises(skill_host.BootstrapError):
            skill_host.start(str(REPO_ROOT), self._start_request())

    def test_start_missing_workflow_binding_config_raises_bootstrap_error(self) -> None:
        skill_host = self._load_skill_host()
        binding_config_path().unlink(missing_ok=True)

        with self.assertRaises(skill_host.BootstrapError):
            skill_host.start(str(REPO_ROOT), self._start_request())

    def test_start_invalid_workflow_binding_config_raises_bootstrap_error(self) -> None:
        skill_host = self._load_skill_host()
        self._write_binding_config({"default_workflow_id": "missing_workflow"})

        with self.assertRaises(skill_host.BootstrapError):
            skill_host.start(str(REPO_ROOT), self._start_request())

    def test_start_explicit_workflow_id_requires_catalog_membership(self) -> None:
        skill_host = self._load_skill_host()
        self._write_binding_config(
            {
                "default_workflow_id": "demo_prompt_loop",
                "workflows": [
                    {
                        "workflow_id": "demo_prompt_loop",
                        "flow_description": "demo only",
                    }
                ],
            }
        )

        with self.assertRaises(skill_host.BootstrapError):
            skill_host.start(
                str(REPO_ROOT),
                self._start_request(),
                workflow_id="superpowers_delivery_chain",
            )

    def test_preflight_registers_workflow_start_input_schema_in_manifest(self) -> None:
        skill_host = self._load_skill_host()
        manifest_path = self._workflow_manifest_path("demo_prompt_loop")
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_payload.pop("start_input_schema", None)
        manifest_path.write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        response = skill_host.preflight(str(REPO_ROOT), "demo_prompt_loop")

        self.assertEqual(response["status"], "ready")
        updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(
            updated_manifest["start_input_schema"],
            self._contract_start_input_schema("demo_prompt_loop"),
        )

    def test_preflight_rejects_manifest_start_input_schema_that_drifted_from_contract(self) -> None:
        skill_host = self._load_skill_host()
        manifest_path = self._workflow_manifest_path("demo_prompt_loop")
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_payload["start_input_schema"] = {
            "task_input": {"unexpected": "string"},
            "context": {},
            "constraints": {},
        }
        manifest_path.write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        response = skill_host.preflight(str(REPO_ROOT), "demo_prompt_loop")

        self.assertEqual(response["status"], "invalid_manifest")
        self.assertIn("start_input_schema", response["message"])

    def test_published_manifest_start_input_schemas_match_contracts(self) -> None:
        for manifest_path in sorted((RUNTIME_ROOT / "workflows").glob("*/manifest.json")):
            workflow_id = manifest_path.parent.name
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest_payload["start_input_schema"],
                self._contract_start_input_schema(workflow_id),
            )

    def test_graphbuilder_runtime_builds_graph(self) -> None:
        from workflows.demo_prompt_loop import graphbuilder_runtime

        prototype_graph = graphbuilder_runtime.build_graph()

        self.assertEqual(prototype_graph.name, "demo_prompt_loop_graphbuilder_runtime")
        self.assertTrue(callable(getattr(prototype_graph, "run", None)))

    def test_graphbuilder_runtime_blocked_routes_to_request_missing_access(self) -> None:
        from workflows.demo_prompt_loop import graphbuilder_runtime, state as workflow_state

        result = graphbuilder_runtime.run_transition_preview(
            state=workflow_state.make_initial_state(self._start_request()),
            current_step_id="collect_context",
            observation={
                "status": "blocked",
                "summary": "无法读取目标目录。",
            },
            verifier_result=None,
        )

        self.assertEqual(result.step_id, "request_missing_access")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(result.history_entry.event, "branch_selected")
        self.assertEqual(result.history_entry.node, "collect_context")
        self.assertEqual(result.history_entry.step_id, "collect_context")
        self.assertEqual(
            result.trace_payload,
            {
                "next_node": "request_missing_access",
                "branch_kind": "repair",
                "reason": "host reported blocked while collecting runtime context",
            },
        )
        self.assertEqual(result.history_entry.payload, result.trace_payload)

    def test_workflow_skeleton_prompts_only_use_supported_placeholders(self) -> None:
        prompts_dir = (
            SKILL_ROOT / "workflow-runtime" / "templates" / "workflow_skeleton" / "prompts"
        )
        expected = {
            "run_primary_stage.md": {"workflow_goal"},
            "request_unblocking_input.md": {
                "workflow_goal",
                "repair_category",
                "repair_summary",
                "repair_requirements",
                "repair_evidence",
            },
            "repair_and_resume.md": {
                "workflow_goal",
                "return_stage_id",
                "repair_category",
                "repair_summary",
                "repair_requirements",
                "repair_evidence",
            },
            "finalize_summary.md": {"workflow_goal"},
        }

        actual = {
            path.name: self._extract_placeholders(path)
            for path in sorted(prompts_dir.glob("*.md"))
        }

        self.assertEqual(actual, expected)

    def test_demo_prompts_match_available_template_context(self) -> None:
        from workflows.demo_prompt_loop import graphbuilder_runtime

        prompts_dir = SKILL_ROOT / "workflow-runtime" / "workflows" / "demo_prompt_loop" / "prompts"
        start_context_keys = {"runtime_root_path"}
        runtime_context_keys = set(
            graphbuilder_runtime.build_template_context(
                step_id="finalize_summary",
                run_state=SimpleNamespace(graph_state={}),
            ).keys()
        )

        for path in sorted(prompts_dir.glob("*.md")):
            placeholders = self._extract_placeholders(path)
            if path.name == "collect_context.md":
                self.assertTrue(
                    placeholders.issubset(start_context_keys),
                    f"{path.name} uses placeholders not provided by start context: {placeholders - start_context_keys}",
                )
            else:
                self.assertTrue(
                    placeholders.issubset(runtime_context_keys),
                    f"{path.name} uses placeholders not provided by build_template_context: {placeholders - runtime_context_keys}",
                )

    def test_workflow_authoring_guide_links_placeholder_and_blueprint_references(self) -> None:
        guide = (
            SKILL_ROOT / "references" / "workflow-authoring-guide.md"
        ).read_text(encoding="utf-8")
        refs_index = (SKILL_ROOT / "references" / "index.md").read_text(encoding="utf-8")

        self.assertIn("prompt-placeholder-spec.md", guide)
        self.assertIn("spec.json", guide)
        self.assertIn("workflow blueprint", guide)
        self.assertIn("keep it aligned", guide)
        self.assertIn("prompt-placeholder-spec.md", refs_index)

    def test_skill_entrypoint_avoids_repo_specific_install_path(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertNotIn(".codex/skills/durable-workflow-runtime/", skill_md)
        self.assertIn("references/index.md", skill_md)

    def test_skill_entrypoint_discourages_runtime_internal_reads_by_default(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        refs_index = (SKILL_ROOT / "references" / "index.md").read_text(encoding="utf-8")

        self.assertIn("Do not inspect `verifiers.py`", skill_md)
        self.assertIn("Default interface docs", skill_md)
        self.assertIn("Internal authoring/debugging only", skill_md)
        self.assertIn("Do not open runtime", refs_index)
        self.assertIn("Internal authoring/debugging docs", refs_index)

    def test_skill_entrypoint_keeps_execution_protocol_details_in_spokes(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

        self.assertNotIn("workflow-runtime/workflows/<workflow_id>/", skill_md)
        self.assertIn("--workflow-id", skill_md)
        self.assertIn("final_prompt_envelope", skill_md)
        self.assertIn("references/workflow-selection-spec.md", skill_md)
        self.assertIn("references/host-loop.md", skill_md)
        self.assertIn("references/observation-format.md", skill_md)

    def test_skill_description_avoids_runtime_model_type_names(self) -> None:
        skill_md = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        header = skill_md.split("---", 2)[1]

        self.assertNotIn("PromptEnvelope", header)
        self.assertNotIn("Observation", header)
        self.assertNotIn("pack", header)
        self.assertNotIn(".flow", header)
        self.assertIn("start/resume", header)
        self.assertIn("bridge", header)

    def test_pack_reference_documents_pack_surface(self) -> None:
        pack_skill = (PACK_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        pack_spec = (PACK_SKILL_ROOT / "references" / "pack-cli-spec.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("name: durable-workflow-runtime:pack", pack_skill)
        self.assertIn("references/pack-cli-spec.md", pack_skill)
        self.assertIn("durable-workflow-runtime:pack", pack_spec)
        self.assertIn("scripts/pack.py", pack_spec)
        self.assertIn(".flow", pack_spec)
        self.assertIn("<pack-skill-root>", pack_spec)

    def test_register_reference_documents_register_surface(self) -> None:
        register_skill = (REGISTER_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        register_spec = (
            REGISTER_SKILL_ROOT / "references" / "register-cli-spec.md"
        ).read_text(encoding="utf-8")

        self.assertIn("name: durable-workflow-runtime:register", register_skill)
        self.assertIn("references/register-cli-spec.md", register_skill)
        self.assertIn("durable-workflow-runtime:register", register_spec)
        self.assertIn("scripts/register.py", register_spec)
        self.assertIn("workflow-binding.json", register_spec)
        self.assertIn("<register-skill-root>", register_spec)
        self.assertIn("../inject/scripts/inject.py", register_skill)
        self.assertIn("../inject/scripts/inject.py", register_spec)
        self.assertIn("AGENTS.md", register_spec)
        self.assertIn("CLAUDE.md", register_spec)
        self.assertIn("workflow:<workflow_id>", register_skill)
        self.assertIn("workflow-shortcuts/<workflow_id>/SKILL.md", register_spec)

    def test_delete_reference_documents_delete_surface(self) -> None:
        delete_skill = (DELETE_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        delete_spec = (
            DELETE_SKILL_ROOT / "references" / "delete-cli-spec.md"
        ).read_text(encoding="utf-8")

        self.assertIn("name: durable-workflow-runtime:delete", delete_skill)
        self.assertIn("references/delete-cli-spec.md", delete_skill)
        self.assertIn("durable-workflow-runtime:delete", delete_spec)
        self.assertIn("scripts/delete_workflow.py", delete_spec)
        self.assertIn("workflow-binding.json", delete_spec)
        self.assertIn("--confirm <workflow_id>", delete_spec)
        self.assertIn("--new-default-workflow-id", delete_spec)
        self.assertIn("--clear-default", delete_spec)
        self.assertIn("../inject/scripts/inject.py", delete_skill)
        self.assertIn("../inject/scripts/inject.py", delete_spec)
        self.assertIn("AGENTS.md", delete_spec)
        self.assertIn("CLAUDE.md", delete_spec)
        self.assertIn("workflow:<workflow_id>", delete_skill)
        self.assertIn("workflow-shortcuts/<workflow_id>/", delete_spec)

    def test_inject_reference_documents_inject_surface(self) -> None:
        inject_skill = (INJECT_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        inject_spec = (
            INJECT_SKILL_ROOT / "references" / "inject-cli-spec.md"
        ).read_text(encoding="utf-8")

        self.assertIn("name: durable-workflow-runtime:inject", inject_skill)
        self.assertIn("references/inject-cli-spec.md", inject_skill)
        self.assertIn("durable-workflow-runtime:inject", inject_spec)
        self.assertIn("scripts/inject.py", inject_spec)
        self.assertIn("AGENTS.md", inject_spec)
        self.assertIn("CLAUDE.md", inject_spec)
        self.assertIn("<!-- durable-workflow-runtime:start -->", inject_spec)

    def test_workflow_creator_reference_documents_creator_surface(self) -> None:
        creator_skill = (WORKFLOW_CREATOR_SKILL_ROOT / "SKILL.md").read_text(
            encoding="utf-8"
        )
        creator_spec = (
            WORKFLOW_CREATOR_SKILL_ROOT / "references" / "workflow-creator-cli-spec.md"
        ).read_text(encoding="utf-8")

        self.assertIn("name: durable-workflow-runtime:workflow-creator", creator_skill)
        self.assertIn("scripts/create_workflow.py", creator_skill)
        self.assertIn("workflow-authoring-guide.md", creator_skill)
        self.assertIn("durable-workflow-runtime:workflow-creator", creator_spec)
        self.assertIn("workflow_skeleton", creator_spec)
        self.assertIn("workflow-binding.json", creator_spec)
        self.assertIn("--flow-description", creator_spec)
        self.assertIn("--force", creator_spec)
        self.assertIn("contract.py", creator_spec)
        self.assertIn("policy.py", creator_spec)
        self.assertIn("spec.json", creator_skill)
        self.assertIn("spec_blueprint_file", creator_spec)
        self.assertIn("workflow blueprint", creator_spec)
        self.assertIn("workflow:<workflow_id>", creator_skill)
        self.assertIn("workflow-shortcuts/<workflow_id>/SKILL.md", creator_spec)
        self.assertIn("Do not keep a second checked-in workflow spec", creator_spec)
        self.assertIn(
            "workflow-runtime/workflows/<workflow_id>/tests/test_workflow.py",
            creator_skill,
        )
        self.assertIn(
            "workflow-runtime/workflows/<workflow_id>/tests/test_workflow.py",
            creator_spec,
        )
        self.assertIn("core runtime", creator_skill)
        self.assertIn("test file", creator_skill)
        self.assertIn("bridge/runtime/pack/register/inject tests", creator_spec)
        self.assertIn("That review should start from", creator_skill)
        self.assertIn("spec-first semantic review", creator_spec)
        self.assertIn("Start by reading `spec.json`", creator_spec)
        self.assertIn("faithful implementation of that blueprint", creator_spec)
        self.assertIn("Generated Policy Evaluation Order", creator_spec)
        self.assertIn("Declarative Field Quick Reference", creator_spec)
        self.assertIn("stages[].outcome_routes", creator_spec)
        self.assertIn("stages[].stage_kind", creator_spec)
        self.assertIn("recovery_return_node", creator_spec)
        self.assertIn("stages[].verifier_templates", creator_spec)
        self.assertIn("stages[].custom_verifier_requirements", creator_spec)
        self.assertIn("Do not declare the same", creator_spec)
        self.assertIn("prefers promoted state over start input", creator_spec)
        self.assertIn("Shared recovery helpers", creator_spec)
        self.assertIn("`return_stage_id` on success", creator_spec)
        self.assertIn("default structural tests", creator_spec)
        self.assertIn("business-specific failure recovery", creator_skill)
        self.assertIn("Use `transitions` for normal business branches", creator_skill)
        self.assertIn("Use `verifier_templates` for common complex checks", creator_skill)
        self.assertIn("custom_verifier_requirements", creator_skill)
        self.assertIn("authoring pass can generate concrete `verifiers.py` scaffolds", creator_skill)
        self.assertIn("stable shared-module helpers", creator_skill)
        self.assertIn("same-file helper layers", creator_skill)
        self.assertIn("implementation_surface", creator_skill)
        self.assertIn("hint_pseudocode", creator_skill)
        self.assertIn("test_intent", creator_skill)
        self.assertIn("explicitly ask the", creator_skill)
        self.assertIn("user for permission", creator_skill)
        self.assertIn("subagent-backed agent review pass", creator_skill)
        self.assertIn("stop and request authorization", creator_skill)
        self.assertIn("subagent-backed review pass", creator_spec)
        self.assertIn("requirement-scoped custom verifier scaffolds", creator_spec)
        self.assertIn("implementation_surface", creator_spec)
        self.assertIn("hint_pseudocode", creator_spec)
        self.assertIn("test_intent", creator_spec)
        self.assertIn("wait for consent", creator_spec)
        self.assertIn("report the workflow as blocked", creator_spec)
        self.assertIn("prompt-focused pass", creator_skill)
        self.assertIn("verifier-focused pass", creator_skill)
        self.assertIn("contract-focused pass", creator_skill)
        self.assertIn("graph/runtime-flow pass", creator_skill)
        self.assertIn("prompt review", creator_spec)
        self.assertIn("verifier review", creator_spec)
        self.assertIn("contract review", creator_spec)
        self.assertIn("graph/runtime-flow", creator_spec)

    def test_workflow_creator_stage_prompts_follow_prompt_asset_template(self) -> None:
        create_workflow = self._load_create_workflow_module()
        prompt = create_workflow._stage_prompt_text(
            {
                "prompt": "Use `example-skill` and `example-reviewer` to prepare and review the example workflow stage.",
                "skill_routing": [
                    {
                        "skill": "example-skill",
                        "operations": ["example preparation"],
                        "file_patterns": ["*.md"],
                        "usage_notes": ["Use for example stage preparation."],
                    },
                    {
                        "skill": "example-reviewer",
                        "operations": ["example review"],
                        "file_patterns": ["*.md"],
                        "usage_notes": ["Use for example stage review."],
                    }
                ],
                "prompt_sections": {
                    "stage_goal": "Prepare the example workflow stage.",
                    "context": ["Input path: {{input_path}}"],
                    "boundaries": ["Do not implement unrelated changes."],
                    "blocked_conditions": ["If the input path is missing, return `blocked`."],
                },
            }
        )

        self.assertTrue(
            prompt.startswith(
                "Use `example-skill` and `example-reviewer` to prepare and review the example workflow stage.\n\n"
            )
        )
        self.assertIn("Stage Context:\n\n- Input path: {{input_path}}", prompt)
        self.assertNotIn("Workflow goal: `{{workflow_goal}}`", prompt)
        self.assertIn("- Input path: {{input_path}}", prompt)
        self.assertNotIn("\nTasks:\n\n1. Read the input.", prompt)
        self.assertIn("\nStage Boundaries:\n\n- Do not implement unrelated changes.", prompt)
        self.assertIn(
            "\nBlocked Conditions:\n\n- If the input path is missing, return `blocked`.",
            prompt,
        )
        self.assertNotIn("阶段上下文", prompt)
        self.assertNotIn("需要完成", prompt)

    def test_workflow_creator_stage_prompts_omit_tasks_for_non_skill_stages(self) -> None:
        create_workflow = self._load_create_workflow_module()
        prompt = create_workflow._stage_prompt_text(
            {
                "prompt": "Prepare the internal execution plan for this workflow stage.",
                "skill_routing": [],
                "prompt_sections": {
                    "stage_goal": "Prepare the internal execution plan.",
                    "context": ["Input path: {{input_path}}"],
                    "boundaries": ["Do not implement unrelated changes."],
                    "blocked_conditions": ["If the input path is missing, return `blocked`."],
                },
            }
        )

        self.assertNotIn("\nTasks:\n\n1. Read the input.", prompt)

    def test_workflow_creator_prompt_context_prefers_promoted_state_over_start_input(self) -> None:
        create_workflow = self._load_create_workflow_module()

        lines = create_workflow._graph_template_context_update_lines(
            {
                "start_input_schema": {
                    "task_input": {"change_id": "string"},
                    "context": {},
                    "constraints": {},
                },
                "stages": [
                    {
                        "step_id": "collect_context",
                        "state_updates": [
                            {
                                "state_key": "change_id",
                                "output_key": "change_id",
                                "kind": "string",
                            }
                        ],
                    }
                ],
            }
        )

        rendered = "\n".join(lines)
        self.assertIn('"change_id": _format_prompt_value(state.change_id),', rendered)
        self.assertNotIn('task_input_values.get("change_id")', rendered)

    def test_workflow_creator_shared_recovery_helpers_require_return_stage_id(self) -> None:
        create_workflow = self._load_create_workflow_module()
        policy_text = create_workflow._render_policy_py(
            {
                "workflow_id": "example_workflow",
                "final_step_id": "finalize_summary",
                "stages": [
                    {
                        "step_id": "collect_context",
                        "stage_kind": "main",
                        "outcome_routes": [],
                        "repair_conditions": [],
                        "transitions": [],
                    }
                ],
            }
        )

        self.assertIn('return_stage_id = state.get("return_stage_id")', policy_text)
        self.assertIn('reason="cannot resume because the next recovery target is missing"', policy_text)
        self.assertNotIn('next_node=state.get("return_stage_id") or', policy_text)

    def test_workflow_creator_generated_regression_tests_include_structural_defaults(self) -> None:
        create_workflow = self._load_create_workflow_module()
        generated = create_workflow._render_regression_tests_py(
            {
                "workflow_id": "example_workflow",
                "start_input_schema": {
                    "task_input": {"change_id": "string"},
                    "context": {},
                    "constraints": {},
                },
                "stages": [
                    {
                        "step_id": "collect_context",
                        "stage_kind": "main",
                        "state_updates": [
                            {
                                "state_key": "change_id",
                                "output_key": "change_id",
                                "kind": "string",
                            }
                        ],
                    }
                ],
                "final_step_id": "finalize_summary",
                "regression_tests": [],
            }
        )

        self.assertIn("test_generated_request_unblocking_input_resumes_to_return_stage", generated)
        self.assertIn("test_generated_request_unblocking_input_without_return_stage_stays_put", generated)
        self.assertIn("test_generated_request_unblocking_input_returns_to_repair_owner", generated)
        self.assertIn("test_generated_repair_and_resume_blocked_before_threshold_retries_locally", generated)
        self.assertIn("test_generated_repair_and_resume_blocked_after_threshold_requests_unblocking", generated)
        self.assertIn("test_generated_repair_and_resume_resumes_to_return_stage", generated)
        self.assertIn("test_generated_repair_and_resume_without_return_stage_stays_put", generated)
        self.assertIn("test_generated_template_context_prefers_state_for_change_id", generated)

    def test_workflow_creator_verifier_regression_tests_support_state(self) -> None:
        create_workflow = self._load_create_workflow_module()
        tests = create_workflow._validate_regression_tests(
            [
                {
                    "name": "verifier_uses_state",
                    "type": "verifier",
                    "step_id": "collect_context",
                    "observation": {
                        "status": "succeeded",
                        "summary": "Done.",
                        "structured_output": {"ready": True},
                    },
                    "state": {"prepared_target": "abc123"},
                    "expected_passed": False,
                }
            ],
            stages=[{"step_id": "collect_context"}],
            final_step_id="finalize_summary",
        )

        self.assertEqual(tests[0]["state"], {"prepared_target": "abc123"})

    def test_workflow_creator_prompt_sections_reject_tasks_field(self) -> None:
        create_workflow = self._load_create_workflow_module()

        with self.assertRaisesRegex(ValueError, "tasks is no longer supported"):
            create_workflow._validate_prompt_sections(
                {
                    "stage_goal": "Prepare the internal execution plan.",
                    "context": ["Input path: {{input_path}}"],
                    "tasks": ["Read the input.", "Return the result."],
                    "boundaries": ["Do not implement unrelated changes."],
                    "blocked_conditions": ["If the input path is missing, return `blocked`."],
                },
                fallback_prompt="Prepare the internal execution plan for this workflow stage.",
                label="example.prompt_sections",
            )

    def test_workflow_creator_agent_review_includes_spec_and_prompt_alignment(self) -> None:
        create_workflow = self._load_create_workflow_module()
        review = create_workflow._render_agent_review_md(
            {
                "workflow_id": "example_workflow",
                "stages": [
                    {
                        "step_id": "collect_context",
                    }
                ],
            }
        )

        self.assertIn("as the source of truth for the review", review)
        self.assertIn("Review `spec.json` first", review)
        self.assertIn("Do not start by patching", review)
        self.assertIn("After the spec review, verify generated files faithfully implement the spec", review)
        self.assertIn("then regenerate or make matching code edits", review)
        self.assertIn("Prefer citing `spec.json`", review)
        self.assertIn("Verify prompt-contract intent in the spec", review)
        self.assertIn("Verify outcome and recovery routing in the spec", review)
        self.assertIn("recovery_return_node", review)
        self.assertIn("verifier templates", review)
        self.assertIn("`prompts/*.md`", review)
        self.assertIn("`prompt_sections` should match `done_when`", review)
        self.assertIn("placeholders should come", review)
        self.assertIn("from start input", review)
        self.assertIn("generated files when they drift from the spec", review)
        self.assertIn("use multiple review", review)
        self.assertIn("explicitly ask the user", review)
        self.assertIn("permission to use", review)
        self.assertIn("subagent-backed pass", review)
        self.assertIn("blocked", review)
        self.assertIn("prompt review", review)
        self.assertIn("stage goal", review)
        self.assertIn("should not", review)
        self.assertIn("internal checklist", review)
        self.assertIn("overly procedural", review)
        self.assertIn("`verifiers.py` and verifier declarations", review)
        self.assertIn("`contract.py` and output schemas", review)
        self.assertIn("`graphbuilder_runtime.py`, `policy.py`, and `references/flowchart.md`", review)

    def test_workflow_creator_generates_custom_verifier_scaffolds_before_review(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "custom_verifier_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "custom_verifier_workflow",
                        "flow_description": "Exercise custom verifier requirement preservation.",
                        "stages": [
                            {
                                "step_id": "review_design_doc",
                                "prompt": "Review the design doc and confirm it is implementation-ready.",
                                "done_when": ["The design doc is reviewable"],
                                "output_schema": {
                                    "design_doc_path": "string",
                                    "design_ready": "boolean",
                                },
                                "failure_schema": {"blocked_reason": "string?"},
                                "custom_verifier_requirements": [
                                    {
                                        "id": "design_doc_matches_brainstorming_contract",
                                        "description": "When design_ready is true, the design doc must exist and include goal, approaches, recommendation, and explicit user approval context.",
                                        "signals": [
                                            "design_doc_path",
                                            "design_ready",
                                        ],
                                        "implementation_surface": ["verifier", "tests"],
                                        "implementation_notes": "Check file contents and stage semantics in generated verifiers.py code before review.",
                                        "hint_pseudocode": [
                                            "if output.design_ready is true: require design_doc_path to exist",
                                            "read the design doc and verify goal, approaches, recommendation, and explicit approval context headings exist",
                                        ],
                                        "test_intent": [
                                            "fails when design_ready is true but the file is missing",
                                            "fails when the design doc omits required headings",
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            workflow_spec = create_workflow._load_workflow_spec(
                spec_file=spec_path,
                workflow_id=None,
                flow_description=None,
            )

        stage = workflow_spec["stages"][0]
        self.assertEqual(
            stage["custom_verifier_requirements"][0]["id"],
            "design_doc_matches_brainstorming_contract",
        )
        self.assertEqual(
            stage["custom_verifier_requirements"][0]["signals"],
            ["design_doc_path", "design_ready"],
        )
        self.assertEqual(
            stage["custom_verifier_requirements"][0]["implementation_surface"],
            ["verifier", "tests"],
        )
        rendered_verifiers, warnings = create_workflow._render_verifiers_py(workflow_spec)
        self.assertEqual(warnings, [])
        self.assertIn(
            "def _run_custom_verifier_requirements_review_design_doc(",
            rendered_verifiers,
        )
        self.assertIn(
            "def _custom_verifier_requirement_review_design_doc_design_doc_matches_brainstorming_contract(",
            rendered_verifiers,
        )
        self.assertIn(
            "Custom verifier scaffold generated from stages[].custom_verifier_requirements.",
            rendered_verifiers,
        )
        self.assertIn(
            "Self-contained contract: keep this requirement-scoped verifier self-contained when practical.",
            rendered_verifiers,
        )
        self.assertIn(
            "Do not add same-file helper layers in verifiers.py and depend on them from the preserved requirement function.",
            rendered_verifiers,
        )
        self.assertIn(
            "TODO(custom_verifier_requirement): Implement `design_doc_matches_brainstorming_contract`.",
            rendered_verifiers,
        )
        self.assertIn("Implementation surfaces: verifier, tests", rendered_verifiers)
        self.assertIn(
            "# - if output.design_ready is true: require design_doc_path to exist",
            rendered_verifiers,
        )
        self.assertIn(
            "# - fails when the design doc omits required headings",
            rendered_verifiers,
        )
        review = create_workflow._render_agent_review_md(workflow_spec)
        self.assertIn("Declared Custom Verifier Requirements", review)
        self.assertIn("design_doc_matches_brainstorming_contract", review)
        self.assertIn("generated custom verifier scaffolds", review)
        self.assertIn("Implementation surfaces: `verifier`, `tests`", review)
        self.assertIn("Hint pseudocode:", review)
        self.assertIn("Test intent:", review)
        self.assertIn("custom_verifier_requirements", review)
        self.assertIn("same-file helper dependencies as a blocking review issue", review)

    def test_workflow_creator_accepts_generic_verifier_templates(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "generic_template_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "generic_template_workflow",
                        "flow_description": "Exercise generic verifier template generation.",
                        "stages": [
                            {
                                "step_id": "review_inputs",
                                "prompt": "Review the generated inputs.",
                                "done_when": ["The generated inputs are accepted"],
                                "output_schema": {
                                    "artifact_path": "string",
                                    "review_perspectives": "string[]",
                                },
                                "failure_schema": {"blocked_reason": "string?"},
                                "verifier_templates": [
                                    {
                                        "id": "artifact_path_policy",
                                        "template": "repo_path_policy",
                                        "output_key": "artifact_path",
                                        "message": "artifact_path must stay under docs/ and be Markdown.",
                                        "required_prefix": "docs/",
                                        "forbidden_prefixes": ["openspec/changes/"],
                                        "required_suffix": ".md",
                                    },
                                    {
                                        "id": "review_requires_named_perspectives",
                                        "template": "required_set_members",
                                        "output_key": "review_perspectives",
                                        "message": "review_perspectives must include required review lenses.",
                                        "required_members": ["development", "design", "testing"],
                                    },
                                ],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            workflow_spec = create_workflow._load_workflow_spec(
                spec_file=spec_path,
                workflow_id=None,
                flow_description=None,
            )

        templates = workflow_spec["stages"][0]["verifier_templates"]
        self.assertEqual(templates[0]["template"], "repo_path_policy")
        self.assertEqual(templates[0]["required_prefix"], "docs/")
        self.assertEqual(templates[0]["forbidden_prefixes"], ["openspec/changes/"])
        self.assertEqual(templates[0]["required_suffix"], ".md")
        self.assertEqual(templates[1]["template"], "required_set_members")
        self.assertEqual(
            templates[1]["required_members"],
            ["development", "design", "testing"],
        )

        rendered_verifiers, warnings = create_workflow._render_verifiers_py(workflow_spec)
        self.assertEqual(warnings, [])
        self.assertIn("def _repo_path_policy_error(", rendered_verifiers)
        self.assertIn("def _required_set_members_error(", rendered_verifiers)
        self.assertNotIn("_custom_verifier_requirement_implementation_lines", rendered_verifiers)

    def test_workflow_creator_rejects_duplicate_repair_and_transition_conditions(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "conflicting_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "conflicting_workflow",
                        "flow_description": "Exercise conflict validation.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {"ready": "boolean"},
                                "failure_schema": {"blocked_reason": "string?"},
                                "repair_conditions": [
                                    {
                                        "output_key": "ready",
                                        "operator": "is_false",
                                        "reason": "context is not ready",
                                    }
                                ],
                                "transitions": [
                                    {
                                        "output_key": "ready",
                                        "operator": "is_false",
                                        "next_node": "collect_context",
                                        "branch_kind": "retry",
                                        "reason": "retry context collection",
                                    }
                                ],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                create_workflow.WorkflowCreatorError,
                "same output condition",
            ):
                create_workflow._load_workflow_spec(
                    spec_file=spec_path,
                    workflow_id=None,
                    flow_description=None,
                )

    def test_workflow_creator_rejects_unsupported_verifier_template(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "bad_template_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "bad_template_workflow",
                        "flow_description": "Exercise verifier template validation.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {"items": "string[]"},
                                "failure_schema": {"blocked_reason": "string?"},
                                "verifier_templates": [
                                    {
                                        "id": "items_follow_contract",
                                        "template": "arbitrary_python",
                                        "output_key": "items",
                                        "message": "items must follow contract",
                                    }
                                ],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                create_workflow.WorkflowCreatorError,
                "template is unsupported",
            ):
                create_workflow._load_workflow_spec(
                    spec_file=spec_path,
                    workflow_id=None,
                    flow_description=None,
                )

    def test_workflow_creator_rejects_object_return_schema_types(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "object_return_schema_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "object_return_schema_workflow",
                        "flow_description": "Reject open-ended structured return schemas.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {"items": "object[]"},
                                "failure_schema": {"blocked_reason": "string?"},
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                create_workflow.WorkflowCreatorError,
                "cannot use object/object\\[\\]",
            ):
                create_workflow._load_workflow_spec(
                    spec_file=spec_path,
                    workflow_id=None,
                    flow_description=None,
                )

    def test_workflow_creator_rejects_nested_return_schema(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "nested_return_schema_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "nested_return_schema_workflow",
                        "flow_description": "Reject nested return schemas.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {
                                    "artifact": {
                                        "path": "string",
                                    }
                                },
                                "failure_schema": {"blocked_reason": "string?"},
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                create_workflow.WorkflowCreatorError,
                "must use a flat schema type string",
            ):
                create_workflow._load_workflow_spec(
                    spec_file=spec_path,
                    workflow_id=None,
                    flow_description=None,
                )

    def test_workflow_creator_rejects_unsupported_outcome_route(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "bad_outcome_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "bad_outcome_workflow",
                        "flow_description": "Exercise outcome route validation.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {"ready": "boolean"},
                                "failure_schema": {"blocked_reason": "string?"},
                                "outcome_routes": [
                                    {
                                        "outcome": "cancelled",
                                        "next_node": "collect_context",
                                        "reason": "unsupported outcome",
                                    }
                                ],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                create_workflow.WorkflowCreatorError,
                "outcome is unsupported",
            ):
                create_workflow._load_workflow_spec(
                    spec_file=spec_path,
                    workflow_id=None,
                    flow_description=None,
                )

    def test_workflow_creator_rejects_unknown_outcome_route_target(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "unknown_outcome_target_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "unknown_outcome_target_workflow",
                        "flow_description": "Exercise outcome target validation.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {"ready": "boolean"},
                                "failure_schema": {"blocked_reason": "string?"},
                                "outcome_routes": [
                                    {
                                        "outcome": "failed",
                                        "next_node": "repair_collect_context",
                                        "reason": "route to missing repair stage",
                                    }
                                ],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                create_workflow.WorkflowCreatorError,
                "outcome_routes next_node is unknown",
            ):
                create_workflow._load_workflow_spec(
                    spec_file=spec_path,
                    workflow_id=None,
                    flow_description=None,
                )

    def test_workflow_creator_rejects_recovery_stage_without_return_node(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "bad_recovery_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "bad_recovery_workflow",
                        "flow_description": "Exercise recovery return validation.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {"ready": "boolean"},
                                "failure_schema": {"blocked_reason": "string?"},
                            },
                            {
                                "step_id": "repair_context",
                                "stage_kind": "recovery",
                                "prompt": "Repair context.",
                                "done_when": ["Context repair is complete"],
                                "output_schema": {"repair_summary": "string"},
                                "failure_schema": {"blocked_reason": "string?"},
                            },
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                create_workflow.WorkflowCreatorError,
                "recovery stage requires recovery_return_node",
            ):
                create_workflow._load_workflow_spec(
                    spec_file=spec_path,
                    workflow_id=None,
                    flow_description=None,
                )

    def test_workflow_creator_accepts_shared_repair_helper_skill_routing(self) -> None:
        create_workflow = self._load_create_workflow_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "shared_helper_skill_route_spec.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "workflow_id": "shared_helper_skill_route_workflow",
                        "flow_description": "Exercise shared helper skill routing support.",
                        "stages": [
                            {
                                "step_id": "collect_context",
                                "prompt": "Collect context.",
                                "done_when": ["Context is collected"],
                                "output_schema": {"ready": "boolean"},
                                "failure_schema": {"blocked_reason": "string?"},
                            }
                        ],
                        "shared_repair_helpers": {
                            "repair_and_resume": {
                                "skill_routing": [
                                    {
                                        "skill": "research-nex",
                                        "operations": [
                                            "repair solution exploration",
                                            "evidence-backed option synthesis",
                                        ],
                                        "file_patterns": [
                                            "*.md",
                                            "*.swift",
                                            "*.m",
                                            "*.mm",
                                        ],
                                        "usage_notes": [
                                            "Primary owner for researching repair options before retrying the return stage."
                                        ],
                                    }
                                ]
                            }
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            workflow_spec = create_workflow._load_workflow_spec(
                spec_file=spec_path,
                workflow_id=None,
                flow_description=None,
            )

            helper_routes = workflow_spec["shared_repair_helpers"]["repair_and_resume"]["skill_routing"]
            self.assertEqual(len(helper_routes), 1)
            self.assertEqual(helper_routes[0]["skill"], "research-nex")

            contract_text = create_workflow._render_contract_py(workflow_spec)
            self.assertIn("REPAIR_AND_RESUME_ROUTE_1 = SkillRoute(", contract_text)
            self.assertIn("skill='research-nex'", contract_text)
            self.assertIn("skill_routing=[REPAIR_AND_RESUME_ROUTE_1]", contract_text)

    def test_general_references_explain_skill_root_path_convention(self) -> None:
        reference_files = [
            SKILL_ROOT / "references" / "index.md",
            SKILL_ROOT / "references" / "bridge-cli-spec.md",
            SKILL_ROOT / "references" / "runtime-layout.md",
            SKILL_ROOT / "references" / "workflow-authoring-guide.md",
            SKILL_ROOT / "references" / "skill-host-python-spec.md",
        ]

        for path in reference_files:
            text = path.read_text(encoding="utf-8")
            self.assertIn("<skill-root>", text, f"{path.name} should document bundle-relative paths")

    def test_graphbuilder_runtime_verifier_failed_routes_to_recheck_runtime_scaffold(self) -> None:
        from workflows.demo_prompt_loop import graphbuilder_runtime, state as workflow_state

        result = graphbuilder_runtime.run_transition_preview(
            state=workflow_state.make_initial_state(self._start_request()),
            current_step_id="collect_context",
            observation={
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 不存在。",
            },
            verifier_result={
                "passed": False,
                "message": "reported runtime existence does not match filesystem",
            },
        )

        self.assertEqual(result.step_id, "recheck_runtime_scaffold")
        self.assertEqual(result.branch_kind, "repair")
        self.assertEqual(result.history_entry.event, "branch_selected")
        self.assertEqual(result.history_entry.node, "collect_context")
        self.assertEqual(result.history_entry.step_id, "collect_context")
        self.assertEqual(
            result.trace_payload,
            {
                "next_node": "recheck_runtime_scaffold",
                "branch_kind": "repair",
                "reason": "verifier detected a mismatch in runtime scaffold reporting",
            },
        )
        self.assertEqual(result.history_entry.payload, result.trace_payload)

    def test_graphbuilder_runtime_success_routes_to_finalize_summary(self) -> None:
        from workflows.demo_prompt_loop import graphbuilder_runtime, state as workflow_state

        result = graphbuilder_runtime.run_transition_preview(
            state=workflow_state.make_initial_state(self._start_request()),
            current_step_id="collect_context",
            observation={
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 存在。",
            },
            verifier_result={
                "passed": True,
                "message": "runtime scaffold check passed",
            },
        )

        self.assertEqual(result.step_id, "finalize_summary")
        self.assertEqual(result.branch_kind, "complete")
        self.assertEqual(result.history_entry.event, "branch_selected")
        self.assertEqual(result.history_entry.node, "collect_context")
        self.assertEqual(result.history_entry.step_id, "collect_context")
        self.assertEqual(
            result.trace_payload,
            {
                "next_node": "finalize_summary",
                "branch_kind": "complete",
                "reason": "runtime scaffold status is sufficient for final summary",
            },
        )
        self.assertEqual(result.history_entry.payload, result.trace_payload)

    def test_graphbuilder_runtime_preserves_source_step_in_history_entry(self) -> None:
        from workflows.demo_prompt_loop import graphbuilder_runtime, state as workflow_state

        result = graphbuilder_runtime.run_transition_preview(
            state=workflow_state.make_initial_state(self._start_request()),
            current_step_id="recheck_runtime_scaffold",
            observation={
                "status": "blocked",
                "summary": "复查阶段仍然无法访问目录。",
            },
            verifier_result=None,
        )

        self.assertEqual(result.step_id, "request_missing_access")
        self.assertEqual(result.history_entry.node, "recheck_runtime_scaffold")
        self.assertEqual(result.history_entry.step_id, "recheck_runtime_scaffold")
        self.assertEqual(
            result.history_entry.payload,
            {
                "next_node": "request_missing_access",
                "branch_kind": "repair",
                "reason": "recheck step is blocked and needs user help",
            },
        )

    def test_graphbuilder_engine_start_returns_collect_context_yield(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))

        response = engine.start("demo_prompt_loop", self._start_request())

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "collect_context")
        self.assertEqual(response["prompt_envelope"]["step_id"], "collect_context")
        self.assertEqual(
            set(response["prompt_envelope"]),
            {
                "run_id",
                "step_id",
                "prompt",
                "intent",
                "expected_artifact",
                "done_when",
                "output_schema",
                "failure_schema",
                "resume_instructions",
                "metadata",
            },
        )

    def test_graphbuilder_engine_resume_blocked_returns_next_yield(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        start_response = engine.start("demo_prompt_loop", self._start_request())

        response = engine.resume(
            start_response["run_id"],
            {
                "run_id": start_response["run_id"],
                "step_id": "collect_context",
                "status": "blocked",
                "summary": "无法读取目标目录。",
                "structured_output": {
                    "blocked_reason": "permission denied",
                    "error_message": "cannot access workflow-runtime",
                },
                "artifacts": [],
                "error": {
                    "type": "permission_error",
                    "message": "cannot access workflow-runtime",
                    "details": {},
                },
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "request_missing_access")
        self.assertEqual(
            response["prompt_envelope"]["step_id"],
            "request_missing_access",
        )

    def test_graphbuilder_engine_resume_success_returns_done(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        start_response = engine.start("demo_prompt_loop", self._start_request())
        runtime_entries = sorted(
            path.name
            for path in RUNTIME_ROOT.iterdir()
            if path.is_dir() and not path.name.startswith("__")
        )

        response = engine.resume(
            start_response["run_id"],
            {
                "run_id": start_response["run_id"],
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 存在，并收集到一级目录。",
                "structured_output": {
                    "runtime_exists": True,
                    "top_level_entries": runtime_entries,
                    "missing_paths": [],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "done")
        self.assertEqual(response["step_id"], "finalize_summary")
        self.assertEqual(
            response["final_prompt_envelope"]["step_id"],
            "finalize_summary",
        )

    def test_graphbuilder_engine_resume_verifier_failed_returns_recheck_yield(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        start_response = engine.start("demo_prompt_loop", self._start_request())

        response = engine.resume(
            start_response["run_id"],
            {
                "run_id": start_response["run_id"],
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 不存在。",
                "structured_output": {
                    "runtime_exists": False,
                    "top_level_entries": [],
                    "missing_paths": ["workflow-runtime"],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "recheck_runtime_scaffold")
        self.assertEqual(
            response["prompt_envelope"]["step_id"],
            "recheck_runtime_scaffold",
        )

    def test_ios_workflow_engine_verifier_failed_yield_surfaces_retry_context(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        start_response = engine.start("ios_ai_assisted_development_flow", self._start_request())

        response = engine.resume(
            start_response["run_id"],
            {
                "run_id": start_response["run_id"],
                "step_id": "run_brainstorming",
                "status": "succeeded",
                "summary": "Brainstorming completed but still has unresolved open questions.",
                "structured_output": {
                    "clarification_questions": ["What user-visible behavior should change?"],
                    "clarification_answers_summary": "The user confirmed behavior, scope, and success criteria.",
                    "design_presented": True,
                    "user_approved_design": True,
                    "design_approved": True,
                    "approved_design_summary": "Approved design summary.",
                    "approved_design_path": "docs/superpowers/specs/2026-05-30-durable-workflow-runtime-superpowers-delivery-chain-design.md",
                    "ui_surface_affected": False,
                    "open_questions": [
                        "Brainstorming open_questions must be empty before implementation planning."
                    ],
                    "ready_for_subagent_review": True,
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "run_brainstorming")
        self.assertEqual(response["retry_context"]["category"], "verifier_failed")
        self.assertIn(
            "open_questions must be empty",
            response["retry_context"]["summary"],
        )
        self.assertIn(
            "open_questions must be empty",
            response["retry_context"]["requirements"][0],
        )

    def test_ios_workflow_engine_blocked_yield_surfaces_retry_context(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        start_response = engine.start("ios_ai_assisted_development_flow", self._start_request())

        response = engine.resume(
            start_response["run_id"],
            {
                "run_id": start_response["run_id"],
                "step_id": "run_brainstorming",
                "status": "blocked",
                "summary": "Need user confirmation on the target screen before the design can continue.",
                "structured_output": {
                    "blocked_reason": "waiting for target screen confirmation",
                    "missing_inputs": ["target screen confirmation"],
                    "open_questions": ["Which screen should change?"],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "repair_and_resume")
        self.assertEqual(response["retry_context"]["category"], "blocked")
        self.assertEqual(
            response["retry_context"]["summary"],
            "waiting for target screen confirmation",
        )
        self.assertEqual(
            response["retry_context"]["requirements"],
            ["target screen confirmation"],
        )

    def test_graphbuilder_engine_cross_instance_resume_blocked_returns_next_yield(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine1 = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        start_response = engine1.start("demo_prompt_loop", self._start_request())

        engine2 = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        response = engine2.resume(
            start_response["run_id"],
            {
                "run_id": start_response["run_id"],
                "step_id": "collect_context",
                "status": "blocked",
                "summary": "无法读取目标目录。",
                "structured_output": {
                    "blocked_reason": "permission denied",
                    "error_message": "cannot access workflow-runtime",
                },
                "artifacts": [],
                "error": {
                    "type": "permission_error",
                    "message": "cannot access workflow-runtime",
                    "details": {},
                },
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "request_missing_access")

    def test_graphbuilder_engine_cross_instance_resume_success_returns_done(self) -> None:
        from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine

        engine1 = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        start_response = engine1.start("demo_prompt_loop", self._start_request())
        runtime_entries = sorted(
            path.name
            for path in RUNTIME_ROOT.iterdir()
            if path.is_dir() and not path.name.startswith("__")
        )

        engine2 = GraphBuilderRuntimeEngine(str(REPO_ROOT))
        response = engine2.resume(
            start_response["run_id"],
            {
                "run_id": start_response["run_id"],
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 存在，并收集到一级目录。",
                "structured_output": {
                    "runtime_exists": True,
                    "top_level_entries": runtime_entries,
                    "missing_paths": [],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "done")
        self.assertEqual(response["step_id"], "finalize_summary")

    def test_shared_module_loader_returns_demo_workflow_modules(self) -> None:
        from runtime.module_loader import load_workflow_modules

        modules = load_workflow_modules("demo_prompt_loop")

        self.assertEqual(modules["contract"].WORKFLOW_ID, "demo_prompt_loop")
        self.assertTrue(hasattr(modules["graphbuilder_runtime"], "build_graph"))
        self.assertTrue(hasattr(modules["state"], "make_initial_state"))

    def test_shared_validation_rejects_invalid_constraints_type(self) -> None:
        from runtime.models import StartRequest
        from runtime.module_loader import load_workflow_modules
        from runtime.validation import validate_workflow_input
        from runtime.errors import WorkflowExecutionError

        modules = load_workflow_modules("demo_prompt_loop")
        request = StartRequest.from_dict(
            {
                "task_input": {"goal": "检查仓库里是否已有 workflow-runtime 骨架"},
                "context": {"repo_root": str(REPO_ROOT)},
                "constraints": {"max_steps": "five"},
            }
        )

        with self.assertRaises(WorkflowExecutionError):
            validate_workflow_input(request, modules["contract"].WORKFLOW_INPUT_CONTRACT)

    def test_common_policy_condition_matches_supported_operators(self) -> None:
        from workflows.common.policies import condition_matches

        self.assertTrue(condition_matches("ship", "equals", "ship"))
        self.assertTrue(condition_matches("ship", "not_equals", "blocked"))
        self.assertTrue(condition_matches(True, "is_true", None))
        self.assertTrue(condition_matches(False, "is_false", None))
        self.assertTrue(condition_matches(["check"], "non_empty", None))
        self.assertTrue(condition_matches([], "empty", None))
        self.assertFalse(condition_matches("ship", "unknown", None))

    def test_common_policy_max_steps_routes_to_unblocking(self) -> None:
        from workflows.common.policies import max_steps_exceeded_decision

        decision = max_steps_exceeded_decision(
            current_step_id="execute_implementation",
            state={
                "constraints": {"max_steps": 2},
                "attempt_counts": {
                    "run_brainstorming": 1,
                    "execute_implementation": 1,
                },
            },
        )

        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertEqual(decision.next_node, "repair_and_resume")
        self.assertEqual(decision.branch_kind, "repair")
        self.assertEqual(decision.metadata["max_steps"], 2)

    def test_common_policy_max_steps_ignores_repair_stage(self) -> None:
        from workflows.common.policies import max_steps_exceeded_decision

        decision = max_steps_exceeded_decision(
            current_step_id="request_unblocking_input",
            state={
                "constraints": {"max_steps": 1},
                "attempt_counts": {"run_brainstorming": 2},
            },
        )

        self.assertIsNone(decision)

    def test_ios_repair_blocked_before_threshold_stays_in_repair(self) -> None:
        from workflows.ios_ai_assisted_development_flow import graphbuilder_runtime
        from workflows.ios_ai_assisted_development_flow.state import make_initial_state

        state = make_initial_state(
            {
                "task_input": {"goal": "repair threshold"},
                "context": {"repo_root": str(REPO_ROOT)},
                "constraints": {},
            }
        )
        state.return_stage_id = "verify_completion"
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={
                "status": "blocked",
                "summary": "Need approval before retry.",
                "structured_output": {"missing_inputs": ["approval"]},
            },
            verifier_result=None,
        )

        self.assertEqual(result.step_id, "repair_and_resume")
        self.assertEqual(result.branch_kind, "retry")

    def test_ios_repair_blocked_after_threshold_requests_unblocking(self) -> None:
        from workflows.ios_ai_assisted_development_flow import graphbuilder_runtime
        from workflows.ios_ai_assisted_development_flow.state import make_initial_state

        state = make_initial_state(
            {
                "task_input": {"goal": "repair threshold"},
                "context": {"repo_root": str(REPO_ROOT)},
                "constraints": {},
            }
        )
        state.return_stage_id = "verify_completion"
        state.attempt_counts["repair_and_resume"] = 2
        result = graphbuilder_runtime.run_transition_preview(
            state=state,
            current_step_id="repair_and_resume",
            observation={
                "status": "blocked",
                "summary": "Need approval before retry.",
                "structured_output": {"missing_inputs": ["approval"]},
            },
            verifier_result=None,
        )

        self.assertEqual(result.step_id, "request_unblocking_input")
        self.assertEqual(result.branch_kind, "repair")

    def test_shared_verifier_runner_executes_shell_command(self) -> None:
        from runtime.models import Observation, RunState
        from runtime.module_loader import load_workflow_modules
        from runtime.verifier_runner import run_step_verifier
        from workflows.common.contracts import StepVerifier

        modules = load_workflow_modules("demo_prompt_loop")
        run_state = RunState(
            run_id="run_test",
            workflow_id="demo_prompt_loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        observation = Observation.from_dict(
            {
                "run_id": "run_test",
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "shell verifier smoke test",
                "structured_output": {},
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            }
        )

        result = run_step_verifier(
            repo_root=str(REPO_ROOT),
            modules=modules,
            verifier=StepVerifier(
                kind="shell_command",
                ref="test 1 -eq 1",
                timeout_seconds=5,
                run_on_status=["succeeded"],
            ),
            run_state=run_state,
            observation=observation,
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["message"], "shell verifier passed")

    def test_resume_blocked_routes_to_request_missing_access(self) -> None:
        skill_host = self._load_skill_host()
        start_response = skill_host.start(str(REPO_ROOT), self._start_request())
        run_id = start_response["run_id"]

        response = skill_host.resume(
            str(REPO_ROOT),
            run_id,
            {
                "run_id": run_id,
                "step_id": "collect_context",
                "status": "blocked",
                "summary": "无法读取目标目录。",
                "structured_output": {
                    "blocked_reason": "permission denied",
                    "error_message": "cannot access workflow-runtime",
                },
                "artifacts": [],
                "error": {
                    "type": "permission_error",
                    "message": "cannot access workflow-runtime",
                    "details": {},
                },
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "request_missing_access")
        self.assertEqual(
            response["prompt_envelope"]["step_id"],
            "request_missing_access",
        )

    def test_resume_success_returns_done(self) -> None:
        skill_host = self._load_skill_host()
        start_response = skill_host.start(str(REPO_ROOT), self._start_request())
        run_id = start_response["run_id"]
        runtime_entries = sorted(
            path.name
            for path in RUNTIME_ROOT.iterdir()
            if path.is_dir() and not path.name.startswith("__")
        )

        response = skill_host.resume(
            str(REPO_ROOT),
            run_id,
            {
                "run_id": run_id,
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 存在，并收集到一级目录。",
                "structured_output": {
                    "runtime_exists": True,
                    "top_level_entries": runtime_entries,
                    "missing_paths": [],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [
                    {
                        "tool_name": "shell",
                        "status": "succeeded",
                        "input_summary": "ls workflow-runtime",
                        "output_summary": "listed first-level entries",
                        "artifact_refs": [],
                        "metadata": {},
                    }
                ],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "done")
        self.assertEqual(response["step_id"], "finalize_summary")
        self.assertEqual(
            response["final_prompt_envelope"]["step_id"],
            "finalize_summary",
        )
        recommendations = response["next_step_recommendations"]
        self.assertEqual(recommendations["kind"], "workflow_catalog_lookup")
        self.assertEqual(recommendations["source_workflow_id"], "demo_prompt_loop")
        self.assertNotIn("workflow_binding_ref", recommendations)
        self.assertNotIn("reference_scope", recommendations)
        self.assertNotIn("workflow_binding_path", recommendations)
        self.assertNotIn("workflows", recommendations)
        self.assertTrue(
            any("workflow-binding.json" in item for item in recommendations["instructions"])
        )
        self.assertTrue(
            any("catalog entry" in item for item in recommendations["instructions"])
        )

    def test_resume_verifier_failed_routes_to_recheck_runtime_scaffold(self) -> None:
        skill_host = self._load_skill_host()
        start_response = skill_host.start(str(REPO_ROOT), self._start_request())
        run_id = start_response["run_id"]

        response = skill_host.resume(
            str(REPO_ROOT),
            run_id,
            {
                "run_id": run_id,
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 不存在。",
                "structured_output": {
                    "runtime_exists": False,
                    "top_level_entries": [],
                    "missing_paths": ["workflow-runtime"],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            },
        )

        self.assertEqual(response["kind"], "yield")
        self.assertEqual(response["step_id"], "recheck_runtime_scaffold")
        self.assertEqual(
            response["prompt_envelope"]["step_id"],
            "recheck_runtime_scaffold",
        )

    def test_resume_after_done_raises_protocol_error(self) -> None:
        skill_host = self._load_skill_host()
        start_response = skill_host.start(str(REPO_ROOT), self._start_request())
        run_id = start_response["run_id"]
        runtime_entries = sorted(
            path.name
            for path in RUNTIME_ROOT.iterdir()
            if path.is_dir() and not path.name.startswith("__")
        )

        done_response = skill_host.resume(
            str(REPO_ROOT),
            run_id,
            {
                "run_id": run_id,
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "已确认 workflow-runtime 存在，并收集到一级目录。",
                "structured_output": {
                    "runtime_exists": True,
                    "top_level_entries": runtime_entries,
                    "missing_paths": [],
                },
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            },
        )
        self.assertEqual(done_response["kind"], "done")

        with self.assertRaises(skill_host.ProtocolError):
            skill_host.resume(
                str(REPO_ROOT),
                run_id,
                {
                    "run_id": run_id,
                    "step_id": "finalize_summary",
                    "status": "succeeded",
                    "summary": "不应该允许 done 后 resume。",
                    "structured_output": {},
                    "artifacts": [],
                    "error": None,
                    "tool_trace": [],
                    "raw_output": "",
                },
            )

    def test_persisted_history_records_branch_selection(self) -> None:
        from workflows.demo_prompt_loop import graphbuilder_runtime, state as workflow_state

        skill_host = self._load_skill_host()
        start_response = skill_host.start(str(REPO_ROOT), self._start_request())
        run_id = start_response["run_id"]

        skill_host.resume(
            str(REPO_ROOT),
            run_id,
            {
                "run_id": run_id,
                "step_id": "collect_context",
                "status": "blocked",
                "summary": "无法读取目标目录。",
                "structured_output": {
                    "blocked_reason": "permission denied",
                    "error_message": "cannot access workflow-runtime",
                },
                "artifacts": [],
                "error": {
                    "type": "permission_error",
                    "message": "cannot access workflow-runtime",
                    "details": {},
                },
                "tool_trace": [],
                "raw_output": "",
            },
        )
        preview = graphbuilder_runtime.run_transition_preview(
            state=workflow_state.make_initial_state(self._start_request()),
            current_step_id="collect_context",
            observation={
                "status": "blocked",
                "summary": "无法读取目标目录。",
            },
            verifier_result=None,
        )

        run_state_file = WORKSPACE_ROOT / "runs" / f"{run_id}.json"
        self.assertTrue(run_state_file.exists())
        payload = json.loads(run_state_file.read_text(encoding="utf-8"))
        events = [entry["event"] for entry in payload["history"]]
        self.assertIn("branch_selected", events)
        self.assertEqual(payload["current_node"], "request_missing_access")
        branch_entry = next(entry for entry in payload["history"] if entry["event"] == "branch_selected")
        self.assertEqual(branch_entry["node"], preview.history_entry.node)
        self.assertEqual(branch_entry["step_id"], preview.history_entry.step_id)
        self.assertEqual(branch_entry["payload"], preview.history_entry.payload)

    def test_host_io_helper_allocates_run_scoped_paths(self) -> None:
        import host_io

        layout = host_io.ensure_run_layout(REPO_ROOT, "run_host_io")
        response_path = host_io.response_path(
            REPO_ROOT,
            "run_host_io",
            "collect_context",
            sequence=1,
        )
        observation_path = host_io.observation_path(
            REPO_ROOT,
            "run_host_io",
            "collect_context",
            sequence=1,
        )
        artifact_path = host_io.artifact_path(
            REPO_ROOT,
            "run_host_io",
            "notes/final.md",
        )

        expected_run_dir = WORKSPACE_ROOT / "host-io" / "run_host_io"
        self.assertEqual(layout.run_dir, expected_run_dir)
        self.assertEqual(response_path, expected_run_dir / "responses" / "001_collect_context.json")
        self.assertEqual(observation_path, expected_run_dir / "observations" / "001_collect_context.json")
        self.assertEqual(artifact_path, expected_run_dir / "artifacts" / "notes" / "final.md")
        self.assertTrue(layout.responses_dir.is_dir())
        self.assertTrue(layout.observations_dir.is_dir())
        self.assertTrue((expected_run_dir / "artifacts" / "notes").is_dir())

    def test_host_io_helper_writes_manifest(self) -> None:
        import host_io

        manifest_path = host_io.write_manifest(
            REPO_ROOT,
            "run_manifest",
            workflow_id="demo_prompt_loop",
            extra={"current_step": "collect_context"},
        )

        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["layout_version"], 1)
        self.assertEqual(payload["run_id"], "run_manifest")
        self.assertEqual(payload["workflow_id"], "demo_prompt_loop")
        self.assertEqual(payload["current_step"], "collect_context")
        self.assertIn("/host-io/run_manifest", payload["paths"]["run_dir"])

    def test_host_io_helper_rejects_path_traversal(self) -> None:
        import host_io

        with self.assertRaises(ValueError):
            host_io.ensure_run_layout(REPO_ROOT, "../run_escape")
        with self.assertRaises(ValueError):
            host_io.response_path(REPO_ROOT, "run_ok", "../step")
        with self.assertRaises(ValueError):
            host_io.artifact_path(REPO_ROOT, "run_ok", "../artifact.md")
        with self.assertRaises(ValueError):
            host_io.artifact_path(REPO_ROOT, "run_ok", "/tmp/artifact.md")

    def test_host_io_cli_allocates_pending_start_request_path(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(HOST_IO_PATH),
                "pending-start",
                "--repo-root",
                str(REPO_ROOT),
                "--workflow-id",
                "ios_goals",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["kind"], "pending_start_request_path")
        self.assertEqual(
            Path(payload["path"]),
            WORKSPACE_ROOT / "host-io" / "pending" / "ios_goals-start-request.json",
        )

    def test_pack_cli_creates_flow_archive_for_published_workflow(self) -> None:
        output_file = WORKSPACE_ROOT / "packages" / "demo_prompt_loop.flow"

        result = subprocess.run(
            [
                sys.executable,
                str(PACK_PATH),
                "--workflow-id",
                "demo_prompt_loop",
                "--output-file",
                str(output_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["kind"], "flow_package")
        self.assertEqual(payload["workflow_id"], "demo_prompt_loop")
        self.assertEqual(Path(payload["output_file"]), output_file)
        self.assertTrue(output_file.exists())

        with zipfile.ZipFile(output_file) as archive:
            names = set(archive.namelist())
            package_manifest = json.loads(
                archive.read("package-manifest.json").decode("utf-8")
            )
            binding_entry = json.loads(archive.read("binding-entry.json").decode("utf-8"))

        self.assertIn("package-manifest.json", names)
        self.assertIn("binding-entry.json", names)
        self.assertIn("workflow/manifest.json", names)
        self.assertIn("workflow/.workflow-lock.json", names)
        self.assertIn("workflow/contract.py", names)
        self.assertIn("workflow/prompts/collect_context.md", names)
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertFalse(any(name.endswith(".pyc") for name in names))
        self.assertEqual(package_manifest["package_type"], "durable-workflow-runtime.flow")
        self.assertEqual(package_manifest["workflow_id"], "demo_prompt_loop")
        self.assertEqual(binding_entry["workflow_id"], "demo_prompt_loop")
        self.assertEqual(
            binding_entry["start_input_schema"],
            self._contract_start_input_schema("demo_prompt_loop"),
        )

    def test_pack_cli_rejects_unpublished_workflow(self) -> None:
        output_file = WORKSPACE_ROOT / "packages" / "missing_workflow.flow"

        result = subprocess.run(
            [
                sys.executable,
                str(PACK_PATH),
                "--workflow-id",
                "missing_workflow",
                "--output-file",
                str(output_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertFalse(output_file.exists())
        self.assertIn("workflow is not published in binding catalog", result.stderr)

    def test_register_cli_installs_flow_archive_into_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            workflows_root = runtime_root / "workflow-runtime" / "workflows"
            workflows_root.mkdir(parents=True)
            binding_path = runtime_root / "workflow-binding.json"
            binding_path.write_text(
                json.dumps(
                    {
                        "default_workflow_id": "demo_prompt_loop",
                        "workflows": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            flow_file = tmpdir_path / "registered_demo.flow"
            self._write_test_flow_archive(flow_file, workflow_id="registered_demo")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REGISTER_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--flow-file",
                    str(flow_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["kind"], "flow_registration")
            self.assertEqual(payload["workflow_id"], "registered_demo")
            self.assertFalse(payload["replaced_existing"])
            self.assertTrue((workflows_root / "registered_demo" / "manifest.json").exists())
            self.assertTrue((workflows_root / "registered_demo" / ".workflow-lock.json").exists())
            self.assertTrue(
                (workflows_root / "registered_demo" / "prompts" / "collect_context.md").exists()
            )
            shortcut_skill_path = (
                runtime_root / "workflow-shortcuts" / "registered_demo" / "SKILL.md"
            ).resolve()
            shortcut_skill_text = shortcut_skill_path.read_text(encoding="utf-8")
            self.assertEqual(payload["shortcut_skill_name"], "workflow:registered_demo")
            self.assertEqual(payload["shortcut_skill_file"], str(shortcut_skill_path))
            self.assertIn("name: workflow:registered_demo", shortcut_skill_text)
            self.assertIn("/workflow:registered_demo", shortcut_skill_text)
            self.assertIn(
                "/durable-workflow-runtime registered_demo followed by the user's raw trailing text after `/workflow:registered_demo`",
                shortcut_skill_text,
            )
            self.assertNotIn("<user_prompt>", shortcut_skill_text)
            self.assertNotIn("## Invocation Boundary", shortcut_skill_text)
            self.assertNotIn("## Empty Invocation", shortcut_skill_text)

            binding_payload = json.loads(binding_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [item["workflow_id"] for item in binding_payload["workflows"]],
                ["registered_demo"],
            )

    def test_register_cli_rejects_existing_workflow_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            workflows_root = runtime_root / "workflow-runtime" / "workflows"
            (workflows_root / "registered_demo").mkdir(parents=True)
            binding_path = runtime_root / "workflow-binding.json"
            binding_path.write_text(
                json.dumps(
                    {
                        "default_workflow_id": "demo_prompt_loop",
                        "workflows": [
                            {
                                "workflow_id": "registered_demo",
                                "flow_description": "existing workflow",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            flow_file = tmpdir_path / "registered_demo.flow"
            self._write_test_flow_archive(flow_file, workflow_id="registered_demo")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REGISTER_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--flow-file",
                    str(flow_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("workflow already exists", result.stderr)

    def test_delete_cli_removes_workflow_dir_and_binding_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            workflows_root = runtime_root / "workflow-runtime" / "workflows"
            (workflows_root / "default_demo").mkdir(parents=True)
            (workflows_root / "old_demo").mkdir(parents=True)
            shortcut_dir = runtime_root / "workflow-shortcuts" / "old_demo"
            shortcut_dir.mkdir(parents=True)
            (shortcut_dir / "SKILL.md").write_text(
                "---\nname: workflow:old_demo\n---\n",
                encoding="utf-8",
            )
            binding_path = runtime_root / "workflow-binding.json"
            binding_path.write_text(
                json.dumps(
                    {
                        "default_workflow_id": "default_demo",
                        "workflows": [
                            {
                                "workflow_id": "default_demo",
                                "flow_description": "default workflow",
                            },
                            {
                                "workflow_id": "old_demo",
                                "flow_description": "workflow to delete",
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(DELETE_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--workflow-id",
                    "old_demo",
                    "--confirm",
                    "old_demo",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["kind"], "workflow_deletion")
            self.assertEqual(payload["workflow_id"], "old_demo")
            self.assertFalse((workflows_root / "old_demo").exists())
            self.assertTrue((workflows_root / "default_demo").exists())
            self.assertEqual(payload["shortcut_skill_name"], "workflow:old_demo")
            self.assertTrue(payload["removed_shortcut_skill"])
            self.assertFalse(shortcut_dir.exists())

            binding_payload = json.loads(binding_path.read_text(encoding="utf-8"))
            self.assertEqual(binding_payload["default_workflow_id"], "default_demo")
            self.assertEqual(
                [item["workflow_id"] for item in binding_payload["workflows"]],
                ["default_demo"],
            )

    def test_delete_cli_rejects_default_workflow_without_explicit_default_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            workflows_root = runtime_root / "workflow-runtime" / "workflows"
            (workflows_root / "default_demo").mkdir(parents=True)
            binding_path = runtime_root / "workflow-binding.json"
            binding_path.write_text(
                json.dumps(
                    {
                        "default_workflow_id": "default_demo",
                        "workflows": [
                            {
                                "workflow_id": "default_demo",
                                "flow_description": "default workflow",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(DELETE_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--workflow-id",
                    "default_demo",
                    "--confirm",
                    "default_demo",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("workflow is the current default", result.stderr)
            self.assertTrue((workflows_root / "default_demo").exists())

    def test_inject_cli_writes_agents_and_claude_workflow_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            repo_root = tmpdir_path / "target-repo"
            repo_root.mkdir()
            self._write_test_runtime_binding(runtime_root)
            (repo_root / "AGENTS.md").write_text("Existing guidance.\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(INJECT_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--repo-root",
                    str(repo_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["kind"], "workflow_instruction_injection")
            self.assertEqual(payload["workflow_count"], 2)
            actions = {
                Path(item["path"]).name: item["action"]
                for item in payload["updated_files"]
            }
            self.assertEqual(actions["AGENTS.md"], "appended")
            self.assertEqual(actions["CLAUDE.md"], "created")

            agents_text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
            claude_text = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
            for text in (agents_text, claude_text):
                self.assertIn("<!-- durable-workflow-runtime:start -->", text)
                self.assertIn("How to use durable-workflow-runtime", text)
                self.assertIn("use `durable-workflow-runtime`", text)
                self.assertIn("Select a workflow", text)
                self.assertIn(
                    "Invocation format: `durable-workflow-runtime <workflow_id> <user_prompt>`",
                    text,
                )
                self.assertNotIn("bridge.py", text)
                self.assertNotIn("task_input", text)
                self.assertNotIn("constraints", text)
                self.assertIn("<available_workflows>", text)
                self.assertIn("<workflow_id>pdf-processing</workflow_id>", text)
                self.assertIn(
                    "<description>Analyze datasets, generate charts, and create summary reports.</description>",
                    text,
                )
                self.assertIn("<!-- durable-workflow-runtime:end -->", text)
            self.assertIn("Existing guidance.", agents_text)

    def test_inject_cli_replaces_existing_marker_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            repo_root = tmpdir_path / "target-repo"
            repo_root.mkdir()
            self._write_test_runtime_binding(runtime_root)
            agents_path = repo_root / "AGENTS.md"
            agents_path.write_text(
                "Before\n"
                "<!-- durable-workflow-runtime:start -->\n"
                "old workflow list\n"
                "<!-- durable-workflow-runtime:end -->\n"
                "After\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(INJECT_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--repo-root",
                    str(repo_root),
                    "--target-file",
                    "AGENTS.md",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["updated_files"][0]["action"], "replaced")
            agents_text = agents_path.read_text(encoding="utf-8")
            self.assertEqual(agents_text.count("<!-- durable-workflow-runtime:start -->"), 1)
            self.assertEqual(agents_text.count("<!-- durable-workflow-runtime:end -->"), 1)
            self.assertIn("Before", agents_text)
            self.assertIn("After", agents_text)
            self.assertNotIn("old workflow list", agents_text)
            self.assertIn("<workflow_id>data-analysis</workflow_id>", agents_text)
            self.assertFalse((repo_root / "CLAUDE.md").exists())

    def test_workflow_creator_cli_creates_scaffold_and_binding_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)

            result = subprocess.run(
                [
                    sys.executable,
                    str(CREATE_WORKFLOW_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--workflow-id",
                    "paper_review_flow",
                    "--flow-description",
                    "Review academic paper drafts through structured reviewer stages.",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            workflow_dir = runtime_root / "workflow-runtime" / "workflows" / "paper_review_flow"
            self.assertEqual(payload["kind"], "workflow_scaffold")
            self.assertEqual(payload["workflow_id"], "paper_review_flow")
            self.assertFalse(payload["replaced_existing"])
            self.assertEqual(
                payload["spec_blueprint_file"],
                str((workflow_dir / "spec.json").resolve()),
            )
            shortcut_skill_path = (
                runtime_root / "workflow-shortcuts" / "paper_review_flow" / "SKILL.md"
            ).resolve()
            self.assertTrue((workflow_dir / "contract.py").exists())
            self.assertTrue((workflow_dir / "manifest.json").exists())
            self.assertTrue((workflow_dir / ".workflow-lock.json").exists())
            self.assertTrue((workflow_dir / "spec.json").exists())
            self.assertEqual(payload["shortcut_skill_name"], "workflow:paper_review_flow")
            self.assertEqual(payload["shortcut_skill_file"], str(shortcut_skill_path))

            contract_text = (workflow_dir / "contract.py").read_text(encoding="utf-8")
            state_text = (workflow_dir / "state.py").read_text(encoding="utf-8")
            flowchart_text = (workflow_dir / "references" / "flowchart.md").read_text(
                encoding="utf-8"
            )
            shortcut_skill_text = shortcut_skill_path.read_text(encoding="utf-8")
            manifest_payload = json.loads(
                (workflow_dir / "manifest.json").read_text(encoding="utf-8")
            )
            lockfile_payload = json.loads(
                (workflow_dir / ".workflow-lock.json").read_text(encoding="utf-8")
            )
            spec_blueprint = json.loads((workflow_dir / "spec.json").read_text(encoding="utf-8"))
            binding_payload = json.loads(
                (runtime_root / "workflow-binding.json").read_text(encoding="utf-8")
            )

            self.assertIn('WORKFLOW_ID = "paper_review_flow"', contract_text)
            self.assertIn("workflows.paper_review_flow.verifiers", contract_text)
            self.assertIn("class PaperReviewFlowWorkflowState", state_text)
            self.assertIn("paper_review_flow", flowchart_text)
            self.assertIn("## Stage Responsibilities", flowchart_text)
            self.assertIn("run_primary_stage[run_primary_stage]", flowchart_text)
            self.assertIn("| `run_primary_stage` |", flowchart_text)
            self.assertNotIn("example_workflow", contract_text)
            self.assertIn("name: workflow:paper_review_flow", shortcut_skill_text)
            self.assertIn("/workflow:paper_review_flow", shortcut_skill_text)
            self.assertIn(
                "/durable-workflow-runtime paper_review_flow followed by the user's raw trailing text after `/workflow:paper_review_flow`",
                shortcut_skill_text,
            )
            self.assertNotIn("<user_prompt>", shortcut_skill_text)
            self.assertNotIn("# Workflow Shortcut", shortcut_skill_text)
            self.assertEqual(manifest_payload["workflow_id"], "paper_review_flow")
            self.assertEqual(lockfile_payload["workflow_id"], "paper_review_flow")
            self.assertEqual(lockfile_payload["installed"], [])
            self.assertEqual(spec_blueprint["workflow_id"], "paper_review_flow")
            self.assertEqual(spec_blueprint["stages"], [])
            self.assertEqual(spec_blueprint["final_step_id"], "finalize_summary")
            self.assertEqual(
                [item["workflow_id"] for item in binding_payload["workflows"]],
                ["paper_review_flow"],
            )
            self.assertEqual(
                binding_payload["workflows"][0]["start_input_schema"],
                manifest_payload["start_input_schema"],
            )

    def test_workflow_creator_rejects_local_dependency_source_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="local_source_flow",
                flow_description="Reject dependency source values that point at local resolved paths.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="local_source_flow",
                spec_payload={
                    "workflow_id": "local_source_flow",
                    "flow_description": "Reject dependency source values that point at local resolved paths.",
                    "dependencies": [
                        {
                            "id": "example-skill",
                            "type": "skill",
                            "required": True,
                            "scope": "either",
                            "source": ".codex/skills/example-skill/SKILL.md",
                            "purpose": "Exercise dependency source validation.",
                        }
                    ],
                },
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("installation source", result.stderr)

    def test_workflow_creator_normalizes_internal_child_skill_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="child_skill_flow",
                flow_description="Exercise generic child skill normalization from skill-catalog source paths.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="child_skill_flow",
                spec_payload={
                    "workflow_id": "child_skill_flow",
                    "flow_description": "Exercise generic child skill normalization from skill-catalog source paths.",
                    "stages": [
                        {
                            "step_id": "run_child_capability",
                            "intent": "run_child_capability",
                            "expected_artifact": "child capability result",
                            "prompt": "Use the parent skill suite to run child capabilities.",
                            "done_when": ["Child capability result is recorded"],
                            "output_schema": {"child_result": "string"},
                            "failure_schema": {"blocked_reason": "string?"},
                            "skill_routing": [
                                {
                                    "skill": "example-child-reviewer",
                                    "operations": ["child review"],
                                    "file_patterns": ["docs/**/*.md"],
                                    "usage_notes": ["Run the child review capability."],
                                },
                                {
                                    "skill": "example-child-qa",
                                    "operations": ["child QA"],
                                    "file_patterns": ["docs/**/*.md"],
                                    "usage_notes": ["Run the child QA capability."],
                                },
                            ],
                        }
                    ],
                    "dependencies": [
                        {
                            "id": "example-child-reviewer",
                            "type": "skill",
                            "required": True,
                            "scope": "either",
                            "source": "skill-catalog:example-skill-suite/child-reviewer",
                            "purpose": "Run child review capability.",
                        }
                    ],
                    "installed": [
                        {
                            "id": "example-child-qa",
                            "type": "skill",
                            "scope": "either",
                            "source": "skill-catalog:example-skill-suite/child-qa",
                            "recorded_at": "2026-06-04T00:00:00Z",
                            "recorded_by": "workflow-creator",
                        }
                    ],
                },
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            workflow_dir = runtime_root / "workflow-runtime" / "workflows" / "child_skill_flow"
            manifest_payload = json.loads(
                (workflow_dir / "manifest.json").read_text(encoding="utf-8")
            )
            lockfile_payload = json.loads(
                (workflow_dir / ".workflow-lock.json").read_text(encoding="utf-8")
            )
            spec_payload = json.loads((workflow_dir / "spec.json").read_text(encoding="utf-8"))
            contract_text = (workflow_dir / "contract.py").read_text(encoding="utf-8")

            dependency_ids = [item["id"] for item in manifest_payload["dependencies"]]
            installed_ids = [item["id"] for item in lockfile_payload["installed"]]
            self.assertEqual(dependency_ids, ["example-skill-suite"])
            self.assertEqual(installed_ids, ["example-skill-suite"])
            self.assertEqual(
                manifest_payload["dependencies"][0]["source"],
                "skill-catalog:example-skill-suite",
            )
            routed_skills = [
                route["skill"]
                for stage in spec_payload["stages"]
                for route in stage["skill_routing"]
            ]
            self.assertEqual(routed_skills, ["example-skill-suite", "example-skill-suite"])
            self.assertIn("skill='example-skill-suite'", contract_text)
            self.assertNotIn("example-child-reviewer", contract_text)
            self.assertNotIn("example-child-qa", contract_text)

    def test_workflow_creator_cli_generates_business_workflow_from_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="paper_review_flow",
                flow_description="Review academic paper drafts through structured reviewer stages.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            spec_payload = {
                "workflow_id": "paper_review_flow",
                "flow_description": "Review academic paper drafts through structured reviewer stages.",
                "start_input_schema": {
                    "task_input": {
                        "goal": "string",
                        "manuscript_path": "string?",
                    },
                    "context": {"repo_root": "string"},
                    "constraints": {"max_steps": "integer?"},
                },
                "stages": [
                    {
                        "step_id": "collect_review_context",
                        "intent": "collect_review_context",
                        "expected_artifact": "review scope and manuscript context",
                        "prompt": "Collect manuscript context, target venue, criteria, and missing inputs.",
                        "done_when": [
                            "Review scope is clear",
                            "Missing inputs are listed or confirmed absent",
                        ],
                        "output_schema": {
                            "review_scope": "string",
                            "missing_inputs": "string[]",
                            "ready_for_critique": "boolean",
                        },
                        "transitions": [
                            {
                                "output_key": "ready_for_critique",
                                "operator": "is_false",
                                "next_node": "collect_review_context",
                                "branch_kind": "retry",
                                "reason": "review context needs another intake pass",
                            }
                        ],
                        "failure_schema": {
                            "blocked_reason": "string?",
                            "error_message": "string?",
                        },
                    },
                    {
                        "step_id": "run_structured_critique",
                        "intent": "run_structured_critique",
                        "expected_artifact": "structured critique findings",
                        "prompt": "Review claims, evidence, structure, method, and revision risks.",
                        "done_when": [
                            "Findings are grouped by severity",
                            "Each finding has evidence and an action",
                        ],
                        "output_schema": {
                            "findings": "string[]",
                            "overall_risk": "string",
                            "ready_for_synthesis": "boolean",
                        },
                        "verifier_rules": [
                            {
                                "output_key": "findings",
                                "operator": "non_empty",
                                "message": "findings must not be empty",
                            },
                            {
                                "output_key": "overall_risk",
                                "operator": "one_of",
                                "value": ["low", "medium", "high"],
                                "message": "overall_risk must be low, medium, or high",
                            },
                        ],
                        "verifier_templates": [
                            {
                                "id": "findings_have_min_count",
                                "template": "min_count",
                                "output_key": "findings",
                                "min_count": 1,
                                "message": "findings must include at least one summary string",
                            }
                        ],
                        "custom_verifier_requirements": [
                            {
                                "id": "synthesis_requires_findings_when_ready",
                                "description": "When ready_for_synthesis is true, findings must remain populated after all critique transformations.",
                                "signals": ["ready_for_synthesis", "findings"],
                                "implementation_surface": ["verifier", "tests"],
                                "implementation_notes": "Tighten this scaffold if later critique stages can accidentally drop findings while preserving the success flag.",
                                "hint_pseudocode": [
                                    "if output.ready_for_synthesis is true and findings is empty: fail",
                                ],
                                "test_intent": [
                                    "rejects succeeded outputs that claim synthesis readiness with empty findings",
                                ],
                            }
                        ],
                        "outcome_routes": [
                            {
                                "outcome": "verifier_failed",
                                "next_node": "repair_structured_critique",
                                "branch_kind": "repair",
                                "reason": "critique verifier failed; route to critique-specific repair",
                            }
                        ],
                        "failure_schema": {
                            "blocked_reason": "string?",
                            "error_message": "string?",
                        },
                    },
                    {
                        "step_id": "repair_structured_critique",
                        "stage_kind": "recovery",
                        "recovery_return_node": "run_structured_critique",
                        "intent": "repair_structured_critique",
                        "expected_artifact": "repaired structured critique findings",
                        "prompt": "Repair structured critique findings and rerun the critique verifier.",
                        "done_when": [
                            "Critique findings have the required evidence fields",
                            "The critique can be rechecked",
                        ],
                        "output_schema": {
                            "repair_summary": "string",
                        },
                        "failure_schema": {
                            "blocked_reason": "string?",
                            "error_message": "string?",
                        },
                    },
                ],
                "final_step_id": "finalize_review_report",
                "final_prompt": "Prepare the final review report and summarize follow-up actions.",
                "regression_tests": [
                    {
                        "name": "context_not_ready_routes_to_context",
                        "type": "transition",
                        "current_step_id": "collect_review_context",
                        "observation": {
                            "status": "succeeded",
                            "summary": "Context still needs source text.",
                            "structured_output": {
                                "review_scope": "Draft review",
                                "missing_inputs": ["manuscript"],
                                "ready_for_critique": False,
                            },
                        },
                        "expected_next_node": "collect_review_context",
                        "expected_branch_kind": "retry",
                    },
                    {
                        "name": "critique_rejects_unknown_risk",
                        "type": "verifier",
                        "step_id": "run_structured_critique",
                        "observation": {
                            "status": "succeeded",
                            "summary": "Critique done.",
                            "structured_output": {
                                "findings": [],
                                "overall_risk": "unknown",
                                "ready_for_synthesis": True,
                            },
                        },
                        "expected_passed": False,
                    },
                    {
                        "name": "critique_rejects_missing_finding_fields",
                        "type": "verifier",
                        "step_id": "run_structured_critique",
                        "observation": {
                            "status": "succeeded",
                            "summary": "Critique done.",
                            "structured_output": {
                                "findings": [{"id": "F1", "severity": "major"}],
                                "overall_risk": "medium",
                                "ready_for_synthesis": True,
                            },
                        },
                        "expected_passed": False,
                    },
                    {
                        "name": "critique_verifier_failed_routes_to_repair",
                        "type": "transition",
                        "current_step_id": "run_structured_critique",
                        "observation": {
                            "status": "succeeded",
                            "summary": "Critique done.",
                            "structured_output": {
                                "findings": [
                                    {
                                        "id": "F1",
                                        "severity": "major",
                                        "evidence": "Claim lacks support.",
                                        "action": "Add evidence.",
                                    }
                                ],
                                "overall_risk": "medium",
                                "ready_for_synthesis": True,
                            },
                        },
                        "verifier_result": {
                            "passed": False,
                            "message": "critique verifier failed",
                        },
                        "expected_next_node": "repair_structured_critique",
                        "expected_branch_kind": "repair",
                    },
                    {
                        "name": "critique_partial_uses_shared_repair_default",
                        "type": "transition",
                        "current_step_id": "run_structured_critique",
                        "observation": {
                            "status": "partial",
                            "summary": "Critique only partially completed.",
                            "structured_output": {},
                        },
                        "expected_next_node": "repair_and_resume",
                        "expected_branch_kind": "retry",
                    },
                    {
                        "name": "recovery_success_returns_to_critique",
                        "type": "transition",
                        "current_step_id": "repair_structured_critique",
                        "observation": {
                            "status": "succeeded",
                            "summary": "Critique repair completed.",
                            "structured_output": {
                                "repair_summary": "Added missing finding evidence.",
                            },
                        },
                        "expected_next_node": "run_structured_critique",
                        "expected_branch_kind": "continue",
                    },
                ],
            }

            result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="paper_review_flow",
                spec_payload=spec_payload,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            workflow_dir = runtime_root / "workflow-runtime" / "workflows" / "paper_review_flow"
            contract_text = (workflow_dir / "contract.py").read_text(encoding="utf-8")
            policy_text = (workflow_dir / "policy.py").read_text(encoding="utf-8")
            graph_text = (workflow_dir / "graphbuilder_runtime.py").read_text(encoding="utf-8")
            verifier_text = (workflow_dir / "verifiers.py").read_text(encoding="utf-8")
            flowchart_text = (workflow_dir / "references" / "flowchart.md").read_text(
                encoding="utf-8"
            )
            generated_test_path = workflow_dir / "tests" / "test_workflow.py"
            generated_test_text = generated_test_path.read_text(encoding="utf-8")
            spec_blueprint = json.loads((workflow_dir / "spec.json").read_text(encoding="utf-8"))

            self.assertEqual(
                payload["spec_blueprint_file"],
                str((workflow_dir / "spec.json").resolve()),
            )
            self.assertIn(
                "Translate any generated custom verifier scaffolds and domain-specific routing needs into concrete workflow code before review sign-off.",
                payload["next_actions"],
            )
            self.assertEqual(spec_blueprint["workflow_id"], "paper_review_flow")
            self.assertEqual(spec_blueprint["final_step_id"], "finalize_review_report")
            self.assertEqual(
                [stage["step_id"] for stage in spec_blueprint["stages"]],
                [
                    "collect_review_context",
                    "run_structured_critique",
                    "repair_structured_critique",
                ],
            )
            self.assertEqual(spec_blueprint["dependencies"], [])
            self.assertEqual(spec_blueprint["installed"], [])
            self.assertIn("COLLECT_REVIEW_CONTEXT = StepContract", contract_text)
            self.assertIn("RUN_STRUCTURED_CRITIQUE = StepContract", contract_text)
            self.assertIn("verify_collect_review_context", contract_text)
            self.assertIn('next_node="run_structured_critique"', policy_text)
            self.assertIn('next_node="finalize_review_report"', policy_text)
            self.assertIn("critique verifier failed; route to critique-specific repair", policy_text)
            self.assertIn("next_node='repair_structured_critique'", policy_text)
            self.assertIn('next_node="run_structured_critique"', policy_text)
            self.assertIn("review context needs another intake pass", policy_text)
            self.assertIn("next_node='collect_review_context'", policy_text)
            self.assertIn('"collect_review_context": NodeDefinition', graph_text)
            self.assertIn('prompt_asset_path=PROMPTS_DIR / "run_structured_critique.md"', graph_text)
            self.assertIn('"repair_structured_critique": NodeDefinition', graph_text)
            self.assertIn("def verify_run_structured_critique", verifier_text)
            self.assertIn("overall_risk must be low, medium, or high", verifier_text)
            self.assertIn("operator == \"one_of\"", verifier_text)
            self.assertIn("findings_have_min_count", verifier_text)
            self.assertIn("template_name == \"min_count\"", verifier_text)
            self.assertIn(
                "def _run_custom_verifier_requirements_run_structured_critique(",
                verifier_text,
            )
            self.assertIn(
                "def _custom_verifier_requirement_run_structured_critique_synthesis_requires_findings_when_ready(",
                verifier_text,
            )
            self.assertIn(
                "TODO(custom_verifier_requirement): Implement `synthesis_requires_findings_when_ready`.",
                verifier_text,
            )
            self.assertIn(
                "Self-contained contract: keep this requirement-scoped verifier self-contained when practical.",
                verifier_text,
            )
            self.assertIn("Implementation surfaces: verifier, tests", verifier_text)
            self.assertIn(
                "# - if output.ready_for_synthesis is true and findings is empty: fail",
                verifier_text,
            )
            self.assertIn(
                "# - rejects succeeded outputs that claim synthesis readiness with empty findings",
                verifier_text,
            )
            self.assertIn("def _meaningful_entries(value) -> list[str]:", verifier_text)
            self.assertIn("def _extract_single_review_perspective(text: str) -> str | None:", verifier_text)
            self.assertIn("def _looks_like_visual_evidence(text: str) -> bool:", verifier_text)
            self.assertIn("def _severity_rank(severity: str) -> int:", verifier_text)
            self.assertIn("collect_review_context -->|success| run_structured_critique", flowchart_text)
            self.assertIn("run_structured_critique -->|success| finalize_review_report", flowchart_text)
            self.assertNotIn("run_structured_critique -->|success| repair_structured_critique", flowchart_text)
            self.assertIn("run_structured_critique -->|verifier_failed| repair_structured_critique", flowchart_text)
            self.assertIn("repair_structured_critique -->|recovery complete| run_structured_critique", flowchart_text)
            self.assertIn("unblock_loop[[request_unblocking_input]]", flowchart_text)
            self.assertIn("repair_loop[[repair_and_resume]]", flowchart_text)
            self.assertIn("collect_review_context -.->|blocked| repair_loop", flowchart_text)
            self.assertIn("repair_structured_critique -.->|blocked| repair_loop", flowchart_text)
            self.assertIn("collect_review_context -->|ready_for_critique is_false|", flowchart_text)
            self.assertIn("## Stage Responsibilities", flowchart_text)
            self.assertIn("collect_review_context[collect_review_context]", flowchart_text)
            self.assertIn("run_structured_critique[run_structured_critique]", flowchart_text)
            self.assertIn("repair_structured_critique[repair_structured_critique]", flowchart_text)
            self.assertNotIn('collect_review_context["collect_review_context<br/>', flowchart_text)
            self.assertIn("| `collect_review_context` |", flowchart_text)
            self.assertIn("Collect manuscript context, target venue, criteria, and missing inputs.", flowchart_text)
            self.assertIn("review scope and manuscript context", flowchart_text)
            self.assertTrue((workflow_dir / "prompts" / "collect_review_context.md").exists())
            self.assertTrue((workflow_dir / "prompts" / "run_structured_critique.md").exists())
            self.assertTrue((workflow_dir / "prompts" / "repair_structured_critique.md").exists())
            self.assertTrue((workflow_dir / "prompts" / "finalize_review_report.md").exists())
            self.assertTrue(generated_test_path.exists())
            self.assertIn("test_context_not_ready_routes_to_context", generated_test_text)
            self.assertIn("test_critique_rejects_unknown_risk", generated_test_text)
            self.assertIn("test_critique_rejects_missing_finding_fields", generated_test_text)
            self.assertIn("test_critique_verifier_failed_routes_to_repair", generated_test_text)
            self.assertIn("test_critique_partial_uses_shared_repair_default", generated_test_text)
            self.assertIn("test_recovery_success_returns_to_critique", generated_test_text)
            self.assertIn("test_generated_request_unblocking_input_resumes_to_return_stage", generated_test_text)
            self.assertIn("test_generated_request_unblocking_input_returns_to_repair_owner", generated_test_text)
            self.assertIn("test_generated_repair_and_resume_without_return_stage_stays_put", generated_test_text)
            self.assertIn("test_generated_repair_and_resume_blocked_before_threshold_retries_locally", generated_test_text)
            self.assertIn("test_generated_repair_and_resume_blocked_after_threshold_requests_unblocking", generated_test_text)
            self.assertIn(
                "test_generated_blocked_repair_context_preserves_host_visible_summary",
                generated_test_text,
            )
            self.assertIn("repo_root=str(REPO_ROOT)", generated_test_text)
            self.assertNotIn("run_primary_stage", contract_text)
            self.assertNotIn('next_node=state.get("return_stage_id") or', policy_text)

            py_files = [
                workflow_dir / "contract.py",
                workflow_dir / "state.py",
                workflow_dir / "policy.py",
                workflow_dir / "graphbuilder_runtime.py",
                workflow_dir / "verifiers.py",
                generated_test_path,
            ]
            compile_result = subprocess.run(
                [sys.executable, "-m", "py_compile", *[str(path) for path in py_files]],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(compile_result.returncode, 0, msg=compile_result.stderr)

            shutil.copytree(
                RUNTIME_ROOT / "runtime",
                runtime_root / "workflow-runtime" / "runtime",
            )
            shutil.copytree(
                RUNTIME_ROOT / "workflows" / "common",
                runtime_root / "workflow-runtime" / "workflows" / "common",
            )
            shutil.copy2(
                RUNTIME_ROOT / "workflows" / "__init__.py",
                runtime_root / "workflow-runtime" / "workflows" / "__init__.py",
            )
            generated_test_paths = [
                str(runtime_root / "workflow-runtime"),
                str(RUNTIME_ROOT),
            ]
            if VENV_SITE_PACKAGES is not None:
                generated_test_paths.append(str(VENV_SITE_PACKAGES))
            generated_test_env = {
                **os.environ,
                "PYTHONPATH": ":".join(
                    generated_test_paths
                    + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])
                ),
            }
            generated_test_result = subprocess.run(
                [sys.executable, str(generated_test_path)],
                cwd=runtime_root,
                capture_output=True,
                text=True,
                env=generated_test_env,
            )
            self.assertEqual(
                generated_test_result.returncode,
                0,
                msg=generated_test_result.stderr,
            )

            blocked_runtime_result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "\n".join(
                        [
                            "import json",
                            "from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine",
                            f"engine = GraphBuilderRuntimeEngine({str(runtime_root)!r})",
                            "response = engine.start(",
                            "    'paper_review_flow',",
                            "    {'task_input': {'goal': 'generated workflow regression'}, 'context': {'repo_root': "
                            + repr(str(runtime_root))
                            + "}, 'constraints': {'max_steps': 5}},",
                            ")",
                            "run_id = response['run_id']",
                            "response = engine.resume(",
                            "    run_id,",
                            "    {",
                            "        'run_id': run_id,",
                            "        'step_id': 'collect_review_context',",
                            "        'status': 'blocked',",
                            "        'summary': 'Need manuscript before context collection can continue.',",
                            "        'structured_output': {'blocked_reason': 'awaiting manuscript', 'missing_inputs': ['manuscript']},",
                            "        'artifacts': [],",
                            "        'error': None,",
                            "        'tool_trace': [],",
                            "        'raw_output': '',",
                            "    },",
                            ")",
                            "print(json.dumps(response, ensure_ascii=False))",
                        ]
                    ),
                ],
                cwd=runtime_root,
                capture_output=True,
                text=True,
                env=generated_test_env,
            )
            self.assertEqual(blocked_runtime_result.returncode, 0, msg=blocked_runtime_result.stderr)
            blocked_runtime_payload = json.loads(blocked_runtime_result.stdout)
            self.assertEqual(blocked_runtime_payload["kind"], "yield")
            self.assertEqual(blocked_runtime_payload["step_id"], "repair_and_resume")
            self.assertEqual(blocked_runtime_payload["retry_context"]["category"], "blocked")
            self.assertEqual(blocked_runtime_payload["retry_context"]["summary"], "awaiting manuscript")
            self.assertEqual(
                blocked_runtime_payload["retry_context"]["requirements"],
                ["manuscript"],
            )

            verifier_runtime_result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "\n".join(
                        [
                            "import json",
                            "from runtime.engine_graphbuilder import GraphBuilderRuntimeEngine",
                            f"engine = GraphBuilderRuntimeEngine({str(runtime_root)!r})",
                            "response = engine.start(",
                            "    'paper_review_flow',",
                            "    {'task_input': {'goal': 'generated workflow regression'}, 'context': {'repo_root': "
                            + repr(str(runtime_root))
                            + "}, 'constraints': {'max_steps': 5}},",
                            ")",
                            "run_id = response['run_id']",
                            "response = engine.resume(",
                            "    run_id,",
                            "    {",
                            "        'run_id': run_id,",
                            "        'step_id': 'collect_review_context',",
                            "        'status': 'succeeded',",
                            "        'summary': 'Context is ready for critique.',",
                            "        'structured_output': {'review_scope': 'Draft review', 'missing_inputs': [], 'ready_for_critique': True},",
                            "        'artifacts': [],",
                            "        'error': None,",
                            "        'tool_trace': [],",
                            "        'raw_output': '',",
                            "    },",
                            ")",
                            "response = engine.resume(",
                            "    run_id,",
                            "    {",
                            "        'run_id': run_id,",
                            "        'step_id': 'run_structured_critique',",
                            "        'status': 'succeeded',",
                            "        'summary': 'Critique done but risk classification is invalid.',",
                            "        'structured_output': {'findings': ['Claim lacks support.'], 'overall_risk': 'unknown', 'ready_for_synthesis': True},",
                            "        'artifacts': [],",
                            "        'error': None,",
                            "        'tool_trace': [],",
                            "        'raw_output': '',",
                            "    },",
                            ")",
                            "print(json.dumps(response, ensure_ascii=False))",
                        ]
                    ),
                ],
                cwd=runtime_root,
                capture_output=True,
                text=True,
                env=generated_test_env,
            )
            self.assertEqual(verifier_runtime_result.returncode, 0, msg=verifier_runtime_result.stderr)
            verifier_runtime_payload = json.loads(verifier_runtime_result.stdout)
            self.assertEqual(verifier_runtime_payload["kind"], "yield")
            self.assertEqual(verifier_runtime_payload["step_id"], "repair_structured_critique")
            self.assertEqual(
                verifier_runtime_payload["retry_context"]["category"],
                "verifier_failed",
            )
            self.assertIn(
                "overall_risk must be low, medium, or high",
                verifier_runtime_payload["retry_context"]["summary"],
            )
            self.assertIn(
                "overall_risk must be low, medium, or high",
                verifier_runtime_payload["retry_context"]["requirements"][0],
            )

    def test_workflow_creator_preserves_custom_verifier_body_when_requirement_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="incremental_verifier_flow",
                flow_description="Exercise incremental verifier preservation.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            spec_payload = self._custom_verifier_workflow_spec(
                workflow_id="incremental_verifier_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                        "signals": ["design_doc_path", "design_ready"],
                        "implementation_surface": ["verifier", "tests"],
                        "hint_pseudocode": [
                            "if output.design_ready is true and design_doc_path is empty: fail",
                        ],
                        "test_intent": [
                            "rejects ready outputs that omit the generated design doc path",
                        ],
                    }
                ],
            )
            first_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="incremental_verifier_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(first_result.returncode, 0, msg=first_result.stderr)

            verifier_path = (
                runtime_root
                / "workflow-runtime"
                / "workflows"
                / "incremental_verifier_flow"
                / "verifiers.py"
            )
            original_text = verifier_path.read_text(encoding="utf-8")
            edited_text = original_text.replace(
                "    _ = output, state, repo_root\n"
                "    # TODO(custom_verifier_requirement): Implement `design_doc_matches_contract`.\n",
                "    _ = output, state, repo_root\n"
                "    if output.get(\"design_ready\") and not output.get(\"design_doc_path\"):\n"
                "        return \"design_doc_path is required when design_ready is true\"\n",
                1,
            )
            verifier_path.write_text(edited_text, encoding="utf-8")

            second_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="incremental_verifier_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(second_result.returncode, 0, msg=second_result.stderr)
            payload = json.loads(second_result.stdout)
            self.assertEqual(payload["warnings"], [])
            preserved_text = verifier_path.read_text(encoding="utf-8")
            self.assertIn(
                'return "design_doc_path is required when design_ready is true"',
                preserved_text,
            )
            self.assertIn("# spec_fingerprint:", preserved_text)
            self.assertIn("# implementation_version: none", preserved_text)

    def test_workflow_creator_regenerates_custom_verifier_body_when_requirement_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="changed_verifier_flow",
                flow_description="Exercise verifier invalidation on spec change.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            base_spec = self._custom_verifier_workflow_spec(
                workflow_id="changed_verifier_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                    }
                ],
            )
            first_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="changed_verifier_flow",
                spec_payload=base_spec,
            )
            self.assertEqual(first_result.returncode, 0, msg=first_result.stderr)

            verifier_path = (
                runtime_root
                / "workflow-runtime"
                / "workflows"
                / "changed_verifier_flow"
                / "verifiers.py"
            )
            edited_text = verifier_path.read_text(encoding="utf-8").replace(
                "    _ = output, state, repo_root\n"
                "    # TODO(custom_verifier_requirement): Implement `design_doc_matches_contract`.\n",
                "    _ = output, state, repo_root\n"
                "    return \"manual implementation that should be invalidated\"\n",
                1,
            )
            verifier_path.write_text(edited_text, encoding="utf-8")

            changed_spec = self._custom_verifier_workflow_spec(
                workflow_id="changed_verifier_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a non-empty design doc path and matching readiness summary.",
                    }
                ],
            )
            second_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="changed_verifier_flow",
                spec_payload=changed_spec,
            )
            self.assertEqual(second_result.returncode, 0, msg=second_result.stderr)
            regenerated_text = verifier_path.read_text(encoding="utf-8")
            self.assertNotIn("manual implementation that should be invalidated", regenerated_text)
            self.assertIn(
                "TODO(custom_verifier_requirement): Implement `design_doc_matches_contract`.",
                regenerated_text,
            )

    def test_workflow_creator_regenerates_custom_verifier_body_when_implementation_version_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="implementation_version_flow",
                flow_description="Exercise explicit implementation version invalidation.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            spec_v1 = self._custom_verifier_workflow_spec(
                workflow_id="implementation_version_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                        "implementation_version": 1,
                    }
                ],
            )
            first_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="implementation_version_flow",
                spec_payload=spec_v1,
            )
            self.assertEqual(first_result.returncode, 0, msg=first_result.stderr)

            verifier_path = (
                runtime_root
                / "workflow-runtime"
                / "workflows"
                / "implementation_version_flow"
                / "verifiers.py"
            )
            edited_text = verifier_path.read_text(encoding="utf-8").replace(
                "    _ = output, state, repo_root\n"
                "    # TODO(custom_verifier_requirement): Implement `design_doc_matches_contract`.\n",
                "    _ = output, state, repo_root\n"
                "    return \"manual implementation for v1\"\n",
                1,
            )
            verifier_path.write_text(edited_text, encoding="utf-8")

            spec_v2 = self._custom_verifier_workflow_spec(
                workflow_id="implementation_version_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                        "implementation_version": 2,
                    }
                ],
            )
            second_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="implementation_version_flow",
                spec_payload=spec_v2,
            )
            self.assertEqual(second_result.returncode, 0, msg=second_result.stderr)
            regenerated_text = verifier_path.read_text(encoding="utf-8")
            self.assertNotIn("manual implementation for v1", regenerated_text)
            self.assertIn("# implementation_version: 2", regenerated_text)

    def test_workflow_creator_adds_and_removes_custom_verifier_scaffolds_incrementally(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="add_remove_verifier_flow",
                flow_description="Exercise custom verifier add/remove behavior.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            initial_spec = self._custom_verifier_workflow_spec(
                workflow_id="add_remove_verifier_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                    }
                ],
            )
            first_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="add_remove_verifier_flow",
                spec_payload=initial_spec,
            )
            self.assertEqual(first_result.returncode, 0, msg=first_result.stderr)

            verifier_path = (
                runtime_root
                / "workflow-runtime"
                / "workflows"
                / "add_remove_verifier_flow"
                / "verifiers.py"
            )
            edited_text = verifier_path.read_text(encoding="utf-8").replace(
                "    _ = output, state, repo_root\n"
                "    # TODO(custom_verifier_requirement): Implement `design_doc_matches_contract`.\n",
                "    _ = output, state, repo_root\n"
                "    return \"preserved implementation\"\n",
                1,
            )
            verifier_path.write_text(edited_text, encoding="utf-8")

            expanded_spec = self._custom_verifier_workflow_spec(
                workflow_id="add_remove_verifier_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                    },
                    {
                        "id": "design_summary_exists",
                        "description": "Require a design summary artifact before the review can pass.",
                    },
                ],
            )
            second_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="add_remove_verifier_flow",
                spec_payload=expanded_spec,
            )
            self.assertEqual(second_result.returncode, 0, msg=second_result.stderr)
            expanded_text = verifier_path.read_text(encoding="utf-8")
            self.assertIn("preserved implementation", expanded_text)
            self.assertIn(
                "TODO(custom_verifier_requirement): Implement `design_summary_exists`.",
                expanded_text,
            )

            reduced_spec = self._custom_verifier_workflow_spec(
                workflow_id="add_remove_verifier_flow",
                requirements=[
                    {
                        "id": "design_summary_exists",
                        "description": "Require a design summary artifact before the review can pass.",
                    }
                ],
            )
            third_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="add_remove_verifier_flow",
                spec_payload=reduced_spec,
            )
            self.assertEqual(third_result.returncode, 0, msg=third_result.stderr)
            reduced_payload = json.loads(third_result.stdout)
            reduced_text = verifier_path.read_text(encoding="utf-8")
            self.assertNotIn("preserved implementation", reduced_text)
            self.assertIn(
                "Removed preserved custom verifier implementation because the requirement no longer exists in spec.json",
                "\n".join(reduced_payload["warnings"]),
            )

    def test_workflow_creator_warns_and_regenerates_when_custom_verifier_metadata_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="malformed_metadata_flow",
                flow_description="Exercise metadata upgrade fallback behavior.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            spec_payload = self._custom_verifier_workflow_spec(
                workflow_id="malformed_metadata_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                    }
                ],
            )
            first_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="malformed_metadata_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(first_result.returncode, 0, msg=first_result.stderr)

            verifier_path = (
                runtime_root
                / "workflow-runtime"
                / "workflows"
                / "malformed_metadata_flow"
                / "verifiers.py"
            )
            malformed_text = verifier_path.read_text(encoding="utf-8").replace(
                "# spec_fingerprint:",
                "# spec_fingerprint_removed:",
                1,
            )
            verifier_path.write_text(malformed_text, encoding="utf-8")

            second_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="malformed_metadata_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(second_result.returncode, 0, msg=second_result.stderr)
            payload = json.loads(second_result.stdout)
            self.assertIn(
                "Regenerated custom verifier scaffold because preservation metadata was missing or malformed",
                "\n".join(payload["warnings"]),
            )
            regenerated_text = verifier_path.read_text(encoding="utf-8")
            self.assertIn(
                "TODO(custom_verifier_requirement): Implement `design_doc_matches_contract`.",
                regenerated_text,
            )

    def test_workflow_creator_migrates_legacy_custom_verifier_without_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="legacy_metadata_flow",
                flow_description="Exercise legacy custom verifier metadata migration.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            spec_payload = self._custom_verifier_workflow_spec(
                workflow_id="legacy_metadata_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                    }
                ],
            )
            first_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="legacy_metadata_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(first_result.returncode, 0, msg=first_result.stderr)

            verifier_path = (
                runtime_root
                / "workflow-runtime"
                / "workflows"
                / "legacy_metadata_flow"
                / "verifiers.py"
            )
            legacy_lines = [
                line
                for line in verifier_path.read_text(encoding="utf-8").splitlines()
                if not line.startswith("# custom_verifier_")
                and not line.startswith("# template_version:")
                and not line.startswith("# spec_fingerprint:")
                and not line.startswith("# implementation_version:")
            ]
            legacy_text = "\n".join(legacy_lines) + "\n"
            legacy_text = legacy_text.replace(
                "    _ = output, state, repo_root\n"
                "    # TODO(custom_verifier_requirement): Implement `design_doc_matches_contract`.\n",
                "    _ = output, state, repo_root\n"
                "    if output.get(\"design_ready\") and not output.get(\"design_doc_path\"):\n"
                "        return \"design_doc_path is required when design_ready is true\"\n",
                1,
            )
            verifier_path.write_text(legacy_text, encoding="utf-8")

            second_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="legacy_metadata_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(second_result.returncode, 0, msg=second_result.stderr)
            payload = json.loads(second_result.stdout)
            self.assertIn(
                "Migrated legacy custom verifier implementation without preservation metadata for "
                "review_design_doc.design_doc_matches_contract",
                "\n".join(payload["warnings"]),
            )
            migrated_text = verifier_path.read_text(encoding="utf-8")
            self.assertIn("# spec_fingerprint:", migrated_text)
            self.assertIn(
                'return "design_doc_path is required when design_ready is true"',
                migrated_text,
            )

    def test_workflow_creator_cli_migrates_legacy_custom_verifier_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="legacy_metadata_cli_flow",
                flow_description="Exercise CLI legacy custom verifier metadata migration.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            spec_payload = self._custom_verifier_workflow_spec(
                workflow_id="legacy_metadata_cli_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                    }
                ],
            )
            first_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="legacy_metadata_cli_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(first_result.returncode, 0, msg=first_result.stderr)

            verifier_path = (
                runtime_root
                / "workflow-runtime"
                / "workflows"
                / "legacy_metadata_cli_flow"
                / "verifiers.py"
            )
            legacy_lines = [
                line
                for line in verifier_path.read_text(encoding="utf-8").splitlines()
                if not line.startswith("# custom_verifier_")
                and not line.startswith("# template_version:")
                and not line.startswith("# spec_fingerprint:")
                and not line.startswith("# implementation_version:")
            ]
            verifier_path.write_text("\n".join(legacy_lines) + "\n", encoding="utf-8")

            migrate_result = subprocess.run(
                [
                    sys.executable,
                    str(CREATE_WORKFLOW_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--workflow-id",
                    "legacy_metadata_cli_flow",
                    "--migrate-legacy-custom-verifier-metadata",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(migrate_result.returncode, 0, msg=migrate_result.stderr)
            payload = json.loads(migrate_result.stdout)
            self.assertEqual(payload["kind"], "legacy_custom_verifier_metadata_migration")
            self.assertEqual(payload["migrated_workflows"], ["legacy_metadata_cli_flow"])
            migrated_text = verifier_path.read_text(encoding="utf-8")
            self.assertIn("# spec_fingerprint:", migrated_text)

    def test_workflow_creator_cli_migration_scan_filters_to_workflow_dirs_with_spec_and_verifiers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_root = Path(tmpdir) / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            create_result = self._create_creator_workflow_scaffold(
                runtime_root,
                workflow_id="eligible_flow",
                flow_description="Exercise migration scan filtering.",
            )
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr)

            spec_payload = self._custom_verifier_workflow_spec(
                workflow_id="eligible_flow",
                requirements=[
                    {
                        "id": "design_doc_matches_contract",
                        "description": "Require a design doc path whenever the design is marked ready.",
                    }
                ],
            )
            regen_result = self._regenerate_creator_workflow_from_spec(
                runtime_root,
                workflow_id="eligible_flow",
                spec_payload=spec_payload,
            )
            self.assertEqual(regen_result.returncode, 0, msg=regen_result.stderr)

            (runtime_root / "workflow-runtime" / "workflows" / "common").mkdir()
            (runtime_root / "workflow-runtime" / "workflows" / "common" / "__init__.py").write_text(
                "",
                encoding="utf-8",
            )
            (runtime_root / "workflow-runtime" / "workflows" / "old_flow").mkdir()
            (runtime_root / "workflow-runtime" / "workflows" / "old_flow" / "verifiers.py").write_text(
                "from __future__ import annotations\n",
                encoding="utf-8",
            )

            migrate_result = subprocess.run(
                [
                    sys.executable,
                    str(CREATE_WORKFLOW_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--migrate-legacy-custom-verifier-metadata",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(migrate_result.returncode, 0, msg=migrate_result.stderr)
            payload = json.loads(migrate_result.stdout)
            self.assertEqual(payload["scanned_workflows"], ["eligible_flow"])
            self.assertNotIn("common", payload["scanned_workflows"])
            self.assertNotIn("old_flow", payload["scanned_workflows"])

    def test_workflow_creator_cli_rejects_existing_workflow_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)
            (runtime_root / "workflow-runtime" / "workflows" / "paper_review_flow").mkdir()

            result = subprocess.run(
                [
                    sys.executable,
                    str(CREATE_WORKFLOW_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--workflow-id",
                    "paper_review_flow",
                    "--flow-description",
                    "Review academic paper drafts through structured reviewer stages.",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("workflow already exists", result.stderr)

    def test_workflow_creator_cli_rejects_non_importable_workflow_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            runtime_root = tmpdir_path / "durable-workflow-runtime"
            self._write_test_creator_runtime(runtime_root)

            result = subprocess.run(
                [
                    sys.executable,
                    str(CREATE_WORKFLOW_PATH),
                    "--runtime-skill-root",
                    str(runtime_root),
                    "--workflow-id",
                    "paper-review-flow",
                    "--flow-description",
                    "Review academic paper drafts through structured reviewer stages.",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("Python package identifier", result.stderr)

    def test_bridge_start_writes_response_file(self) -> None:
        request_file, response_file = self._write_host_io_start_request(self._start_request())

        result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_PATH),
                "start",
                "--repo-root",
                str(REPO_ROOT),
                "--request-file",
                str(request_file),
                "--response-file",
                str(response_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(response_file.exists())

        response = json.loads(response_file.read_text(encoding="utf-8"))
        self.assertEqual(response["kind"], "yield")
        self.assertIn("status=yield", result.stdout)

    def test_bridge_start_rejects_request_file_outside_host_io(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            request_file = Path(tmpdir) / "start-request.json"
            response_file = self._pending_host_io_file("unsafe-request-response.json")
            request_file.write_text(
                json.dumps(self._start_request(), ensure_ascii=False),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(BRIDGE_PATH),
                    "start",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--request-file",
                    str(request_file),
                    "--response-file",
                    str(response_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 3)
            payload = json.loads(response_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "error")
            self.assertIn("request-file must be under", payload["message"])

    def test_bridge_start_rejects_response_file_outside_host_io_without_writing_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            request_file, _ = self._write_host_io_start_request(self._start_request())
            response_file = Path(tmpdir) / "response.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(BRIDGE_PATH),
                    "start",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--request-file",
                    str(request_file),
                    "--response-file",
                    str(response_file),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 3)
            self.assertFalse(response_file.exists())
            self.assertIn("response-file must be under", result.stderr)

    def test_bridge_start_allows_unsafe_paths_when_flag_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            request_file = tmpdir_path / "start-request.json"
            response_file = tmpdir_path / "response.json"
            request_file.write_text(
                json.dumps(self._start_request(), ensure_ascii=False),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(BRIDGE_PATH),
                    "start",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--request-file",
                    str(request_file),
                    "--response-file",
                    str(response_file),
                    "--allow-unsafe-host-io-paths",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            response = json.loads(response_file.read_text(encoding="utf-8"))
            self.assertEqual(response["kind"], "yield")

    def test_bridge_start_invalid_workflow_id_writes_error_response(self) -> None:
        request_file, response_file = self._write_host_io_start_request(
            self._start_request(),
            workflow_id="missing_workflow",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_PATH),
                "start",
                "--repo-root",
                str(REPO_ROOT),
                "--request-file",
                str(request_file),
                "--response-file",
                str(response_file),
                "--workflow-id",
                "missing_workflow",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(response_file.read_text(encoding="utf-8"))
        self.assertEqual(payload["kind"], "error")
        self.assertIn("status=error", result.stdout)

    @unittest.skipUnless(
        IOS_GOALS_WORKFLOW_DIR.is_dir(),
        "ios_goals workflow is not present in this checkout",
    )
    def test_bridge_preflight_install_deps_writes_response_file(self) -> None:
        self._hide_project_skill("ios-best-practices")
        self._hide_project_skill("software-design-philosophy")

        response_file = self._pending_host_io_file("ios_goals-preflight-response.json")

        result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_PATH),
                "preflight",
                "install-deps",
                "--repo-root",
                str(REPO_ROOT),
                "--workflow-id",
                "ios_goals",
                "--response-file",
                str(response_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(response_file.read_text(encoding="utf-8"))
        self.assertEqual(payload["kind"], "preflight_result")
        self.assertEqual(payload["workflow_id"], "ios_goals")
        self.assertEqual(payload["status"], "needs_install")
        self.assertIn("status=preflight", result.stdout)

    def test_bridge_resume_mismatched_run_id_writes_error_response(self) -> None:
        import host_io

        request_file, start_response_file = self._write_host_io_start_request(self._start_request())

        start_result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_PATH),
                "start",
                "--repo-root",
                str(REPO_ROOT),
                "--request-file",
                str(request_file),
                "--response-file",
                str(start_response_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(start_result.returncode, 0, msg=start_result.stderr)
        start_response = json.loads(start_response_file.read_text(encoding="utf-8"))

        observation_file = host_io.observation_path(
            REPO_ROOT,
            start_response["run_id"],
            start_response["step_id"],
            sequence=1,
        )
        resume_response_file = host_io.response_path(
            REPO_ROOT,
            start_response["run_id"],
            start_response["step_id"],
            sequence=2,
        )
        observation_file.write_text(
            json.dumps(
                {
                    "run_id": "wrong_run_id",
                    "step_id": start_response["step_id"],
                    "status": "blocked",
                    "summary": "run_id 不一致。",
                    "structured_output": {
                        "blocked_reason": "bad run id",
                        "error_message": "mismatch",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        resume_result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_PATH),
                "resume",
                "--repo-root",
                str(REPO_ROOT),
                "--run-id",
                start_response["run_id"],
                "--observation-file",
                str(observation_file),
                "--response-file",
                str(resume_response_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(resume_result.returncode, 6, msg=resume_result.stderr)
        payload = json.loads(resume_response_file.read_text(encoding="utf-8"))
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["error_type"], "validation_error")
        self.assertIn("status=error", resume_result.stdout)

    def test_bridge_resume_invalid_tool_trace_writes_error_response(self) -> None:
        import host_io

        request_file, start_response_file = self._write_host_io_start_request(self._start_request())

        start_result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_PATH),
                "start",
                "--repo-root",
                str(REPO_ROOT),
                "--request-file",
                str(request_file),
                "--response-file",
                str(start_response_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(start_result.returncode, 0, msg=start_result.stderr)
        start_response = json.loads(start_response_file.read_text(encoding="utf-8"))

        observation_file = host_io.observation_path(
            REPO_ROOT,
            start_response["run_id"],
            start_response["step_id"],
            sequence=1,
        )
        resume_response_file = host_io.response_path(
            REPO_ROOT,
            start_response["run_id"],
            start_response["step_id"],
            sequence=2,
        )
        observation_file.write_text(
            json.dumps(
                {
                    "run_id": start_response["run_id"],
                    "step_id": start_response["step_id"],
                    "status": "succeeded",
                    "summary": "tool trace shape is invalid.",
                    "structured_output": {
                        "runtime_exists": True,
                        "top_level_entries": ["adapters", "runtime", "workflows"],
                        "missing_paths": [],
                    },
                    "artifacts": [],
                    "error": None,
                    "tool_trace": [
                        {
                            "tool": "shell",
                            "action": "inspect_runtime_scaffold",
                        }
                    ],
                    "raw_output": "",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        resume_result = subprocess.run(
            [
                sys.executable,
                str(BRIDGE_PATH),
                "resume",
                "--repo-root",
                str(REPO_ROOT),
                "--run-id",
                start_response["run_id"],
                "--observation-file",
                str(observation_file),
                "--response-file",
                str(resume_response_file),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(resume_result.returncode, 6, msg=resume_result.stderr)
        payload = json.loads(resume_response_file.read_text(encoding="utf-8"))
        self.assertEqual(payload["kind"], "error")
        self.assertEqual(payload["error_type"], "validation_error")
        self.assertIn("ToolTraceEntry missing required fields", payload["message"])
        self.assertIn("status=error", resume_result.stdout)

    def test_shell_command_verifier_passes_on_zero_exit(self) -> None:
        from runtime.models import Observation, RunState
        from runtime.module_loader import load_workflow_modules
        from runtime.verifier_runner import run_step_verifier
        from workflows.common.contracts import StepVerifier

        modules = load_workflow_modules("demo_prompt_loop")
        run_state = RunState(
            run_id="run_shell_ok",
            workflow_id="demo_prompt_loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        observation = Observation.from_dict(
            {
                "run_id": "run_shell_ok",
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "shell verifier pass",
                "structured_output": {},
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            }
        )

        result = run_step_verifier(
            repo_root=str(REPO_ROOT),
            modules=modules,
            verifier=StepVerifier(
                kind="shell_command",
                ref=f"test -d {shlex.quote(str(RUNTIME_ROOT))}",
            ),
            run_state=run_state,
            observation=observation,
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["returncode"], 0)

    def test_shell_command_verifier_fails_on_non_zero_exit(self) -> None:
        from runtime.models import Observation, RunState
        from runtime.module_loader import load_workflow_modules
        from runtime.verifier_runner import run_step_verifier
        from workflows.common.contracts import StepVerifier

        modules = load_workflow_modules("demo_prompt_loop")
        run_state = RunState(
            run_id="run_shell_fail",
            workflow_id="demo_prompt_loop",
            workflow_version="v1",
            status="waiting_for_host",
            current_node="collect_context",
            graph_state={},
        )
        observation = Observation.from_dict(
            {
                "run_id": "run_shell_fail",
                "step_id": "collect_context",
                "status": "succeeded",
                "summary": "shell verifier fail",
                "structured_output": {},
                "artifacts": [],
                "error": None,
                "tool_trace": [],
                "raw_output": "",
            }
        )

        result = run_step_verifier(
            repo_root=str(REPO_ROOT),
            modules=modules,
            verifier=StepVerifier(kind="shell_command", ref="test -d definitely-missing-dir"),
            run_state=run_state,
            observation=observation,
        )

        self.assertFalse(result["passed"])
        self.assertNotEqual(result["details"]["returncode"], 0)


if __name__ == "__main__":
    unittest.main()
