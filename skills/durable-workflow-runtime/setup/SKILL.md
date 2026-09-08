---
name: durable-workflow-runtime:setup
description: |
  Load when the user asks for `durable-workflow-runtime setup`,
  `/durable-workflow-runtime setup`, `durable-workflow-runtime:setup`,
  installing workflow shortcut skills, or creating global slash-command
  symlinks for `workflow-shortcuts` into `~/.agents/skills` or
  `~/.claude/skills`. Skip normal start/resume execution.
---

# Durable Workflow Runtime Setup

This is an install-only companion to `durable-workflow-runtime`. It publishes
the slash-only skills under `workflow-shortcuts/` into the current user's
global skill directories so `/<workflow_id>` is discoverable outside this
runtime bundle.

## Use This Surface

Run the bundled setup script:

```bash
python <setup-skill-root>/scripts/setup.py
```

This subskill is expected to live under `durable-workflow-runtime/setup/`, so
the default runtime root is `<setup-skill-root>/..`. If the runtime skill lives
elsewhere, pass it explicitly:

```bash
python <setup-skill-root>/scripts/setup.py \
  --runtime-skill-root <path/to/durable-workflow-runtime>
```

Override the install destinations only when the caller asks for a non-default
layout:

```bash
python <setup-skill-root>/scripts/setup.py \
  --skill-root ~/.agents/skills \
  --skill-root ~/.claude/skills
```

## After Successful Setup

Report the created, replaced, unchanged, and pruned shortcut links. Do not
start a workflow after setup unless the user separately asks to run one.

## Boundary

- Install only directories under `workflow-shortcuts/` that contain `SKILL.md`.
- Create or repair symlinks in `~/.agents/skills` and `~/.claude/skills` by
  default.
- Replace a destination only when it is already a symlink. Refuse to overwrite
  a real file or directory.
- Prune stale symlinks in those skill roots that still point at this runtime's
  `workflow-shortcuts/` but no longer have a matching shortcut skill.
- Do not call `bridge.py start`, `bridge.py resume`, or `bridge.py preflight`
  for setup.
- Do not allocate host I/O paths or create run state.

Read `references/setup-cli-spec.md` for the exact link layout and output shape.
