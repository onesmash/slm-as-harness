# Agent Review for `earnings-reviewer`

This workflow was generated from `spec.json` by `workflow-creator`. Treat
`spec.json` as the source of truth for the review. The generated files prove the
spec can become importable runtime surfaces; they do not prove the spec describes
the right workflow.

## Generated Stage Path

- `collect_earnings_packet`
- `analyze_earnings_call`
- `update_coverage_model`
- `audit_coverage_model`
- `repair_model_audit`
- `draft_earnings_note`

## State Ownership

- `state_mode`: `generated`.
- When `state_mode` is `custom`, review the existing workflow `state.py` as a
  domain-owned implementation and verify strict persisted-state validation,
  bounded serialization, and fail-closed verifier promotion before sign-off.

## Declared Custom Verifier Requirements

### `update_coverage_model`

- `variance_rows_cover_required_metrics`: Each of Revenue, GM, EBITDA, and EPS must appear in variance_rows with non-empty actual, consensus, prior_estimate, and source fields; unsourced figures must include [UNSOURCED].
  Signals: `variance_rows`, `variance_metrics`
  Implementation surfaces: `verifier`, `tests`
  Python imports: `re`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Require variance_rows to be a list of dicts.
    - For each required metric in Revenue, GM, EBITDA, EPS, find a row whose metric field matches case-insensitively.
    - Each matched row must have non-empty actual, consensus, prior_estimate, and source as strings.
    - Treat a source as trusted only when a token/prefix matches FactSet, Daloopa, 10-Q, 10-K, 8-K, 20-F, 6-K, or transcript; do not substring-match filing.
    - Reject sources that contain not/no/internal before a trusted token.
    - If the source is not trusted, the row must contain the exact marker [UNSOURCED].
  Test intent:
    - A complete four-metric variance table with sourced fields passes.
    - Missing EPS or a row lacking consensus fails.
    - An unsourced estimate without [UNSOURCED] fails.
    - Sources such as 'not a filing' or 'profiling notes' fail unless [UNSOURCED] is present.
- `handoff_payload_complete_when_required`: When requires_model_builder_handoff is true, handoff_payload must be an object with non-empty ticker, reporting_period, updated_model_path, and thesis_change_summary.
  Signals: `requires_model_builder_handoff`, `handoff_payload`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - If requires_model_builder_handoff is not true, return None.
    - Require handoff_payload to be a dict.
    - Require non-empty string fields ticker, reporting_period, updated_model_path, and thesis_change_summary.
  Test intent:
    - A required handoff with a complete payload passes.
    - A required handoff with an empty payload fails.
    - When requires_model_builder_handoff is false, an empty payload is allowed.


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
   authorization is still missing, stop and report the workflow as blocked
   instead of falling back to a one-thread review. If the user explicitly
   denies authorization, review the authorization gate as a normal business
   completion branch that should close the workflow before implementation
   planning, not as an error-state block.
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
   promoted state value. Generated prompt assets do not need to render a
   separate `Stage Goal:` heading; review the action line and prompt body
   against `prompt_sections.stage_goal` in `spec.json` instead of expecting that
   heading to appear verbatim in `prompts/*.md`.
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

- Baseline verifiers check required keys and schema types such as `boolean`,
  `string`, `string[]`, and explicitly declared `object[]` records. Structured
  records require a custom verifier or a suitable verifier template to define
  their required fields and cross-record invariants. Declared `verifier_rules`
  add simple deterministic checks such as enum membership, path existence, and
  non-empty fields.
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
  and step contracts. `prompt_sections.stage_goal` stays in `spec.json` as the
  review source of truth and is not required to appear as a separate `Stage
  Goal:` block in generated prompt assets.
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
