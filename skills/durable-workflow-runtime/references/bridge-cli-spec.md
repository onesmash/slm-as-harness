# Bridge CLI Spec

Read this file when invoking or wrapping:

- `<skill-root>/scripts/bridge.py`
- a host loop that shells out to the bridge

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`. In this repo, `<skill-root>` currently resolves
to `.codex/skills/durable-workflow-runtime/`.

## Current scope

The bridge is a thin CLI adapter over the skill-bundled Python adapter:

```text
<skill-root>/workflow-runtime/adapters/skill_host.py
```

Current behavior:

- `start` accepts an optional `--workflow-id`
- if `--workflow-id` is omitted, the adapter falls back to
  `<skill-root>/workflow-binding.json.default_workflow_id`
- if `--workflow-id` is present, it must be both:
  - published in `workflow-binding.json.workflows[]`
  - loadable as a runtime workflow module
- `resume` does not accept `workflow_id`; it relies on persisted
  `RunState.workflow_id`

Skill-side mapping:

- callers may treat `workflow_id` as an optional parameter of
  `durable-workflow-runtime`
- that user-facing parameter maps directly onto this bridge flag
- no script change is required for that mapping; the wrapper contract just
  needs to forward it consistently

## Commands

### `start`

Allocate `--request-file` and `--response-file` with `scripts/host_io.py` before
calling the bridge. Normal bridge payloads must live under
`<repo-root>/.durable-workflow-runtime/host-io/`.

```bash
python3 <skill-root>/scripts/bridge.py start \
  --repo-root <repo-root> \
  --request-file <start-request.json> \
  --response-file <response.json> \
  --workflow-id <workflow-id-optional>
```

Required JSON top-level fields:

```json
{
  "task_input": {},
  "context": {},
  "constraints": {}
}
```

Minimal demo-workflow example:

```json
{
  "task_input": {
    "goal": "检查 skill bundle 自带的 workflow-runtime 骨架是否存在"
  },
  "context": {
    "repo_root": "/abs/path/to/repo"
  },
  "constraints": {
    "max_steps": 5
  }
}
```

Minimal explicit-selection example:

```bash
python3 <skill-root>/scripts/bridge.py start \
  --repo-root <repo-root> \
  --request-file <start-request.json> \
  --response-file <response.json> \
  --workflow-id superpowers_delivery_chain
```

### `resume`

Allocate `--observation-file` and `--response-file` with `scripts/host_io.py`
before calling the bridge.

```bash
python3 <skill-root>/scripts/bridge.py resume \
  --repo-root <repo-root> \
  --run-id <run-id> \
  --observation-file <observation.json> \
  --response-file <response.json>
