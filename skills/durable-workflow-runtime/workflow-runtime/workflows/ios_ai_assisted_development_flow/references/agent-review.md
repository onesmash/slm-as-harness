# Agent Review for `ios_ai_assisted_development_flow`

This workflow was generated from `spec.json` by `workflow-creator`. Treat
`spec.json` as the source of truth for the review. The generated files prove the
spec can become importable runtime surfaces; they do not prove the spec describes
the right workflow.

## Generated Stage Path

- `run_brainstorming`
- `propose_openspec_change`
- `refine_change_with_openspec`
- `approve_refine`
- `execute_implementation`
- `run_agentic_release_qa`
- `request_pre_merge_code_review`
- `verify_completion`

## Declared Custom Verifier Requirements

### `propose_openspec_change`

- `artifact_completeness`: OpenSpec proposal output must prove that proposal, tasks, and at least one durable design/spec artifact were created and reported consistently.
  Signals: `created_artifacts`, `proposal_path`, `tasks_path`, `openspec_design_path`, `spec_paths`
  Implementation surfaces: `verifier`, `tests`
  Hint pseudocode:
    - Require created_artifacts to mention proposal and tasks artifacts.
    - Require either openspec_design_path or spec_paths to provide at least one design/spec artifact path.
    - Reject outputs where created_artifacts omits the durable design/spec surface even if raw files exist.
  Test intent:
    - Reject outputs that only report proposal/tasks and omit any design/spec artifact.
    - Accept outputs that report proposal, tasks, and at least one design/spec artifact consistently.

### `refine_change_with_openspec`

- `talk_first_conversation_evidence`: OpenSpec refinement must prove that at least one real conversational exchange happened before the stage claimed readiness.
  Signals: `user_discussion_summary`, `discussion_turn_count`, `unresolved_questions`, `ready_for_apply`
  Implementation surfaces: `verifier`, `tests`
  Hint pseudocode:
    - Reject if discussion_turn_count is less than 1.
    - Reject if user_discussion_summary is missing or looks empty after trimming.
    - If unresolved_questions is empty and ready_for_apply is true, still require concrete conversation evidence instead of accepting a checklist-only output.
  Test intent:
    - Reject outputs that claim ready_for_apply without any discussion turn evidence.
    - Accept outputs that record a user discussion summary and a positive discussion_turn_count.

### `execute_implementation`

- `completed_tasks_consistency`: Implementation success output must not claim tasks are complete while still listing remaining tasks.
  Signals: `tasks_completed`, `remaining_tasks`, `completed_tasks`, `openspec_updates_required`
  Implementation surfaces: `verifier`, `tests`
  Hint pseudocode:
    - If tasks_completed is true, require remaining_tasks to be empty.
    - If tasks_completed is false and openspec_updates_required is not true, require remaining_tasks to be non-empty so the retry reason is concrete.
    - If verification_passed is false and openspec_updates_required is not true, reject the output so plain failing implementation cannot continue.
  Test intent:
    - Reject outputs that set tasks_completed=true while still listing remaining_tasks.
    - Reject unfinished implementation outputs that provide neither a remaining task list nor an OpenSpec refinement reason.
    - Reject implementation outputs that fail verification without explicitly routing back for OpenSpec updates.

### `run_agentic_release_qa`

- `ui_visual_qa_evidence`: When the workflow state says a UI surface changed and visual comparison inputs are available, release QA must report executed or blocked visual comparison evidence explicitly.
  Signals: `state.ui_surface_affected`, `state.design_comparison_source`, `state.runtime_visual_comparison_scope`, `release_qa_executed_checks`, `release_qa_blocked_checks`, `release_qa_artifacts`
  Implementation surfaces: `verifier`, `tests`
  Hint pseudocode:
    - Read ui_surface_affected, design_comparison_source, and runtime_visual_comparison_scope from persisted state.
    - Only enforce this requirement when all three values indicate visual QA should have been attempted.
    - Require executed_checks, blocked_checks, or artifacts to mention a visual diff, screenshot comparison, or design comparison pass.
  Test intent:
    - Reject UI-impacting release QA output that omits all visual comparison evidence despite having comparison inputs.
    - Accept UI-impacting release QA output when visual comparison evidence appears in executed checks, blocked checks, or artifacts.

