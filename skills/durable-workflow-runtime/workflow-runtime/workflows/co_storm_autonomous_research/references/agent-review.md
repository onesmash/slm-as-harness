# Agent Review for `co_storm_autonomous_research`

This workflow was generated from `spec.json` by `workflow-creator`. Treat
`spec.json` as the source of truth for the review. The generated files prove the
spec can become importable runtime surfaces; they do not prove the spec describes
the right workflow.

## Generated Stage Path

- `warm_start_shared_space`
- `launch_expert_subagents`
- `autonomous_roundtable`
- `reorganize_knowledge_space`
- `synthesize_report`
- `verify_report`
- `repair_report`

## State Ownership

- `state_mode`: `generated`.
- When `state_mode` is `custom`, review the existing workflow `state.py` as a
  domain-owned implementation and verify strict persisted-state validation,
  bounded serialization, and fail-closed verifier promotion before sign-off.

## Declared Custom Verifier Requirements

### `launch_expert_subagents`

- `expert_results_match_roster`: The expert-result stage must return exactly one evidence-grounded result for every persisted expert and a safe, distinct artifact for each result.
  Signals: `expert_roster`, `round_index`, `expert_round_index`, `expert_results`, `expert_results_complete`, `evidence_registry`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Require expert_results_complete to be true.
    - Require persisted expert_roster to contain unique records with exactly non-empty id, role, and brief string fields, and use those ids as the exact expected result order.
    - Require expert_round_index to be a positive integer equal to persisted state.round_index + 1 and no greater than constraints.max_rounds.
    - Require expert_results to have exactly one object per roster id; each object must contain exactly expert_id, summary, and artifact_path, with non-empty strings and unique expert ids and paths.
    - Require expert_results expert_id values to equal the persisted roster ids in order.
    - Parse numeric citation identifiers from persisted evidence_registry, require every evidence detail to be non-empty, and reject any citation identifier in a summary or artifact that is not registered.
    - Resolve each artifact_path beneath repo_root and reject absolute paths, traversal, symlinks, missing or non-regular files, empty files, and invalid UTF-8.
    - Read each artifact through a bounded UTF-8 check so an oversized artifact cannot exhaust verifier memory.
    - Keep the result contract limited to the expert identity, grounded summary, and artifact path.
  Test intent:
    - Accept two roster-matching results with distinct readable artifacts that cite registered evidence.
    - Reject an unknown, missing, duplicate, or out-of-order expert id.
    - Reject a malformed persisted roster, skipped round, malformed result fields, duplicate artifact paths, an ungrounded result, or an unsafe or missing artifact.

### `autonomous_roundtable`

- `roundtable_flags_match_decision`: The autonomous roundtable must select exactly one routing decision, preserve the prior transcript, advance exactly one round, and require a completed expert-result package.
  Signals: `round_decision`, `continue_roundtable`, `should_reorganize`, `ready_for_report`, `expert_results`, `expert_results_complete`
  Implementation surfaces: `verifiers.py`, `policy.py`, `workflow-specific regression tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Count the three decision flags and require exactly one true value.
    - Map continue to continue_roundtable, reorganize to should_reorganize, and report to ready_for_report.
    - Require output.round_index to equal persisted state.round_index + 1 and require the returned transcript to preserve the persisted transcript as an exact prefix plus one new turn.
    - Require persisted expert_results_complete to be true and persisted expert_results to be non-empty before the Moderator can accept a round.
    - Require the Moderator to carry forward the persisted structured expert roster exactly.
    - Reject round_index values below one, reject values above constraints.max_rounds, and reject continue or reorganize once max_rounds has been reached.
    - When coverage_threshold is supplied, require coverage_map to contain at least that many distinct non-empty topics.
  Test intent:
    - Accept a continue decision with only continue_roundtable true, a strictly incremented round, and one appended transcript turn.
    - Reject ambiguous decisions with two true flags.
    - Reject a report decision before coverage_sufficient is true unless max_rounds has been reached.
    - Reject a skipped round or a rewritten transcript prefix.
    - Reject a Moderator turn that has no completed expert-result package.

### `reorganize_knowledge_space`

- `reorganization_budget_is_respected`: Knowledge-space reorganization must advance the counter exactly once, preserve grounded evidence entries, and respect the autonomous reorganization budget.
  Signals: `reorganization_count`, `reorganized`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Require reorganization_count to be an integer greater than zero and exactly one greater than persisted state.reorganization_count.
    - Read constraints.max_reorganizations from persisted state and reject counts above that value or a reorganization after the budget is exhausted.
    - Reject empty evidence entries and preserve the citation identifiers carried by the prior state.
  Test intent:
    - Accept the first reorganization when the configured budget is two.
    - Reject a reorganization count above the configured budget.
    - Reject a reorganization that skips a counter value.

### `verify_report`

- `report_citation_integrity`: Every numeric inline citation in the report must resolve to a non-empty grounded evidence entry carried in state; repair verdicts must explicitly fail the gate and pass verdicts must satisfy the final quality conditions.
  Signals: `report_path`, `verified_report_path`, `evidence_registry`, `report_ready`, `quality_verdict`, `quality_findings`, `coverage_map`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Read the repository-relative report path safely under repo_root.
    - Extract numeric markers such as [1] from the report and parse numeric identifiers from evidence_registry entries.
    - Reject unknown markers, missing or empty evidence entries, or a pass verdict with no citation markers.
    - Require verified_report_path to resolve to the same repository-relative regular file as report_path.
    - Reject unresolved critical or blocker findings when quality_verdict is pass, and make a repair verdict fail this verifier so policy enters repair_report.
  Test intent:
    - Accept a report whose [1] and [2] markers exist in the evidence registry.
    - Reject a report containing an unknown [99] marker.
    - Reject a pass verdict for an uncited report.
    - Reject a pass verdict with an unresolved critical finding.
    - Reject a repair verdict as a verifier failure so the repair route is taken.


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
