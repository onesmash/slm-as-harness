---
name: durable-workflow-runtime:register
description: |
  Load when the user asks for `durable-workflow-runtime:register`, importing a
  `.flow` file, installing a durable workflow archive, or registering a packed
  workflow into `workflow-binding.json`. Skip normal start/resume execution.
---

# Durable Workflow Runtime Register

This is an import-only companion to `durable-workflow-runtime`. It installs one
`.flow` archive into a runtime skill by unpacking its workflow directory and
registering its binding metadata. On success it also creates a slash-only
shortcut skill named `workflow:<workflow_id>` under the same
`durable-workflow-runtime` bundle.

## Use This Surface

Run the bundled register script:

```bash
python <register-skill-root>/scripts/register.py \
  --flow-file <path/to/workflow.flow>
```

This subskill is expected to live under `durable-workflow-runtime/register/`, so
the default runtime root is `<register-skill-root>/..`. If the runtime skill
lives elsewhere, pass it explicitly:

```bash
python <register-skill-root>/scripts/register.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --flow-file <path/to/workflow.flow>
```

Use `--force` only when replacing an existing workflow and catalog entry is the
intended outcome.

## After Successful Registration

After `register.py` succeeds, refresh the target repo's agent instruction files
with the updated workflow catalog:

```bash
python <register-skill-root>/../inject/scripts/inject.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --repo-root <target-repo-root>
```

Use the same runtime skill root that received the `.flow` workflow. This keeps
`AGENTS.md` and `CLAUDE.md` aligned with the newly registered
`workflow-binding.json` entry.

## Boundary

- Register only `.flow` files with matching `package-manifest.json`,
  `binding-entry.json`, and `workflow/manifest.json` workflow IDs.
- Do not call `bridge.py start`, `bridge.py resume`, or `bridge.py preflight`
  for registration.
- Do not allocate host I/O paths or create run state.
- Do not overwrite an existing workflow directory or binding entry unless the
  caller explicitly passes `--force`.

Read `references/register-cli-spec.md` for the archive validation and install
details.
