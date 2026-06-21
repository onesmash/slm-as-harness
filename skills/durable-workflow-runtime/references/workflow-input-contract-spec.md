# Workflow Input Contract Spec

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Read this file when implementing:

- workflow-level validation of `StartRequest`
- workflow-local definition of accepted `task_input`, `context`, and
  `constraints`

## Purpose

`WorkflowInputContract` is the workflow-scoped source of truth for start-time
input semantics.

It answers:

- what `task_input` shape a workflow expects
- what `context` shape a workflow expects
- what `constraints` shape a workflow accepts
- where workflow-specific validation starts after the generic `StartRequest`
  model has already been parsed

This means `constraints` are not an undocumented side channel. Even when a
workflow has no special constraints, the workflow should still publish an
explicit contract.

## Current shared type

The shared type lives in:

```text
<skill-root>/workflow-runtime/workflows/common/contracts.py
```

Current public shape:

```python
class WorkflowInputContract:
    task_input_schema: dict
    context_schema: dict
    constraints_schema: dict

    def to_start_input_schema(self) -> dict: ...
```

Workflow-local modules should expose one instance:

```python
WORKFLOW_INPUT_CONTRACT: WorkflowInputContract
```

## Current validation order

For the current graphbuilder runtime, start-time validation happens in this
order:

1. `bridge.py` checks that the request JSON has top-level
   `task_input/context/constraints`.
2. `StartRequest.from_dict(...)` parses generic runtime shape.
3. `validate_workflow_input(...)` validates the payload against the workflow's
   `WORKFLOW_INPUT_CONTRACT`.
4. Only then does workflow start logic run.

This keeps three boundaries separate:

- bridge-level file and top-level JSON checks
- generic runtime model validation
- workflow-local input validation

The same workflow-local contract is also published as `start_input_schema` in
workflow manifest and binding metadata so hosts can inspect start requirements
before calling `start`. Treat those metadata copies as derived surfaces; the
runtime validation source of truth remains `WORKFLOW_INPUT_CONTRACT`.

## Schema language used by the current runtime

The current runtime does not require full JSON Schema. It uses a lightweight
repo-local schema convention implemented in:

```text
<skill-root>/workflow-runtime/runtime/validation.py
```

Supported patterns in the current implementation:

- `"string"`
- `"boolean"`
- `"integer"`
- `"object"`
- `"string[]"`, `"integer[]"`, and similar list suffixes
- optional scalar or object fields via `?`, for example `"integer?"`

Schema keys are required unless the schema string ends with `?`.

## Current demo workflow contract

The current demo workflow publishes:

```python
WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={
        "goal": "string",
    },
    context_schema={
        "repo_root": "string",
    },
    constraints_schema={
        "max_steps": "integer?",
    },
)
```

That means the current skill wrapper expects:

- `task_input.goal`
- `context.repo_root`
- optional `constraints.max_steps`

## Authoring guidance

- Keep `task_input_schema` limited to workflow-owned business inputs.
- Keep `context_schema` limited to environmental context the workflow actually
  needs.
- Keep `constraints_schema` explicit, even if it is `{}`.
- Do not fold yielded-step output requirements into the workflow-input
  contract; those belong in `StepContract`.

## Failure semantics

If workflow input validation fails:

- the runtime should not emit a yielded step
- the failure is a start-time validation failure
- the host should not treat it like a step-level blocked or failed observation

This is distinct from:

- resume-time `Observation` validation failure
- verifier failure on a yielded step
- workflow policy choosing a repair branch
