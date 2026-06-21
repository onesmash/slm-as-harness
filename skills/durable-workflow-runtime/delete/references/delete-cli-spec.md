# Delete CLI Spec

Read this file when invoking or maintaining:

- `<delete-skill-root>/scripts/delete_workflow.py`
- the `durable-workflow-runtime:delete` removal surface

Unless explicitly marked as a repo-local example, paths are relative to
`<delete-skill-root>/`.

## Purpose

`delete_workflow.py` removes one published durable workflow from a runtime skill
bundle.

This is a removal surface, not a workflow execution surface:

- it reads `durable-workflow-runtime/workflow-binding.json`
- it removes the selected `workflow-binding.json.workflows[]` entry
- it deletes `durable-workflow-runtime/workflow-runtime/workflows/<workflow_id>/`
- it removes `durable-workflow-runtime/workflow-shortcuts/<workflow_id>/`
  when the matching shortcut skill exists
- it does not run dependency preflight
- it does not allocate host I/O paths
- it does not create or mutate runtime run state

## Command

When this skill lives at `durable-workflow-runtime/delete/`:

```bash
python3 <delete-skill-root>/scripts/delete_workflow.py \
  --workflow-id <workflow_id> \
  --confirm <workflow_id>
```

When the runtime skill lives elsewhere:

```bash
python3 <delete-skill-root>/scripts/delete_workflow.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --workflow-id <workflow_id> \
  --confirm <workflow_id>
```

If the workflow is currently the default, either choose a remaining workflow:

```bash
python3 <delete-skill-root>/scripts/delete_workflow.py \
  --workflow-id <workflow_id> \
  --confirm <workflow_id> \
  --new-default-workflow-id <remaining_workflow_id>
```

or explicitly clear the default:

```bash
python3 <delete-skill-root>/scripts/delete_workflow.py \
  --workflow-id <workflow_id> \
  --confirm <workflow_id> \
  --clear-default
```

## Post-Deletion Injection

After deletion succeeds, call the sibling `inject` subskill to refresh the
target repository's `AGENTS.md` and `CLAUDE.md` workflow catalog block:

```bash
python3 <delete-skill-root>/../inject/scripts/inject.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --repo-root <target-repo-root>
```

The delete script intentionally does not infer the target repo; injection is a
separate step because it writes repository instruction files.

## Validation Boundary

`delete_workflow.py` validates only removal concerns:

- `--workflow-id` is a safe identifier
- `--confirm` exactly matches `--workflow-id`
- the runtime skill root exists
- `workflow-binding.json.workflows` is a list
- the workflow is published in `workflow-binding.json`
- the workflow directory exists under `workflow-runtime/workflows/`
- the current default workflow is not removed accidentally
- `--new-default-workflow-id`, when provided, points to a remaining published
  workflow

It intentionally does not validate:

- whether historical run state still references the deleted workflow
- whether external repositories still mention the old workflow catalog before
  post-deletion injection
- whether other workflow docs have prose references to the deleted workflow

Those checks belong to repository review and follow-up cleanup.

## Removed Files

Given this runtime:

```text
durable-workflow-runtime/
├── workflow-binding.json
└── workflow-runtime/workflows/
    └── <workflow_id>/
        ├── manifest.json
        ├── contract.py
        └── ...
```

`delete_workflow.py` removes:

```text
durable-workflow-runtime/workflow-runtime/workflows/<workflow_id>/
```

and also removes this shortcut when present:

```text
durable-workflow-runtime/workflow-shortcuts/<workflow_id>/
```

and rewrites:

```text
durable-workflow-runtime/workflow-binding.json
```

## Success Output

On success, `delete_workflow.py` prints a JSON object:

```json
{
  "kind": "workflow_deletion",
  "workflow_id": "demo_prompt_loop",
  "workflow_dir": "/abs/path/workflow-runtime/workflows/demo_prompt_loop",
  "binding_file": "/abs/path/workflow-binding.json",
  "removed_binding": true,
  "removed_workflow_dir": true,
  "default_workflow_id": "superpowers_delivery_chain",
  "shortcut_skill_name": "workflow:demo_prompt_loop",
  "shortcut_skill_dir": "/abs/path/workflow-shortcuts/demo_prompt_loop",
  "shortcut_skill_file": "/abs/path/workflow-shortcuts/demo_prompt_loop/SKILL.md",
  "removed_shortcut_skill": true
}
```

On failure, it prints a human-readable error to stderr and exits non-zero.