### `request_pre_merge_code_review`

- `findings_include_severity_grouping`: Non-empty review findings must make severity explicit so the workflow can distinguish major merge blockers from lower-risk notes.
  Signals: `review_status`, `findings`
  Implementation surfaces: `verifier`, `tests`
  Hint pseudocode:
    - Skip the requirement when findings is empty.
    - Require each finding string to begin with or clearly include a recognized severity marker such as critical, high, medium, low, major, or minor.
  Test intent:
    - Reject change-requested findings that omit any severity marker.
    - Accept findings that carry an explicit severity prefix.

### `verify_completion`

- `ship_with_risks_requires_resolution_before_pass`: If persisted release QA ended in ship_with_risks, final completion verification may pass only after those residual risks are explicitly resolved with fresh evidence.
  Signals: `state.release_qa_verdict`, `state.release_qa_blocked_checks`, `verification_passed`, `verification_evidence`, `remaining_risks`, `release_qa_risks_resolved`, `release_qa_risk_resolution_summary`
  Implementation surfaces: `verifier`, `tests`
  Hint pseudocode:
    - Read release_qa_verdict and release_qa_blocked_checks from persisted state.
    - If release_qa_verdict is ship_with_risks and verification_passed is true, require release_qa_risks_resolved to be true, a non-empty release_qa_risk_resolution_summary, and fresh verification evidence that resolves the prior risk.
    - If release_qa_verdict is ship_with_risks and verification_passed is false, require remaining_risks or missing_verification_inputs to carry the residual risk forward.
  Test intent:
    - Reject passing completion output that ignores prior ship_with_risks residual QA risk.
    - Accept passing completion output only when it explicitly resolves the prior residual QA risk with fresh evidence.


## What The Script Generated

- `contract.py`: input contract, step contracts, skill routes, and verifier refs.
- `state.py`: durable state fields, serialization, basic state promotion, and repair bookkeeping.
- `policy.py`: declared transitions, default happy path, and shared blocked / partial / failed / verifier repair routing.
- `graphbuilder_runtime.py`: node definitions, start preview, transition preview, and prompt rendering.
- `verifiers.py`: baseline structured-output checks plus declared rule/template verifier plumbing.
- `prompts/*.md`: stage prompt assets.
- `references/flowchart.md`: linear flowchart and summarized repair loop.
- `manifest.json` and the `workflow-binding.json` entry.

## Agent-Owned Review Checklist

1. Before starting agent review, explicitly ask the user for permission to use
   review subagents and wait for consent. This workflow is not review-complete
   until that subagent-backed pass runs. Once authorized, use multiple review
   subagents to inspect the spec, generated code, or tests from different
   angles. Typical angles include prompt review (`prompts/*.md`), verifier
   review (`verifiers.py` and verifier declarations), contract review
   (`contract.py` and output schemas), and graph/runtime-flow review
   (`graphbuilder_runtime.py`, `policy.py`, and `references/flowchart.md`). If
   authorization is missing or denied, stop and report the workflow as blocked
   instead of falling back to a one-thread review.
2. Review `spec.json` first. Check whether it fully describes the intended
   workflow boundary, stage order, stage kinds, prompts, outputs, dependencies,
   state promotion, outcome routes, repair gates, shared repair helpers,
   recovery return points, business transitions, verifier rules, verifier
   templates, final prompt, and regression tests. Do not start by patching
   generated Python files.
3. Compare the spec against the closest mature workflow in
   `workflow-runtime/workflows/` to catch missing durable control surfaces:
   approvals, user input gates, repair return points, final-stage gates, and
   state carried into later prompts.
4. Verify stage boundaries in the spec: each stage should have one durable
   responsibility, clear blocked conditions, and no hidden implementation step.
   For skill-owned stages, require exactly one primary owner. If a stage needs
   multiple primary skills or none at all, split or redefine the stage.
5. Verify prompt-contract intent in the spec before reading generated prompts:
   each stage `prompt` should describe the stage goal, intended primary skill,
   execution object or artifact, and minimum workflow inputs. It should not
   teach the routed skill how to run its internal checklist. Multi-route stages
   should keep the primary route first and any others in supporting-only roles,
   `prompt_sections` should match `done_when`, and placeholders should come
   from start input or declared state promotion. When a placeholder name exists
   in both start input and promoted state, later prompts should prefer the
   promoted state value.
