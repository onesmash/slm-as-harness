# Inject CLI Spec

Read this file when invoking or maintaining:

- `<inject-skill-root>/scripts/inject.py`
- the `durable-workflow-runtime:inject` instruction injection surface

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<inject-skill-root>/`.

## Purpose

`inject.py` writes a durable workflow usage block into repository instruction
files so future agents can discover the available workflows without inspecting
runtime internals.

This is a documentation/update surface, not a workflow execution surface:

- it reads `durable-workflow-runtime/workflow-binding.json`
- it writes marked blocks into target instruction files
- it does not run dependency preflight
- it does not allocate host I/O paths
- it does not create or mutate runtime run state
- it does not edit workflow definitions

## Command

Inject into both `AGENTS.md` and `CLAUDE.md` under a target repository:

```bash
python3 <inject-skill-root>/scripts/inject.py \
  --repo-root <target-repo-root>
```

When the runtime skill lives elsewhere:

```bash
python3 <inject-skill-root>/scripts/inject.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --repo-root <target-repo-root>
```

Limit the target files when needed:

```bash
python3 <inject-skill-root>/scripts/inject.py \
  --repo-root <target-repo-root> \
  --target-file AGENTS.md \
  --target-file docs/agent-instructions.md
```

## Injected Block

The script owns only this marked block:

```markdown
<!-- durable-workflow-runtime:start -->
## Durable Workflow Runtime Routing
Before selecting any standalone skill or manually orchestrating a multi-step task,
check whether the user's request semantically matches one of the published durable workflows below.
Use `durable-workflow-runtime` when:
- The task is multi-step, long-running, checkpointed, review-gated, or needs durable state across turns/sessions.
- The task matches a workflow domain by intent, even if the exact `workflow_id` is not mentioned.
- A standalone skill and a durable workflow both match; in this case, the durable workflow wins because it may invoke the relevant skills internally.
Do not use `durable-workflow-runtime` when:
- The user asks for a short answer, one-off explanation, quick command, or narrow single-step edit.
- No workflow clearly matches and the user has not chosen one.
- The user explicitly asks to avoid the runtime.
Selection rule:
1. Match the user's request against each `<workflow_id>`, `<description>`.
2. Prefer the most specific workflow over a generic one.
3. If exactly one workflow clearly matches, invoke it.
4. If multiple workflows plausibly match, ask the user to choose.
5. If no workflow matches, proceed normally with the best skill/tool.
Invocation format:
`/durable-workflow-runtime <workflow_id> <user_prompt>`

Available workflows:
<available_workflows>
  <workflow>
    <workflow_id>pdf-processing</workflow_id>
    <description>Extract PDF text, fill forms, merge files. Use when handling PDFs.</description>
  </workflow>
</available_workflows>
<!-- durable-workflow-runtime:end -->
```

Descriptions are XML-escaped before insertion so `&`, `<`, and `>` in
`flow_description` cannot break the block.

## Replacement Rules

- If a target file does not exist, create it with only the injected block.
- If the marker block already exists, replace that block in place.
- If no marker block exists, append the block to the end of the file.
- Preserve all content outside the marker block.
- Reject files with only one marker, or with multiple start/end marker pairs,
  because the intended replacement boundary is ambiguous.

## Success Output

On success, `inject.py` prints a JSON object:

```json
{
  "kind": "workflow_instruction_injection",
  "workflow_count": 2,
  "updated_files": [
    {
      "path": "/abs/path/AGENTS.md",
      "action": "created | appended | replaced"
    }
  ]
}
```

On failure, it prints a human-readable error to stderr and exits non-zero.
