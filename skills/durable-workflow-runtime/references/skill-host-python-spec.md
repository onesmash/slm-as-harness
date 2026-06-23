# `skill_host.py` Python Interface Spec

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Read this file when implementing:

- `<skill-root>/workflow-runtime/adapters/skill_host.py`

If imports fail locally, read `environment-setup.md` before changing adapter
bootstrap logic. Missing packages are an environment problem first, not a
reason to widen `skill_host.py` responsibilities.

## Purpose

`skill_host.py` is the thin Python adapter that sits between:

- the skill-facing bridge at `scripts/bridge.py`
- the hidden runtime under `workflow-runtime/`

It exists to keep responsibilities separated:

- `bridge.py` owns CLI parsing, file I/O, response-file writing, and exit-code
  mapping
- `skill_host.py` owns repo-root checks, import bootstrap, adapter-level input
  validation, terminal next-step recommendations, and delegation into the
  runtime
- the runtime owns state, branching, retries, stop conditions, and persistence
- the workflow definition owns prompt assets, contracts, and verifier logic

`skill_host.py` must stay thin. It is not a second orchestrator.

## Current public API

Current V1 surface:

```python
def start(repo_root: str, request: dict, workflow_id: str | None = None) -> dict: ...
def resume(repo_root: str, run_id: str, observation: dict) -> dict: ...
```

The adapter also re-exports exception classes that the bridge maps into
response-file errors and exit codes:

- `BootstrapError`
- `RequestValidationError`
- `ObservationValidationError`
- `ProtocolError`
- `WorkflowExecutionError`

## Current workflow binding

Current binding config shape:

```json
{
  "default_workflow_id": "ios_goals",
  "workflows": [
    {
      "workflow_id": "demo_prompt_loop",
      "flow_description": "...",
      "start_input_schema": {
        "task_input": {},
        "context": {},
        "constraints": {}
      }
    },
    {
      "workflow_id": "superpowers_delivery_chain",
      "flow_description": "...",
      "start_input_schema": {
        "task_input": {},
        "context": {},
        "constraints": {}
      }
    },
    {
      "workflow_id": "ios_goals",
      "flow_description": "...",
      "start_input_schema": {
        "task_input": {},
        "context": {},
        "constraints": {}
      }
    },
    {
      "workflow_id": "academic_research_pipeline",
      "flow_description": "...",
      "start_input_schema": {
        "task_input": {},
        "context": {},
        "constraints": {}
      }
    }
  ]
}
```

The current skill-host adapter resolves that config from:

```text
<skill-root>/workflow-binding.json
```

Current boundary:

- the adapter supports explicit `workflow_id` on `start(...)`
- if `workflow_id` is omitted, it consumes `default_workflow_id`
- `workflows[].flow_description` is still caller-facing selection metadata
- `workflows[].start_input_schema` is caller-facing contract metadata copied
  from the selected workflow's `WORKFLOW_INPUT_CONTRACT`
- terminal `done` responses expose `next_step_recommendations.instructions`
  telling the host agent to inspect `workflow-binding.json` before recommending
  which workflow to start next
- the current runtime still does not semantically parse descriptions by itself
- `resume(...)` never re-selects workflow

## Current responsibilities

### `start(repo_root, request, workflow_id=None)`

Current adapter responsibilities:

1. resolve and validate `repo_root`
2. verify the skill-bundled runtime tree exists
3. load and validate the workflow binding config
4. validate adapter-level top-level fields
5. bootstrap runtime imports by prepending the runtime root to `sys.path`
6. resolve workflow by:
   - explicit `workflow_id`, or
   - `default_workflow_id` fallback
7. confirm explicit workflow selection is both:
   - published in the binding catalog
   - loadable as runtime modules
8. backfill or validate the selected catalog entry's `start_input_schema`
   against `WORKFLOW_INPUT_CONTRACT`
9. construct the graphbuilder runtime engine
10. delegate to `engine.start(workflow_id, request)`
11. if the response is terminal, attach next-step workflow recommendations
12. return a plain JSON-serializable dict

### `resume(repo_root, run_id, observation)`

Current adapter responsibilities:

1. resolve and validate `repo_root`
2. verify the skill-bundled runtime tree exists
3. validate adapter-level top-level fields
4. verify `observation["run_id"] == run_id`
5. bootstrap runtime imports
6. construct the graphbuilder runtime engine
7. delegate to `engine.resume(run_id, observation)`
8. if the response is terminal, attach next-step workflow recommendations
9. return a plain JSON-serializable dict

## Validation boundary

`skill_host.py` should validate only adapter-level concerns:

- repo root exists
- runtime directories exist
- input objects are dict-like
- required top-level fields are present
- `run_id` consistency between CLI arg and observation

It should not validate:

- workflow-specific nested input semantics
- step-level `structured_output` shape
- branch correctness
- verifier results
- prompt asset content

Workflow selection note:

- selector correctness at adapter level means catalog membership + module
  loadability
- workflow-specific business fit still belongs to the caller or selecting agent

Those belong to the runtime and workflow contracts.

## Import bootstrap rule

Because `workflow-runtime` is a hidden directory with a hyphen in its name, it
cannot be used directly as a dotted Python package root.

The current adapter handles this by:

1. resolving the skill-bundled runtime root
2. prepending that directory to `sys.path`
3. importing packages such as `runtime.engine_graphbuilder`

That is the correct level for this bootstrap logic. Do not move it into
`bridge.py`.

## Prompt ownership boundary

`skill_host.py` must not render or author step prompt bodies itself.

Current intended ownership:

- prompt assets live under
  `workflow-runtime/workflows/<workflow>/prompts/`
- graph metadata selects the active prompt asset
- runtime code assembles `PromptEnvelope`
- `skill_host.py` only returns runtime responses

For the agent-side workflow catalog and `flow_description` guidance, read
`workflow-selection-spec.md`.

## Return and failure shape

`skill_host.py` should return plain dicts with runtime response kinds:

- `yield`
- `done`

For failures, the preferred pattern is to raise one of the exported exception
classes and let `bridge.py` map that into:

- non-zero exit status
- `response.json` with `kind = "error"`

This keeps file I/O and stdout/stderr policy inside the bridge instead of
duplicating it in the adapter.