```

Required JSON top-level fields:

```json
{
  "run_id": "string",
  "step_id": "string",
  "status": "succeeded | failed | blocked | partial",
  "summary": "string",
  "structured_output": {}
}
```

Minimal example:

```json
{
  "run_id": "run_123",
  "step_id": "collect_context",
  "status": "succeeded",
  "summary": "已确认 workflow-runtime 存在，并收集到一级目录。",
  "structured_output": {
    "runtime_exists": true,
    "top_level_entries": ["adapters", "runtime", "workflows"],
    "missing_paths": []
  },
  "artifacts": [],
  "error": null,
  "tool_trace": [],
  "raw_output": ""
}
```

This example keeps `tool_trace` empty on purpose. If you include structured
host trace, each entry must satisfy the `Observation` contract in
`references/observation-format.md`.

Structured trace example:

```json
{
  "run_id": "run_123",
  "step_id": "collect_context",
  "status": "succeeded",
  "summary": "已确认 workflow-runtime 存在，并收集到一级目录。",
  "structured_output": {
    "runtime_exists": true,
    "top_level_entries": ["adapters", "runtime", "workflows"],
    "missing_paths": []
  },
  "artifacts": [],
  "error": null,
  "tool_trace": [
    {
      "tool_name": "shell",
      "status": "succeeded",
      "input_summary": "ls workflow-runtime",
      "output_summary": "listed first-level entries",
      "artifact_refs": [],
      "metadata": {}
    }
  ],
  "raw_output": ""
}
```

## Success response kinds

The bridge writes a JSON object to `--response-file`.

### `yield`

The runtime needs host execution before it can continue.

```json
{
  "kind": "yield",
  "run_id": "run_123",
  "step_id": "collect_context",
  "retry_context": {
    "category": "verifier_failed",
    "summary": "Context inventory must include at least one authoritative source.",
    "requirements": [
      "Add at least one authoritative source before retrying collect_context."
    ]
  },
  "prompt_envelope": {
    "run_id": "run_123",
    "step_id": "collect_context",
    "prompt": "...",
    "intent": "collect_context",
    "expected_artifact": "runtime scaffold status",
    "done_when": ["..."],
    "output_schema": {},
    "failure_schema": {},
    "resume_instructions": "...",
    "metadata": {
      "workflow_id": "demo_prompt_loop",
      "workflow_version": "v1"
    }
  }
}
```

The host should execute the envelope, build an `Observation`, and call
`resume`.

Optional retry diagnostics:

- `retry_context` is optional
- when present, it is the compact host-visible explanation for why the runtime
  re-yielded a step without requiring the host to read
  `runs/<run_id>.json`
- current contract:
  - `category`: short machine-readable cause such as `verifier_failed` or
    `blocked`
  - `summary`: short human-readable root-cause summary
  - `requirements`: optional actionable repair requirements

Observability rule:

- `yield` without `retry_context`
  normal next-step yield unless the workflow deliberately reuses the same step
- `yield` with `retry_context.category == "verifier_failed"`
  verifier-driven retry; the host should surface the summary instead of
  misreading it as silent non-progress
- `Observation.status == "blocked"`
  host-side blocked outcome that should resume into a runtime-selected unblock
  route instead of being conflated with verifier retry

The host may use `retry_context` for diagnosis, user-facing explanation, and
repair-aware execution, but must not use it to invent new workflow branches.

Important selector rule:

- `workflow_id` is chosen at `start`
- `resume` must not try to change it

### `done`

The workflow has reached its terminal step.

```json
{
  "kind": "done",
  "run_id": "run_123",
  "step_id": "finalize_summary",
  "final_prompt_envelope": {
    "run_id": "run_123",
    "step_id": "finalize_summary",
    "prompt": "...",
    "intent": "finalize_summary",
    "expected_artifact": "final user-facing summary",
    "done_when": ["输出最终总结"],
    "output_schema": {},
    "failure_schema": {},
    "resume_instructions": "No further resume.",
    "metadata": {
      "workflow_id": "demo_prompt_loop",
      "workflow_version": "v1"
    }
  },
  "next_step_recommendations": {
    "kind": "workflow_catalog_lookup",
    "source_workflow_id": "demo_prompt_loop",
    "instructions": [
      "Read workflow-binding.json from the durable-workflow-runtime skill root before recommending the next workflow.",
      "Use catalog entry flow_description and start_input_schema to select a suitable workflow_id.",
      "Do not recommend the source_workflow_id unless the user explicitly wants to rerun it.",
      "If no workflow clearly fits, ask the user which workflow to start next.",
      "Start the selected workflow as a new run; do not call resume on the completed run."
    ]
  }
}
```

Important rule:

- execute `final_prompt_envelope` exactly once
- follow `next_step_recommendations.instructions` to inspect the workflow
  catalog before recommending a follow-up workflow
- do not call `resume` again after a terminal `done`

## Error response file

On failure, the bridge still tries to write a response file:

```json
{
  "kind": "error",
  "error_type": "validation_error | protocol_error | bootstrap_error | execution_error | io_error",
  "message": "human-readable failure",
  "details": {}
}
```

The process also exits non-zero. Treat `kind = "error"` as a bridge or runtime
failure, not as a workflow success payload.

## Validation boundary

`bridge.py` only validates:

- CLI arguments
- file existence
- JSON parsing
- request/observation top-level required fields
- `resume` CLI `run_id` equals `observation.run_id`

The adapter additionally validates:

- `workflow_id` catalog membership
- workflow module loadability

It does not validate:

- workflow-specific `task_input`, `context`, or `constraints`
- step-level `structured_output` schema
- verifier semantics
- branch correctness

Those belong to the skill-host adapter, runtime models, and workflow contracts.

It does validate host-side file placement for normal runs:

- `start`: `--request-file` and `--response-file`
- `preflight`: `--response-file`
- `resume`: `--observation-file` and `--response-file`

These files must be under
`<repo-root>/.durable-workflow-runtime/host-io/`. Pass
`--allow-unsafe-host-io-paths` only for explicit transport debugging; do not use
that flag for normal workflow execution.
