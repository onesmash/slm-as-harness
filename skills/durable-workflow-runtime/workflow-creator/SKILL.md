---
name: durable-workflow-runtime:workflow-creator
description: |
  Load when the user asks for `durable-workflow-runtime:workflow-creator`,
  creating a new durable workflow, designing concrete workflow stages, generating
  workflow contracts/prompts/policy/verifiers, or adding a business workflow to
  `workflow-binding.json`. Skip normal start/resume execution.
---

# Durable Workflow Runtime Workflow Creator

This is an authoring companion to `durable-workflow-runtime`. It turns a user
request for a new workflow into concrete workflow files: stage contracts,
runtime state, transition policy, GraphBuilder metadata, prompt assets,
verifiers, flowchart documentation, manifest metadata, and the
`workflow-binding.json` catalog entry. On success it also creates a slash-only
shortcut skill named `workflow:<workflow_id>` under the same
`durable-workflow-runtime` bundle.

## Use This Surface

First, capture or infer a concrete workflow spec. If the user provides a source
URL or prose process, extract the durable control surfaces before generation:
dependencies, installed references, stage-level skill routes, prompt sections,
state carry-forward, repair gates, stage outputs, and regression-test intent. If
the user has not supplied enough detail, ask only for the missing business
decisions that affect stages, outputs, state, or routing.

Then create the scaffold:

```bash
python <workflow-creator-skill-root>/scripts/create_workflow.py \
  --workflow-id <workflow_id> \
  --flow-description "<when this workflow should be selected>"
```

This always creates the workflow-local blueprint at
`workflow-runtime/workflows/<workflow_id>/spec.json`. Fill that file with the
concrete business stages, then rerun the creator to regenerate the workflow
from its own blueprint:

```bash
python <workflow-creator-skill-root>/scripts/create_workflow.py \
  --workflow-id <workflow_id> \
  --force
```

Do not keep a second checked-in spec elsewhere in the repo. The workflow-local
`spec.json` is the only long-lived workflow blueprint.

After generation, run one subagent-backed agent review pass before treating the
workflow as shipped. The script writes
`workflow-runtime/workflows/<workflow_id>/references/agent-review.md`; use that
file as the review checklist. The generator owns the mechanical surfaces
(`contract.py`, basic `state.py`, linear `policy.py`, GraphBuilder plumbing,
prompt assets, manifest, binding entry). The coordinating agent owns the
semantic review orchestration, and the review subagents own semantic
correctness checks such as prompt-contract alignment, verifier strength,
business repair routing, state carry-forward, final-stage gates, and
regression-test coverage.

Before launching the review subagents, explicitly ask the user for permission
and wait for their answer. This is a hard gate: if the user has not authorized
subagent use yet, stop and request authorization instead of silently replacing
the review with a single-thread pass. Once authorized, use multiple review
subagents to inspect the spec, generated code, or tests from different angles.
Typical angles include a prompt-focused pass (`prompts/*.md`), a
verifier-focused pass (`verifiers.py` plus verifier declarations), a
contract-focused pass (`contract.py` and output schemas), and a
graph/runtime-flow pass (`graphbuilder_runtime.py`, `policy.py`, and
`references/flowchart.md`).

This subskill is expected to live under
`durable-workflow-runtime/workflow-creator/`, so the default runtime root is
`<workflow-creator-skill-root>/..`. If the runtime skill lives elsewhere, pass
it explicitly:

```bash
python <workflow-creator-skill-root>/scripts/create_workflow.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --workflow-id <workflow_id> \
  --flow-description "<when this workflow should be selected>"
```

Use `--force` only when regenerating or replacing an existing workflow from its
workflow-local `spec.json`.

## Authoring Contract

- Use a Python-package-safe `workflow_id`, such as `pdf_processing`, not
  `pdf-processing`.
- Create concrete stage IDs, step contracts, prompt files, policy transitions,
  verifier functions, and the flowchart from the user's business workflow.
- Write each stage `prompt` as the rendered first line of the prompt asset, not
  as a generic stage summary or a mini-SOP for the routed skill. It should name
  the single primary skill owner, the stage goal, the execution object or
  artifact, and the minimum workflow inputs needed to start the step. When a
  stage routes to skills, encode the owner with a direct slash invocation and
  include the concrete handle it should operate on, such as
  `/brainstorming {{workflow_goal}}` or
  `/openspec-apply-change {{change_name}} using {{change_path}}, {{tasks_path}}, and {{openspec_design_path}}`.
  Phrase the rest as workflow intent: what must be accomplished, what artifact
  should exist, and which boundary or approval gates matter. Do not teach the
  invoked skill how to perform its own checklist; the skill body owns that. If
  the prompt needs many procedural instructions to make sense, split or redefine
  the stage instead of overloading the action line. Additional routed skills are
  auxiliary only and should support the primary owner rather than replace it. If
  you cannot name a single primary owner, treat that as a stage-boundary problem
  and split or redefine the stage instead of writing a combined action line. Do
  not expect `skill_routing` to generate this sentence; it is routing metadata
  and may list multiple candidate skills.
