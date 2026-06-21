# Pack CLI Spec

Read this file when invoking or maintaining:

- `<pack-skill-root>/scripts/pack.py`
- the `durable-workflow-runtime:pack` packaging surface

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<pack-skill-root>/`.

## Purpose

`pack.py` exports one published durable workflow into a `.flow` archive without
starting or resuming a runtime run.

This is a packaging surface, not a workflow execution surface:

- it reads `durable-workflow-runtime/workflow-binding.json`
- it reads `durable-workflow-runtime/workflow-runtime/workflows/<workflow_id>/`
- it verifies the workflow can be loaded far enough to read
  `WORKFLOW_INPUT_CONTRACT`
- it writes a portable `.flow` zip archive
- it does not run dependency preflight
- it does not allocate host I/O paths
- it does not create or mutate runtime run state

## Command

When this skill lives at `durable-workflow-runtime/pack/`:

```bash
python3 <pack-skill-root>/scripts/pack.py \
  --workflow-id <workflow_id> \
  --output-file <path/to/workflow.flow>
```

When the runtime skill lives elsewhere:

```bash
python3 <pack-skill-root>/scripts/pack.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --workflow-id <workflow_id> \
  --output-file <path/to/workflow.flow>
```

Overwrite an existing package only when the caller explicitly asks for it:

```bash
python3 <pack-skill-root>/scripts/pack.py \
  --workflow-id <workflow_id> \
  --output-file <path/to/workflow.flow> \
  --force
```

## Validation Boundary

`pack.py` validates only packaging concerns:

- `--workflow-id` is a safe identifier
- `--output-file` ends in `.flow`
- the runtime skill root exists
- the workflow is published in `workflow-binding.json`
- the workflow directory exists under `workflow-runtime/workflows/`
- `workflow/manifest.json.workflow_id` matches the requested workflow
- `workflow-binding.json` does not drift from
  `WORKFLOW_INPUT_CONTRACT.to_start_input_schema()`

It intentionally does not validate:

- missing external workflow dependencies
- whether a workflow can satisfy a future user task
- step-level verifier behavior
- host observation schemas beyond the exported contract metadata

Those checks belong to `preflight`, `start/resume`, or workflow-specific tests.

## `.flow` Archive Shape

`.flow` is a zip container with this minimum layout:

```text
<workflow_id>.flow
├── package-manifest.json
├── binding-entry.json
└── workflow/
    ├── manifest.json
    ├── contract.py
    ├── graphbuilder_runtime.py
    ├── policy.py
    ├── state.py
    ├── verifiers.py
    ├── references/
    └── prompts/
```

`package-manifest.json` identifies the package type, workflow ID, source skill,
archive format, workflow root, and exported start input schema.

`binding-entry.json` is the selected catalog entry from
`workflow-binding.json`, with a `start_input_schema` attached from
`WORKFLOW_INPUT_CONTRACT` when the static catalog entry omitted it.

The archive excludes generated cache files such as `__pycache__/`, `.pyc`, and
`.DS_Store`.

## Success Output

On success, `pack.py` prints a JSON object:

```json
{
  "kind": "flow_package",
  "workflow_id": "demo_prompt_loop",
  "output_file": "/abs/path/demo_prompt_loop.flow",
  "included_files": 12,
  "size_bytes": 4096,
  "package_manifest": "package-manifest.json"
}
```

On failure, it prints a human-readable error to stderr and exits non-zero.