6. Verify output semantics in the spec: boolean fields must be booleans,
   enum-like fields should have `verifier_rules`, path fields should use
   `path_exists` when existence matters, common DSL-expressible invariants
   should use `verifier_templates`, and any remaining domain-specific verifier
   logic should be declared in `custom_verifier_requirements` with enough detail
   for generated custom verifier scaffolds to be completed before review.
7. Verify state promotion in the spec: every output needed by later prompts,
   final summary, repair logic, or tests should appear in `state_updates` and
   `template_context_keys` where appropriate.
8. Verify outcome and recovery routing in the spec: `outcome_routes` should
   cover business-specific `blocked`, `partial`, `failed`, or `verifier_failed`
   recovery paths; `stage_kind: "recovery"` stages should have the right
   `recovery_return_node`. Shared recovery helpers should never silently fall
   back to the first main stage when `return_stage_id` is missing.
9. Verify business repair routing and transitions in the spec:
   `repair_conditions` should mean repair/unblock behavior, `transitions` should
   mean normal business routing, and each target should be the right return
   point.
10. Verify final routing in the spec: the last main stage should only complete
   when declared verifier rules, verifier templates, any generated or completed
   custom verifier code required by `custom_verifier_requirements`, and business gates prove the
   workflow is ready for the final prompt.
11. Verify `regression_tests` in the spec cover start, resume, repair, verifier
   failure, business gates, final completion, prompt placeholder coverage, and
   recovery helper semantics such as returning to `return_stage_id`.
12. After the spec review, verify generated files faithfully implement the spec:
    `contract.py`, `state.py`, `policy.py`, `verifiers.py`, `prompts/*.md`,
    `references/flowchart.md`, `manifest.json`, and generated workflow tests
    should match the normalized blueprint. If semantics need to change, update
    `spec.json` first, then regenerate or make matching code edits.

## Common Generated Skeleton Gaps

- Baseline verifiers check required keys and flat schema types such as
  `boolean`, `string`, and `string[]`; stage return schemas must not use
  `object` or `object[]` because agents would have to infer hidden structure.
  Declared `verifier_rules` add simple deterministic checks such as enum
  membership, path existence, and non-empty fields.
- Output fields with stricter cross-field consistency or domain meaning should
  first be added to `spec.json` when expressible. Use `verifier_templates` for
  whitelistable flat checks such as conditional required fields, uniqueness,
  minimum counts, and artifact section checks when the DSL expresses the
  invariant cleanly; otherwise declare the requirement in
  `custom_verifier_requirements` instead of weakening the acceptance contract.
- Declared `custom_verifier_requirements` now generate requirement-scoped
  scaffolds in `verifiers.py`. Treat those functions as authoring-time work:
  finish or tighten them before review sign-off, then use agent review to
  validate/refine the resulting verifier logic and regression coverage.
- A generated `outcome_route`, `repair_condition`, `transition`, or recovery
  return follows the declared target; it does not know whether that target is
  the best business return point.
- Prompt placeholders are mechanically exposed from declared state updates, so
  missing prompt context is usually a spec gap in `state_updates` or
  `template_context_keys`. When a placeholder name exists in both start input
  and promoted state, generated prompt context now prefers the promoted state
  value; review workflows that rely on a stale start-input copy of the same key.
- Prompt assets are generated from declared prompt sections; they still need a
  human/agent pass to catch action lines that are vague or overly procedural,
  stale placeholders, missing blocked conditions, or drift between prompt text
  and step contracts.
- Shared recovery helpers should now be described in `spec.json` and stay on
  the recovery node when `return_stage_id` is missing. If review finds a
  workflow that still depends on a silent fallback, fix the workflow state
  bookkeeping instead of loosening policy.

## Review Output

Write findings first, ordered by severity. Prefer citing `spec.json` when the
source of the issue is an incomplete or ambiguous workflow declaration. Cite
generated files when they drift from the spec. If edits are needed, update
`spec.json` first, then regenerate or make matching workflow-file and test edits
before calling the workflow shipped.