- Keep generated prompt assets lean. Prefer stage goal, workflow context,
  boundaries, and blocked conditions over copying step-by-step SOP into the
  prompt body. Do not model a separate `prompt_sections.tasks` field in new
  specs; put only stage intent and short execution handles in the action line.
  Use `prompt_sections.context` for background, summaries, long JSON, previous
  review or verification evidence, and other auxiliary context. Do not put
  `Stage goal` or `Workflow goal` entries in `prompt_sections.context`; the
  stage goal belongs in `prompt_sections.stage_goal`, and the workflow goal
  should appear only when the action line or real auxiliary context needs the
  `{{workflow_goal}}` handle. In
  `boundaries`, capture only workflow-owned guardrails, handoff limits, or scope
  restrictions. Do not restate the invoked skill's internal checklist unless
  the workflow is adding a stricter boundary that the skill would not know by
  itself.
- Populate `dependencies`, `installed`, `skill_routing`, `prompt_sections`,
  `state_updates`, `template_context_keys`, `stage_kind`, `outcome_routes`,
  simple `repair_conditions`, `transitions`, `verifier_rules`,
  `verifier_templates`, `custom_verifier_requirements`, and
  `regression_tests` when the source material implies them. A generated
  workflow should not be a shallow linear skeleton unless the user explicitly
  asked for a blank starting point.
- Treat dependency `source` as the installation/provenance source, not the
  currently resolved local path. Use package names, repository URLs, catalog IDs,
  or MCP server names. Do not write `.codex/skills/.../SKILL.md`,
  `~/.agents/skills/...`, or other local paths into `dependencies[].source` or
  `installed[].source`; preflight reports local resolution through `location`.
- Declare installable top-level skills as workflow dependencies. Do not declare
  package-internal child skills as separate dependencies; route stage-specific
  operations through the parent skill and describe the operation in
  `skill_routing.operations`. When an input spec declares a skill dependency or
  installed entry with `source: skill-catalog:<parent>/<child>`, the creator
  normalizes that child dependency and matching routes to `<parent>`.
- Keep `workflow-runtime/workflows/<workflow_id>/spec.json` aligned with the
  workflow's intended shape. It is the durable blueprint for future edits, so
  update it when stages, prompts, outputs, dependencies, or repair gates change.
  Do not maintain a second checked-in workflow spec elsewhere in the repo.
- Prefer a linear happy path through `stage_kind: "main"` stages with shared
  blocked/partial/failed repair handling unless the user describes a real
  branch. If they describe business-specific failure recovery, declare it in
  `stages[].outcome_routes` and add a `stage_kind: "recovery"` stage with a
  `recovery_return_node`. If they describe a successful business branch that can
  be expressed through structured output, declare it in `stages[].transitions`
  so `policy.py` and `flowchart.md` are generated from the spec.
- Use `transitions` for normal business branches and `repair_conditions` only
  for repair/unblock behavior. Do not put the same output condition in both
  lists for one stage; generated policy evaluates repair conditions first.
- Add or update regression tests for the generated workflow before treating it
  as shipped. Keep workflow-specific tests under that workflow's own directory,
  such as `workflow-runtime/workflows/<workflow_id>/tests/test_workflow.py`; do
  not add them to the core runtime test file.
- Use `verifier_templates` for common complex checks such as list item required
  keys, conditional required fields, uniqueness, minimum counts, and artifact
  section checks when the DSL expresses the invariant cleanly. When the
  acceptance rule is more domain-specific or cross-cutting than the built-in
  templates support, declare it explicitly in
  `custom_verifier_requirements` with clear implementation notes so the
  authoring pass can generate concrete `verifiers.py` scaffolds or hand-written
  verifier code before review without losing the intent from `spec.json`. The
  generated requirement-scoped verifier should stay self-contained when
  practical, or call stable shared-module helpers imported into `verifiers.py`.
  The review pass should validate or refine that generated verifier logic, not
  be the first place where it appears.
- When a `custom_verifier_requirement` needs human-authored follow-up across
  `verifiers.py`, `policy.py`, `state.py`, or workflow tests, prefer
  `implementation_surface`, `hint_pseudocode`, and `test_intent` over relying
  on free-form `implementation_notes` alone. Treat these as authoring hints for
  hand-written code and regression coverage, not generator-executed DSL. If the
  verifier needs reuse, move the reusable logic into a stable shared module
  rather than adding same-file helper layers in `verifiers.py`.
- Complete the generated `references/agent-review.md` review pass with review
  subagents before calling the workflow complete. That review should start from
  `spec.json`: verify the workflow boundary, stages, prompts, outputs, state
  promotion, routing, outcome routes, recovery return points, verifier rules,
  verifier templates, and regression tests before inspecting generated files.
  If subagent authorization is still missing, block and request it rather than
  treating a single-thread review or a passing import as proof that the
  business workflow is correct.
- Do not call `bridge.py start`, `bridge.py resume`, or `bridge.py preflight`
  for creation.

Read `references/workflow-creator-cli-spec.md` for the workflow spec shape. Read
`../references/workflow-authoring-guide.md` when editing the generated workflow
logic beyond the generated linear path.
