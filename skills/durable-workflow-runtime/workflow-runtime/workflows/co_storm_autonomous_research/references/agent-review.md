# Agent Review for `co-storm-autonomous-research`

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

- `state_mode`: `custom`.
- When `state_mode` is `custom`, review the existing workflow `state.py` as a
  domain-owned implementation and verify strict persisted-state validation,
  bounded serialization, and fail-closed verifier promotion before sign-off.

## Declared Custom Verifier Requirements

### `launch_expert_subagents`

- `expert_results_match_roster`: The expert-result stage must return exactly one evidence-grounded result for every persisted expert, merge unnumbered new_evidence onto evidence_registry as an append-only prefix-preserving list, and keep a safe, distinct artifact for each result.
  Signals: `expert_roster`, `round_index`, `expert_round_index`, `expert_results`, `expert_results_complete`, `evidence_registry`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Python imports: `re`, `pathlib`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Require expert_results_complete to be true.
    - Require persisted expert_roster to contain unique records with exactly non-empty id, role, and brief string fields, and use those ids as the exact expected result order.
    - Require expert_round_index to be a positive integer equal to persisted state.round_index + 1 and no greater than constraints.max_rounds.
    - Require expert_results to have exactly one object per roster id; each object must contain exactly expert_id, summary, artifact_path, and new_evidence, with unique expert ids and paths.
    - Require each new_evidence item to be an unnumbered non-empty string with at least one ' — ' separator (split on the FIRST occurrence; the claim may itself contain ' — '), a non-empty locator, and a non-empty claim; reject entries that contain [n] citation markers.
    - Treat returned evidence_registry as the exact persisted list (same strings and order) plus newly numbered entries; do not normalize whitespace in the persisted prefix.
    - Merge new_evidence in roster order, skip locators already present in the persisted prefix or earlier experts, and require new citation ids to start at max(persisted id)+1 with no gaps.
    - Reject a rewritten persisted prefix, duplicate locators, more than three unused new_evidence items per expert, or a merged registry longer than 128 entries.
    - Require every citation identifier in a summary or artifact to exist in the merged registry, and require the union of each expert's summary and artifact citations to include at least one merged registry identifier.
    - Resolve each artifact_path beneath repo_root and reject absolute paths, traversal, symlinks, missing or non-regular files, empty files, and invalid UTF-8.
    - Read each artifact through a bounded UTF-8 check so an oversized artifact cannot exhaust verifier memory.
  Test intent:
    - Accept two roster-matching results with distinct readable artifacts that cite only persisted evidence and return the persisted registry unchanged.
    - Accept a merge that preserves the persisted prefix and appends contiguous new citation ids from unnumbered new_evidence.
    - Reject an unknown, missing, duplicate, or out-of-order expert id.
    - Reject a rewritten persisted registry prefix, a skipped citation id, a duplicated locator, more than three unused retrieved items for one expert, or a new_evidence item that is not locator — claim.
    - Reject a malformed persisted roster, skipped round, malformed result fields, duplicate artifact paths, an ungrounded result, an unknown citation, or an unsafe or missing artifact.
- `evidence_registry_byte_budget`: The merged evidence_registry must stay within a serialization-safe byte budget: the full list serialized as UTF-8 must not exceed 192 KiB even when the 128-entry count cap is met, so the workflow state never approaches the runtime MAX_WORKFLOW_LIST_BYTES limit.
  Signals: `evidence_registry`
  Implementation surfaces: `verifier`, `workflow-specific regression tests`
  Python imports: `json`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Read the merged evidence_registry from the observation output; if it is not a list of strings, return None (shape is enforced elsewhere).
    - Serialize the list with json.dumps(registry, ensure_ascii=False) and compute the UTF-8 byte length.
    - If the byte length exceeds 192 * 1024, return an error naming the actual size and the budget.
  Test intent:
    - Accept a merged registry whose UTF-8 serialization stays under the byte budget.
    - Reject a merged registry whose UTF-8 serialization exceeds 192 KiB even when the entry count is at or under 128.

### `autonomous_roundtable`

