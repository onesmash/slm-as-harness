# Workflow Skeleton

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Copy this directory into:

```text
<skill-root>/workflow-runtime/workflows/<your_workflow_id>/
```

Then make these replacements first:

1. Rename the directory from `ios_ai_assisted_development_flow` to your real `workflow_id`.
2. Replace `ios_ai_assisted_development_flow` in:
   - `contract.py`
   - verifier `ref` strings
   - any prompt wording that should mention the real workflow name
3. Rename step IDs if your workflow needs different stage names.
4. Update `references/flowchart.md` so it matches the real `policy.py`
   transitions and first emitted node.
5. Add the new workflow to `<skill-root>/workflow-binding.json`, including the
   `start_input_schema` exported by `WORKFLOW_INPUT_CONTRACT`.
6. Add the same `start_input_schema` to the workflow `manifest.json` if you add
   one for preflight dependency checks.
7. Add regression coverage to
   `<skill-root>/tests/test_durable_workflow_runtime.py`.

What this skeleton already demonstrates:

- one main yielded stage: `run_primary_stage`
- one unblock repair stage: `request_unblocking_input`
- one retry repair stage: `repair_and_resume`
- one explicit final node: `finalize_summary`
- start-time input contract
- yielded-step contracts
- durable state with `return_stage_id` and `repair_context`
- runtime-owned branch / retry / blocked routing
- GraphBuilder `start` and `resume` preview helpers
- developer-facing Mermaid flowchart in `references/flowchart.md`

Use this as a starting point, not as a rule that every workflow must keep the
same node names.

Before editing `prompts/*.md`, read:

```text
<skill-root>/references/prompt-placeholder-spec.md
```

Why:

- prompt placeholders are not global magic variables
- `run_primary_stage.md` only gets the keys explicitly passed by the start graph
- repair/final prompts only get the keys returned by `build_template_context(...)`
- a missing key will fail prompt rendering at runtime
