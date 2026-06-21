---
name: durable-workflow-runtime:pack
description: |
  Load when the user asks for `durable-workflow-runtime:pack`, exporting a
  workflow to `.flow`, packing a named durable workflow, or creating a portable
  workflow archive. Skip normal start/resume execution; this skill only packages.
---

# Durable Workflow Runtime Pack

This is a packaging-only companion to `durable-workflow-runtime`. It exports one
published workflow into a `.flow` archive without starting, resuming, or
preflighting a workflow run.

## Use This Surface

Run the bundled pack script:

```bash
python <pack-skill-root>/scripts/pack.py \
  --workflow-id <workflow_id> \
  --output-file <path/to/workflow.flow>
```

This subskill is expected to live under `durable-workflow-runtime/pack/`, so the
default runtime root is `<pack-skill-root>/..`. If the runtime skill lives
elsewhere, pass it explicitly:

```bash
python <pack-skill-root>/scripts/pack.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --workflow-id <workflow_id> \
  --output-file <path/to/workflow.flow>
```

## Boundary

- Package only workflows that are published in
  `durable-workflow-runtime/workflow-binding.json`.
- Do not call `bridge.py start`, `bridge.py resume`, or `bridge.py preflight`
  for packaging.
- Do not allocate host I/O paths or create run state.
- If the static binding schema drifts from `WORKFLOW_INPUT_CONTRACT`, stop and
  report the packaging failure.

Read `references/pack-cli-spec.md` for the archive layout and validation
details.