- `roundtable_flags_match_decision`: The autonomous roundtable must select exactly one routing decision, preserve the prior transcript, advance exactly one round, require a completed expert-result package, and provide a deterministic topic-level semantic coverage assessment. A bounded_gap topic always carries unresolved open gaps and validation metrics, so any bounded_gap topic keeps coverage_sufficient=false; a complete report therefore contains only covered topics and an empty next_round_validation_plan.
  Signals: `round_decision`, `continue_roundtable`, `should_reorganize`, `ready_for_report`, `coverage_assessment`, `coverage_decision_rationale`, `next_round_validation_plan`, `report_scope_status`, `expert_results`, `expert_results_complete`
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
    - Require coverage_assessment records to have exactly topic_id, status, evidence_refs, open_gaps, and next_validation_metrics; topic ids must be non-empty and unique, statuses must be covered, bounded_gap, or missing, and evidence refs must resolve to evidence_registry ids.
    - Require all persisted coverage_map topics to appear verbatim as assessed topic ids on the first round, and preserve all topic ids from persisted coverage_assessment on later rounds.
    - Treat coverage_threshold only as a minimum number of assessed topics. Reject coverage_sufficient=true unless no topic is missing, covered topics have evidence and no gaps or metrics, and bounded gaps have evidence, explicit gaps, and metrics; allow the Moderator to keep coverage_sufficient=false for material bounded gaps.
    - When coverage_sufficient is false, require next_round_validation_plan to equal the complete set of `topic_id — metric` strings for every missing topic and every bounded_gap topic the Moderator keeps unresolved.
    - Require continue to carry a missing or materially unresolved bounded_gap topic; require complete report to have sufficient coverage and no pending plan.
    - At max_rounds, allow insufficient coverage only as a partial report with a non-empty next_round_validation_plan; never mark forced stopping as complete.
  Test intent:
    - Accept a continue decision with only continue_roundtable true, a strictly incremented round, and one appended transcript turn.
    - Reject ambiguous decisions with two true flags.
    - Reject a report decision before semantic coverage is sufficient unless max_rounds has been reached and the report is explicitly partial.
    - Reject coverage_sufficient when threshold-sized topic counts still include a missing topic.
    - Accept a Moderator continuation when a structurally valid bounded gap is judged material and its metrics are carried into the plan.
    - Reject a covered topic that still contains gaps or validation metrics.
    - Reject a first-round assessment that replaces a warm-start coverage topic.
    - Reject a validation plan that is unrelated to or omits an unresolved topic metric.
    - Reject missing, malformed, or unresolvable evidence references in the semantic assessment.
    - Reject a skipped round or a rewritten transcript prefix.
    - Reject a Moderator turn that has no completed expert-result package.
- `merged_evidence_registry_is_preserved`: The Moderator must carry forward the merged evidence_registry exactly; new numbered evidence is produced only by launch_expert_subagents.
  Signals: `evidence_registry`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Require persisted evidence_registry to be a non-empty list of strings.
    - Require output.evidence_registry to equal the persisted list exactly (same strings and order).
    - Reject dropped, rewritten, reordered, or newly numbered registry rows.
  Test intent:
    - Accept a Moderator turn that returns the persisted merged registry unchanged.
    - Reject a Moderator turn that drops a merged citation or rewrites a persisted row.

### `reorganize_knowledge_space`

- `reorganization_budget_is_respected`: Knowledge-space reorganization must advance the counter exactly once, preserve the evidence registry exactly, and respect the autonomous reorganization budget.
  Signals: `reorganization_count`, `reorganized`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Require reorganization_count to be an integer greater than zero and exactly one greater than persisted state.reorganization_count.
    - Read constraints.max_reorganizations from persisted state and reject counts above that value or a reorganization after the budget is exhausted.
    - Require output.evidence_registry to equal persisted state.evidence_registry exactly, including strings and order; reject additions, rewrites, reordering, and deletion.
  Test intent:
    - Accept the first reorganization when the configured budget is two.
    - Reject a reorganization count above the configured budget.
    - Reject a reorganization that skips a counter value.
    - Reject a reorganization that adds, rewrites, reorders, or deletes any evidence registry row.

### `synthesize_report`

- `report_uses_compact_evidence_index`: The rendered report body may use compact number-only [n] citations for readability, but it must end with exactly one Evidence index containing one exact source-locator-only row for every citation id used in the body.
  Signals: `report_path`, `report_sections`, `context`, `evidence_registry`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Python imports: `re`, `workflows.co_storm_autonomous_research.citation_locators`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Read the repository-relative report_path from structured_output safely under repo_root.
    - When context.output_dir is set, require the report artifact to remain under that canonical repository-relative output directory.
    - Verify that report_sections names at least two substantive rendered Markdown sections and matches the report artifact rather than relying only on the LLM-declared count.
    - Parse evidence_registry rows as [n] locator — optional claim; the locator is the text after [n] and before an em-dash separator, else the remainder of the row.
    - Strip HTML comments and raw HTML blocks, then identify the report body as the content before exactly one `## Evidence index` heading, allowing an optional numeric section prefix or the equivalent Chinese `## 证据索引` heading.
    - Extract bounded ASCII numeric [n] markers from the rendered report body, ignoring inline and fenced or indented Markdown code; reject oversized citation identifiers and unclosed comments or code spans.
    - Parse Evidence index rows in the exact form `- [n] locator`; allow one surrounding pair of Markdown backticks around the locator, but reject any ` — claim` suffix.
    - Require every body citation id to have exactly one matching index row whose locator equals the evidence_registry locator, reject duplicate, unknown, missing, empty, or unused index rows, and reject any registry locator repeated in the rendered report body.
    - Reject when the report has numeric body citations but no valid Evidence index, or when substantive content appears after the Evidence index.
  Test intent:
    - Accept a report whose body uses source [1] and source [2] and whose final Evidence index maps each id to the exact registry locator.
    - Reject a report that only writes [1] and [2] without an Evidence index.
    - Reject a report with duplicate, unknown, missing, or mismatched Evidence index rows.
    - Reject a report with substantive content after the Evidence index.
    - Reject a report that repeats a registry locator in the body, or hides a citation/index inside Markdown code.

