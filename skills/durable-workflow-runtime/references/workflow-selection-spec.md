# Workflow Selection Spec

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Read this file when deciding which workflow a host or agent should start
through this skill wrapper.

## Purpose

This skill can publish a small workflow catalog so the caller can make an
explicit workflow choice instead of guessing from prompt text alone.

The core idea is:

- each workflow has a stable `workflow_id`
- each workflow also has a short human-readable `flow_description`
- the caller reads that catalog to choose which published workflow to start
- the wrapper may either:
  - start the configured default workflow
  - or accept an explicit `workflow_id` chosen before `start`

This means `workflow_id` should be treated as an optional start-time parameter
of the skill wrapper, not as a workflow-local business input.

This keeps workflow identity explicit without pretending that descriptive
metadata alone is a runtime routing mechanism.

## Current file location

The current catalog lives in:

```text
<skill-root>/workflow-binding.json
```

## Current config shape

```json
{
  "default_workflow_id": "demo_prompt_loop",
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

## Field semantics

### `default_workflow_id`

The fallback workflow used when:

- the caller omits explicit `workflow_id`
- a human wants the wrapper to behave like a single-workflow skill

Current shipped default:

- `demo_prompt_loop`

### `workflows`

A catalog for the caller or human operator.

Each item should contain:

- `workflow_id`: stable runtime identifier
- `flow_description`: short explanation of what the workflow is for
- `start_input_schema`: the published start-time input contract, copied from
  the workflow's `WORKFLOW_INPUT_CONTRACT`

Recommended writing style for `flow_description`:

- describe the workflow's job, not its implementation file layout
- mention the kind of user task it is good at
- mention its boundary if it is easy to confuse with neighboring workflows

Good example:

- "检查、解释和演示 prompt-workflow skill 的 bridge、runtime、contract、host loop 与 demo workflow 行为。"

Weaker example:

- "The workflow in `workflows/demo_prompt_loop`."

## Current runtime behavior

Important boundary:

- the adapter now supports explicit workflow selection at `start`
- `workflows[].flow_description` is still metadata for the selecting agent and
  for references
- `workflows[].start_input_schema` lets a host inspect the required
  `task_input`, `context`, and `constraints` shape before calling `start`
- when a workflow returns `done`, the adapter attaches
  `next_step_recommendations.instructions` telling the host to read this catalog
  instead of copying every workflow into the response
- the runtime still does not parse `flow_description` or run automatic semantic
  routing from it

So this file is a workflow catalog plus a default binding. It is not a free-form
semantic resolver.

## Current recommended usage

When a human or host agent is about to start a workflow through the current
wrapper, assume the wrapper has already been selected and only decide which
published workflow to start:

1. Read the workflow catalog in `workflow-binding.json`.
2. Use `flow_description` only to distinguish the published workflows inside
   this wrapper.
3. If the caller has a concrete workflow choice, pass that optional
   `workflow_id` explicitly at `start`.
4. If the caller has no stronger choice, start the configured
   `default_workflow_id`.
5. After `start`, never re-select a workflow during `resume`; rely on
   persisted `RunState.workflow_id`.
6. When a terminal `done` response includes `next_step_recommendations`, follow
   its instructions, read `workflow-binding.json`, recommend the best matching
   workflow, and start the selected workflow as a new run.

## Selector source of truth

An explicit `workflow_id` is valid only when both are true:

- it appears in `workflow-binding.json.workflows[]`
- its workflow modules are loadable under `workflow-runtime/workflows/<workflow_id>/`
- its published `start_input_schema`, when present, matches the workflow
  contract exposed by `WORKFLOW_INPUT_CONTRACT`

## Non-goals

It also does not imply that `skill_host.py` should become a second agent that
does free-form routing in Python.

Current design intent:

- workflow choice happens before `start`
- runtime execution remains code-owned after `start`

## Current shipped workflows

The shipped catalog currently contains:

- `demo_prompt_loop`
- `superpowers_delivery_chain`
- `academic_research_pipeline`

That means the wrapper story is now:

- read the catalog
- choose an explicit `workflow_id` when the task is specific enough
- otherwise fall back to `default_workflow_id`

When more workflows are added later, extend the catalog instead of hiding the
new choices inside unrelated prose.
