# Setup CLI Spec

Read this file when invoking or maintaining:

- `<setup-skill-root>/scripts/setup.py`
- the `durable-workflow-runtime:setup` global shortcut install surface

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<setup-skill-root>/`.

## Purpose

`setup.py` installs slash-only workflow shortcut skills into the current user's
global skill directories.

This is an install surface, not a workflow execution surface:

- it reads `durable-workflow-runtime/workflow-shortcuts/`
- it creates or repairs symlinks in `~/.agents/skills` and `~/.claude/skills`
- it does not run dependency preflight
- it does not allocate host I/O paths
- it does not create or mutate runtime run state
- it does not edit `workflow-binding.json` or workflow definitions

## Command

When this skill lives at `durable-workflow-runtime/setup/`:

```bash
python3 <setup-skill-root>/scripts/setup.py
```

When the runtime skill lives elsewhere:

```bash
python3 <setup-skill-root>/scripts/setup.py \
  --runtime-skill-root <path/to/durable-workflow-runtime>
```

Override destinations when installing into a non-default skill root:

```bash
python3 <setup-skill-root>/scripts/setup.py \
  --skill-root ~/.agents/skills \
  --skill-root ~/.claude/skills
```

## Installed Links

Given this runtime layout:

```text
durable-workflow-runtime/
└── workflow-shortcuts/
    └── <workflow_id>/
        └── SKILL.md
```

`setup.py` installs:

```text
~/.agents/skills/<workflow_id> -> <runtime-skill-root>/workflow-shortcuts/<workflow_id>
~/.claude/skills/<workflow_id> -> <runtime-skill-root>/workflow-shortcuts/<workflow_id>
```

Only child directories of `workflow-shortcuts/` that contain `SKILL.md` are
installed. Hidden names are ignored.

Link rules:

- missing destination: create a directory symlink
- existing symlink that already resolves to the same shortcut: leave unchanged
- existing symlink that points elsewhere: replace it
- existing non-symlink file or directory: fail instead of overwriting
- stale symlink in a target skill root that still points into this runtime's
  `workflow-shortcuts/` but no longer has a matching shortcut: remove it

## Success Output

On success, `setup.py` prints a JSON object:

```json
{
  "kind": "workflow_shortcut_setup",
  "runtime_skill_root": "/abs/path/durable-workflow-runtime",
  "shortcuts_root": "/abs/path/workflow-shortcuts",
  "shortcut_count": 2,
  "skill_roots": [
    "/Users/name/.agents/skills",
    "/Users/name/.claude/skills"
  ],
  "links": [
    {
      "workflow_id": "demo-prompt-loop",
      "source": "/abs/path/workflow-shortcuts/demo-prompt-loop",
      "targets": [
        {
          "path": "/Users/name/.agents/skills/demo-prompt-loop",
          "action": "created | unchanged | replaced"
        }
      ]
    }
  ],
  "pruned": [
    {
      "path": "/Users/name/.agents/skills/old-workflow",
      "reason": "stale shortcut pointing at this runtime"
    }
  ]
}
```

On failure, it prints a human-readable error to stderr and exits non-zero.