### `verify_report`

- `report_citation_integrity`: Every numeric inline citation must resolve to grounded evidence, and the report must deterministically preserve the Moderator's complete-or-partial scope decision and all unresolved validation work before a pass can finalize.
  Signals: `report_path`, `verified_report_path`, `report_sections`, `context`, `evidence_registry`, `report_ready`, `quality_verdict`, `quality_findings`, `coverage_map`, `coverage_assessment`, `coverage_sufficient`, `next_round_validation_plan`, `report_scope_status`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Python imports: `workflows.co_storm_autonomous_research.citation_locators`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Read the repository-relative report path safely under repo_root.
    - When context.output_dir is set, require report_path and verified_report_path to remain under that canonical repository-relative output directory.
    - Require every coverage_map topic to appear among assessed topic ids; the assessment may include extra topics beyond the coverage_map (subset check, not equality).
    - Extract bounded ASCII numeric markers such as [1] from rendered Markdown and parse bounded numeric identifiers from evidence_registry entries; reject oversized identifiers instead of converting them to integers.
    - Reject unknown markers, missing or empty evidence entries, or a pass verdict with no citation markers.
    - Require verified_report_path to resolve to the same repository-relative regular file as report_path.
    - Require `Report scope: complete` only when state.report_scope_status is complete, coverage_sufficient is true, and next_round_validation_plan is empty.
    - Treat only missing topics as unresolved when the report scope is complete and coverage_sufficient is true: a bounded_gap topic is considered handled in that state (matching the Moderator's immaterial-gap allowance with an empty next-round plan), so it must not block a complete report. For a partial report, every missing and bounded_gap topic remains unresolved and must be disclosed verbatim.
    - Ignore citations inside Markdown code and reject unresolved critical or blocker findings when quality_verdict is pass; make a repair verdict fail this verifier so policy enters repair_report.
  Test intent:
    - Accept a report whose [1] and [2] markers exist in the evidence registry.
    - Reject a report containing an unknown [99] marker.
    - Reject a pass verdict for an uncited report.
    - Reject a pass verdict with an unresolved critical finding.
    - Accept a partial report that explicitly discloses every unresolved topic, gap, metric, and plan item.
    - Reject a partial report that omits its marker or any unresolved validation item.
    - Reject a complete report when coverage_sufficient is false or validation work remains.
    - Reject a repair verdict as a verifier failure so the repair route is taken.
- `report_uses_compact_evidence_index`: The rendered report body may use compact number-only [n] citations for readability, but it must end with exactly one Evidence index containing one exact source-locator-only row for every citation id used in the body.
  Signals: `report_path`, `verified_report_path`, `report_sections`, `context`, `evidence_registry`
  Implementation surfaces: `verifiers.py`, `workflow-specific regression tests`
  Python imports: `re`, `workflows.co_storm_autonomous_research.citation_locators`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Read the same repository-relative report identified by persisted report_path and verified_report_path.
    - When context.output_dir is set, require both report paths to remain under that canonical repository-relative output directory.
    - When report_sections is present, verify it against at least two substantive rendered Markdown sections.
    - Parse evidence_registry rows as [n] locator — optional claim; the locator is the text after [n] and before an em-dash separator, else the remainder of the row.
    - Strip HTML comments, raw HTML blocks, fenced or indented code, and inline code when identifying the rendered report body; reject malformed or unclosed hidden regions.
    - Identify the report body as the content before exactly one `## Evidence index` heading, allowing an optional numeric section prefix or the equivalent Chinese `## 证据索引` heading.
    - Extract bounded ASCII [n] markers from the rendered body and parse Evidence index rows in the exact form `- [n] locator`; allow one surrounding pair of Markdown backticks around the locator, but reject a claim suffix.
    - Require every body citation id to have exactly one matching index row whose locator equals the evidence_registry locator, reject duplicate, unknown, missing, empty, or unused index rows, and reject any registry locator repeated in the rendered body.
    - Reject a pass-quality report with missing or invalid Evidence index content, or with substantive content after the Evidence index.
  Test intent:
    - Accept a report whose body uses source [1] and source [2] and whose final Evidence index maps each id to the exact registry locator.
    - Reject a report that only writes [1] and [2] without an Evidence index.
    - Reject a report with duplicate, unknown, missing, or mismatched Evidence index rows.
    - Reject a report with substantive content after the Evidence index.
    - Reject a report whose body repeats a registry locator or whose apparent index is hidden in Markdown code.


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
