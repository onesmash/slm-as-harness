# Register CLI Spec

Read this file when invoking or maintaining:

- `<register-skill-root>/scripts/register.py`
- the `durable-workflow-runtime:register` import surface

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<register-skill-root>/`.

## Purpose

`register.py` installs one `.flow` archive into a durable workflow runtime
bundle.

This is an import surface, not a workflow execution surface:

- it reads a `.flow` zip archive
- it unpacks `workflow/` into
  `durable-workflow-runtime/workflow-runtime/workflows/<workflow_id>/`
- it registers `binding-entry.json` into
  `durable-workflow-runtime/workflow-binding.json`
- it creates a slash-only shortcut skill at
  `durable-workflow-runtime/workflow-shortcuts/<workflow_id>/SKILL.md`
  and mirrors it to `durable-workflow-runtime/.claude/skills/<workflow_id>/`
  so Claude Code can discover `/<workflow_id>`
- it does not run dependency preflight
- it does not allocate host I/O paths
- it does not create or mutate runtime run state

## Command

When this skill lives at `durable-workflow-runtime/register/`:

```bash
python3 <register-skill-root>/scripts/register.py \
  --flow-file <path/to/workflow.flow>
```

When the runtime skill lives elsewhere:

```bash
python3 <register-skill-root>/scripts/register.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --flow-file <path/to/workflow.flow>
```

Replace an existing workflow only when the caller explicitly asks for it:

```bash
python3 <register-skill-root>/scripts/register.py \
  --flow-file <path/to/workflow.flow> \
  --force
```

## Post-Registration Injection

After registration succeeds, call the sibling `inject` subskill to refresh the
target repository's `AGENTS.md` and `CLAUDE.md` workflow catalog block:

```bash
python3 <register-skill-root>/../inject/scripts/inject.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --repo-root <target-repo-root>
```

Use the same runtime skill root that received the `.flow` archive. The register
script intentionally does not infer the target repo; injection is a separate
step because it writes repository instruction files.

## Validation Boundary

`register.py` validates only import concerns:

- `--flow-file` exists and ends in `.flow`
- the runtime skill root exists
- archive paths are relative and cannot escape the extraction directory
- `package-manifest.json.package_type` is `durable-workflow-runtime.flow`
- `package-manifest.json.workflow_id`, `binding-entry.json.workflow_id`, and
  `workflow/manifest.json.workflow_id` all match
- the target workflow ID is a safe identifier
- existing workflow directories or binding entries are rejected unless
  `--force` is present

It intentionally does not validate:

- missing external workflow dependencies
- whether workflow Python modules are importable after installation
- whether a workflow can satisfy a future user task
- step-level verifier behavior

Those checks belong to `preflight`, `start/resume`, or workflow-specific tests.

## Installed Files

Given this archive:

```text
<workflow_id>.flow
├── package-manifest.json
├── binding-entry.json
└── workflow/
    ├── manifest.json
    ├── contract.py
    └── ...
```

`register.py` installs:

```text
durable-workflow-runtime/
├── workflow-binding.json      # adds or replaces binding-entry.json
├── .claude/skills/
│   └── <workflow_id> -> ../../workflow-shortcuts/<workflow_id>
├── workflow-shortcuts/
│   └── <workflow_id>/
│       └── SKILL.md           # slash-only shortcut invoked as /<workflow_id>
└── workflow-runtime/workflows/
    └── <workflow_id>/          # receives archive workflow/ contents
```

The script does not change `default_workflow_id`; selecting the new workflow is
a separate runtime decision.

## Success Output

On success, `register.py` prints a JSON object:

```json
{
  "kind": "flow_registration",
  "workflow_id": "demo-prompt-loop",
  "workflow_dir": "/abs/path/workflow-runtime/workflows/demo_prompt_loop",
  "binding_file": "/abs/path/workflow-binding.json",
  "shortcut_skill_name": "demo-prompt-loop",
  "shortcut_skill_dir": "/abs/path/workflow-shortcuts/demo-prompt-loop",
  "shortcut_skill_file": "/abs/path/workflow-shortcuts/demo-prompt-loop/SKILL.md",
  "claude_shortcut_skill_dir": "/abs/path/.claude/skills/demo-prompt-loop",
  "created_claude_shortcut_skill": true,
  "replaced_existing": false,
  "installed_files": 12
}
```

On failure, it prints a human-readable error to stderr and exits non-zero.
