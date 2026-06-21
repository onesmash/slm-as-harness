---
name: durable-workflow-runtime:inject
description: |
  Load when the user asks for `durable-workflow-runtime:inject`, injecting
  durable workflow instructions into `AGENTS.md` or `CLAUDE.md`, refreshing the
  available workflow block, or publishing workflow catalog context to repo agent
  instructions. Skip normal start/resume execution.
---

# Durable Workflow Runtime Inject

This is an instruction-injection companion to `durable-workflow-runtime`. It
publishes the runtime usage note and current workflow catalog into repository
agent instruction files.

## Use This Surface

Run the bundled inject script:

```bash
python <inject-skill-root>/scripts/inject.py \
  --repo-root <target-repo-root>
```

This subskill is expected to live under `durable-workflow-runtime/inject/`, so
the default runtime root is `<inject-skill-root>/..`. If the runtime skill lives
elsewhere, pass it explicitly:

```bash
python <inject-skill-root>/scripts/inject.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --repo-root <target-repo-root>
```

## Boundary

- Inject only between `<!-- durable-workflow-runtime:start -->` and
  `<!-- durable-workflow-runtime:end -->`.
- Update `AGENTS.md` and `CLAUDE.md` by default; pass `--target-file` to limit
  or customize targets.
- Preserve all content outside the marker block.
- Do not call `bridge.py start`, `bridge.py resume`, or `bridge.py preflight`
  for injection.
- Do not edit workflow definitions or `workflow-binding.json`.

Read `references/inject-cli-spec.md` for the exact block shape and replacement
rules.
