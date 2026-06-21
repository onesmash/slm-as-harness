# Prompt Asset Template

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Read this file when authoring or reviewing prompt assets under:

```text
<skill-root>/workflow-runtime/workflows/<workflow_id>/prompts/
```

## Purpose

Prompt assets own the step's task semantics: what to do, what not to do, and
when to report a blocked state.

They do not own the machine-readable return shape. For yielded steps,
`workflow-runtime/workflows/common/prompting.py` appends the
`structured_output` contract from `StepContract.output_schema` and
`StepContract.failure_schema`.

## Template

Use this shape for normal yielded-step prompts:

```md
[Use a direct slash-skill invocation for the stage's single primary skill owner, e.g. `/brainstorming {{workflow_goal}}`. Include the short execution handle the skill should operate on. If you cannot name one primary owner, split or redefine the stage before writing the prompt.]

[Optional stage context]
Use this section only when the current workflow already provides real
template keys for this prompt. Keep short execution handles in the action line;
use this section for workflow goal, summaries, long JSON, previous review or
verification evidence, and other background. Omit it when no real keys are
available.

Stage Boundaries:

- Do not ...
- This stage only owns ...
- Only ... when ...

Blocked Conditions:

If ..., return `blocked`; do not ...
```

Omit any section that does not add real step-specific behavior. Short prompts
are fine.

## Authoring Rules

- Start with an executable action line that makes the intended skill, action,
  execution object, and minimum required inputs obvious. The authoring agent
  should decide this line from the stage semantics; do not derive it
  mechanically from `skill_routing`, because a stage may list multiple candidate
  skills. When one primary routed skill clearly owns the stage, prefer direct
  slash invocation form, such as
  ``/mattpocock:diagnose failing-check triage``,
  ``/mattpocock:to-prd turn the clarified requirement context into a PRD.``, or
  ``/openspec-apply-change {{change_name}} using {{change_path}}, {{tasks_path}}, and {{openspec_design_path}}``.
  If a stage seems to need multiple primary skills or no primary owner at all,
  treat that as a stage-design problem and split or redefine the stage before
  authoring the prompt. Additional routed skills may exist, but only as
  supporting routes around the primary owner named in the slash action line.
- Do not write `structured_output` field lists in prompt assets.
- Do not write schema field names, schema types, or optional markers in prompt
  assets.
- Do not write glue text such as "see the rendered schema below"; the runtime
  appends the schema block.
- Do not invent double-brace template keys in this template or in prompt assets.
  Use only keys that are actually provided by the workflow's start-time
  `template_context` or `build_template_context(...)`.
- Keep routing decisions out of prompt assets. The host reports what happened;
  runtime policy decides the next node.
- Prefer expressing intended work in the action line and context instead of a
  numbered `Tasks:` section. Add an extra section only when omitting it would
  lose a concrete execution precondition that is not already obvious from the
  action line, context, boundaries, or blocked conditions.
- Do not hide the main execution object in context. If a short name, path, task
  file, target artifact, or retry input determines what the primary skill acts
  on, include it in the action line. Use context for background and evidence,
  not for the handle that makes the action executable.
- Use `Stage Boundaries` for workflow-owned guardrails only. Do not repeat the
  invoked skill's built-in checklist or SOP there unless this workflow needs an
  extra stage-specific restriction or handoff gate.

## Examples

### Direct slash-skill stage

```md
/brainstorming {{workflow_goal}}

Stage Boundaries:

- This stage only owns requirement clarification, approach convergence, and spec review.
- Do not create an OpenSpec change.
- Do not start implementation.

Blocked Conditions:

If key input, authorization, design decisions, or explicit user approval for the spec are missing, return `blocked`; do not fill gaps with assumptions.
```

### Primary slash-skill execution stage

```md
/openspec-apply-change {{change_name}} using {{change_path}}, {{tasks_path}}, and {{openspec_design_path}}; address {{issues_found}} and {{failed_commands}} if present before returning review-ready evidence.

Stage Context:

- Workflow goal: {{workflow_goal}}
- Review summary: {{review_summary}}
- Verification summary: {{verification_summary}}

Stage Boundaries:

- Do not skip unfinished critical tasks.
- Do not silently change the OpenSpec scope.
- Do not report review-ready without review evidence such as an MR, merge commit, or head SHA.

Blocked Conditions:

If implementation cannot continue, a user decision is required, OpenSpec tasks are unclear, or the current state is not review-ready, return `blocked` or `partial`.
```

### Slash-owned stage with supporting routes

```md
/ios-gitlab-merged-mr-review {{review_target}}

Stage Boundaries:

- Judge merge safety from the merged state, not just the patch summary.
- Keep `/ios-gitlab-merged-mr-review` as the stage owner; use supporting routes such as `gitnexus-impact-analysis` only when the findings need downstream-contract evidence.
- Do not downgrade findings just to unblock the workflow.

Blocked Conditions:

If the merged target, review scope, or required evidence is unavailable, return `blocked`.
```

## Related References

- `prompt-placeholder-spec.md`
  for legal double-brace template syntax and available key rules.
- `step-contract-spec.md`
  for `output_schema`, `failure_schema`, and verifier behavior.
- `workflow-authoring-guide.md`
  for the full workflow authoring sequence.
