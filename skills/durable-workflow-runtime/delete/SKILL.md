---
name: durable-workflow-runtime:delete
description: |
  Load when the user asks for `durable-workflow-runtime:delete`, deleting or
  unregistering a durable workflow, removing a workflow directory, or pruning a
  workflow from `workflow-binding.json`. Skip normal start/resume execution.
---

# Durable Workflow Runtime Delete

This is a removal-only companion to `durable-workflow-runtime`. It deletes one
workflow directory and removes the matching catalog entry from
`workflow-binding.json`. On success it also removes the matching slash-only
shortcut skill and its mirrored Claude entry `/<workflow_id>` when present.

## Use This Surface

Run the bundled delete script:

```bash
python <delete-skill-root>/scripts/delete_workflow.py \
  --workflow-id <workflow_id> \
  --confirm <workflow_id>
```

This subskill is expected to live under `durable-workflow-runtime/delete/`, so
the default runtime root is `<delete-skill-root>/..`. If the runtime skill lives
elsewhere, pass it explicitly:

```bash
python <delete-skill-root>/scripts/delete_workflow.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --workflow-id <workflow_id> \
  --confirm <workflow_id>
```

If the workflow is currently the default, choose one explicit default action:

```bash
python <delete-skill-root>/scripts/delete_workflow.py \
  --workflow-id <workflow_id> \
  --confirm <workflow_id> \
  --new-default-workflow-id <remaining_workflow_id>
```

or:

```bash
python <delete-skill-root>/scripts/delete_workflow.py \
  --workflow-id <workflow_id> \
  --confirm <workflow_id> \
  --clear-default
```

After deletion succeeds, refresh the target repo's agent instruction files:

```bash
python <delete-skill-root>/../inject/scripts/inject.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --repo-root <target-repo-root>
```

## Boundary

- Delete only workflows published in `workflow-binding.json`.
- Require `--confirm <workflow_id>` for every deletion.
- Do not delete the current `default_workflow_id` unless the caller explicitly
  supplies `--new-default-workflow-id` or `--clear-default`.
- Do not call `bridge.py start`, `bridge.py resume`, or `bridge.py preflight`
  for deletion.
- Do not allocate host I/O paths or mutate runtime run state.

Read `references/delete-cli-spec.md` for exact validation and catalog update
rules.
