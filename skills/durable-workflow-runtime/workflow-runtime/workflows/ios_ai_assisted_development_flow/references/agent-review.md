# Agent Review for `ios_ai_assisted_development_flow`

This workflow was generated from `spec.json` by `workflow-creator`. Treat
`spec.json` as the source of truth for the review. The generated files prove the
spec can become importable runtime surfaces; they do not prove the spec describes
the right workflow.

## Generated Stage Path

- `run_brainstorming`
- `approve_subagent_review`
- `run_spec_review`
- `write_implementation_plan`
- `execute_implementation`
- `run_agentic_release_qa`
- `request_pre_merge_code_review`
- `verify_completion`

## State Ownership

- `state_mode`: `custom`.
- When `state_mode` is `custom`, review the existing workflow `state.py` as a
  domain-owned implementation and verify strict persisted-state validation,
  bounded serialization, and fail-closed verifier promotion before sign-off.

## Declared Custom Verifier Requirements

### `run_brainstorming`

- `ui_visual_inputs_require_meaningful_text`: When a UI surface is affected, visual QA inputs must contain meaningful non-whitespace text rather than placeholder whitespace.
  Signals: `ui_surface_affected`, `visual_spec_detail_summary`, `design_comparison_source`, `runtime_visual_comparison_scope`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Implementation notes: Normalize each required visual-QA input with trim semantics and fail closed when UI impact is true but any input is missing or whitespace-only.
  Hint pseudocode:
    - If ui_surface_affected is not true, do not apply this UI-specific requirement.
    - When ui_surface_affected is true, require visual_spec_detail_summary, design_comparison_source, and runtime_visual_comparison_scope to contain non-whitespace text.
  Test intent:
    - Reject UI-impacting brainstorming output whose visual-QA inputs are whitespace-only.
    - Accept non-UI brainstorming output without visual-QA inputs.
    - Accept UI-impacting brainstorming output with meaningful visual-QA inputs.

### `run_spec_review`

- `spec_review_outputs_require_artifacts`: The review stage must hand in concrete subagent review artifacts so the workflow can verify that development, design, and testing reviews really happened.
  Signals: `spec_review_perspectives`, `spec_review_subagent_summaries`, `spec_review_artifact_paths`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Require at least three non-empty artifact paths.
    - Require each artifact path to be a relative, canonical, regular UTF-8 Markdown file under docs/superpowers/specs/; reject absolute paths, parent-directory traversal, and symlink traversal.
    - Reject empty artifact files and deduplicate by canonical path, not only by the submitted string.
    - Require each artifact's Markdown content to name the single perspective encoded by its canonical path.
    - Require the combined artifact paths to clearly cover development, design, and testing review outputs.
    - Require three non-empty subagent summaries that map one-to-one to development, design, and testing instead of duplicating one perspective.
    - Reject repeated summaries or repeated artifact paths when they are being used to fake independent review coverage.
  Test intent:
    - Reject review output that provides review summaries without artifact paths.
    - Reject review output whose artifact paths do not exist or do not cover development, design, and testing.
    - Reject review output that repeats one summary or one artifact path while still claiming three independent perspectives.
    - Accept review output that hands in concrete review artifacts for all three perspectives.

### `write_implementation_plan`

- `planning_requires_subagent_execution_mode`: This workflow may continue only when planning records subagent-driven execution as the selected approach and does not ask the user to choose a different execution style.
  Signals: `execution_mode`, `ready_for_implementation`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Normalize execution_mode to lowercase.
    - Accept only subagent-driven as the implementation-ready mode.
    - If execution_mode is inline or any other value, reject the output or require ready_for_implementation to remain false.
    - If plan_update_summary, debugging_summary, or open_issues are present in state, require the revised planning output to acknowledge the replanning reason via plan_revision_reason.
  Test intent:
    - Reject planning outputs that pick inline execution while claiming implementation is ready.
    - Accept planning outputs that record subagent-driven execution with a written plan.
    - Reject replanning output that ignores recorded plan-update or implementation-learned reasons when such context exists in state.

### `execute_implementation`

- `completed_tasks_consistency`: Implementation success output must not claim tasks are complete while still listing remaining tasks.
  Signals: `tasks_completed`, `remaining_tasks`, `completed_tasks`, `plan_updates_required`, `verification_passed`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - If tasks_completed is true, require remaining_tasks to be empty.
    - If tasks_completed is false and plan_updates_required is not true, require remaining_tasks to be non-empty so the retry reason is concrete.
    - If verification_passed is false and plan_updates_required is not true, reject the output so plain failing implementation cannot continue.
  Test intent:
    - Reject outputs that set tasks_completed=true while still listing remaining_tasks.
    - Reject unfinished implementation outputs that provide neither a remaining task list nor a planning reason.
    - Reject implementation outputs that fail verification without explicitly routing back for plan updates.

### `run_agentic_release_qa`

- `ui_visual_qa_evidence`: When the workflow state says a UI surface changed and visual comparison inputs are available, release QA must report executed or blocked visual comparison evidence explicitly.
  Signals: `state.ui_surface_affected`, `state.design_comparison_source`, `state.runtime_visual_comparison_scope`, `release_qa_executed_checks`, `release_qa_blocked_checks`, `release_qa_artifacts`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Read ui_surface_affected, design_comparison_source, and runtime_visual_comparison_scope from persisted state.
    - Only enforce this requirement when all three values indicate visual QA should have been attempted.
    - Require executed_checks, blocked_checks, or artifacts to mention a visual diff, screenshot comparison, or design comparison pass.
  Test intent:
    - Reject UI-impacting release QA output that omits all visual comparison evidence despite having comparison inputs.
    - Accept UI-impacting release QA output when visual comparison evidence appears in executed checks, blocked checks, or artifacts.
- `release_qa_lists_require_meaningful_entries`: Release QA evidence lists must contain meaningful non-empty entries, not whitespace-only placeholders.
  Signals: `release_qa_verdict`, `release_qa_executed_checks`, `release_qa_blocked_checks`, `release_qa_risk_next_steps`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Trim each list entry before validation.
    - Reject ship outputs whose executed checks become empty after trimming.
    - Reject any verdict whose risk next steps become empty after trimming.
    - If blocked_checks is present, reject blocked_checks that only contain blank placeholders.
  Test intent:
    - Reject ship outputs with whitespace-only executed checks or next steps.
    - Reject outputs with whitespace-only blocked checks.
- `ship_verdict_requires_no_blocked_checks`: A ship verdict must not carry unresolved blocked checks or other outstanding QA issues forward.
  Signals: `release_qa_verdict`, `release_qa_blocked_checks`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Trim blocked_checks before validation.
    - If release_qa_verdict is ship, require blocked_checks to be empty after trimming.
  Test intent:
    - Reject ship outputs that still include blocked checks.
    - Accept ship outputs only when blocked checks are empty.
- `required_agent_device_evidence`: When agent_device_mode is required, release QA must prove that agent-device ran successfully with meaningful commands and artifact evidence; off or empty mode must not create a device gate.
  Signals: `context.agent_device_mode`, `context.agent_device_expected_version`, `context.agent_device_app_id`, `context.agent_device_artifact_path`, `context.agent_device_device`, `context.agent_device_evidence_dir`, `agent_device_status`, `agent_device_commands`, `agent_device_artifacts`, `agent_device_cli_version`, `agent_device_observed_device`, `agent_device_observed_app_id`, `agent_device_runner_status`, `agent_device_execution_receipt`, `release_qa_target_scope`, `release_qa_blocked_checks`
  Implementation surfaces: `verifier`, `state`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Implementation notes: The verifier must read the persisted workflow context, fail closed only for required mode, require the declared version/app/artifact/device/evidence inputs, require structured host observations for the actual CLI version, device, app, and runner status, require a bounded JSON execution receipt tied to the current workflow run, require runner-preparation evidence before device operations, require regular build and evidence files, and reject unsafe artifact paths. It must not require the CLI or device when mode is off or empty; command execution remains a host responsibility, while the verifier validates the returned observations, receipt, and bounded files.
  Hint pseudocode:
    - Read context.agent_device_mode from persisted state and normalize whitespace/case.
    - If the mode is not required, return no device-specific verifier error.
    - When required, require context to identify the expected CLI version, app, build artifact, target device, and evidence directory.
    - When required, require agent_device_status to equal succeeded, agent_device_commands to contain meaningful entries including runner preparation before device operations, agent_device_artifacts to contain safe relative paths under the repository, and release_qa_target_scope to identify the app/build/device target.
    - Require agent_device_cli_version to exactly match the expected version, agent_device_observed_device to exactly match the configured target device, agent_device_observed_app_id to exactly match the configured app id, and agent_device_runner_status to equal succeeded.
    - Require the declared build artifact and every evidence artifact to exist as regular non-symlink files under the repository and evidence directory.
    - Require agent_device_execution_receipt to point to a regular JSON file under the evidence directory whose run_id, status, CLI version, device, app, runner status, commands, build artifact, and artifacts match the current host observations and workflow run.
    - When session or replay suite is configured, require the reported values and corresponding receipt values to exactly match the configured values.
    - Reject required-mode output when release_qa_blocked_checks contains meaningful unresolved device blockers.
    - Keep actual CLI command execution in the workflow host/agent, and pass its observed version/device/app/runner results plus bounded artifact paths into the verifier.
  Test intent:
    - Accept release QA with agent_device_mode off and no device output.
    - Reject required mode when agent-device status, commands, or artifacts are missing.
    - Reject required mode when agent-device status is blocked or failed.
    - Reject required mode when version, app, build artifact, target device, or evidence destination is missing.
    - Reject required mode when an artifact path is absolute, traverses a parent directory, or bypasses the repository boundary.
    - Reject required mode when observed CLI/device/app/runner evidence is missing or mismatched.
    - Reject required mode when the declared build or evidence artifact is missing or not a regular file.
    - Reject required mode when the execution receipt is missing, malformed, from another run, or inconsistent with the reported host evidence.
    - Accept required mode when status, commands, artifacts, host observations, target scope, and release QA checks are meaningful.

### `request_pre_merge_code_review`

- `findings_include_severity_grouping`: Non-empty review findings must make severity explicit with a stable prefix and keep findings grouped by descending severity so the workflow can distinguish major merge blockers from lower-risk notes.
  Signals: `review_status`, `findings`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Skip the requirement when findings is empty.
    - Require each finding string to begin with an explicit severity prefix such as critical:, important:, high:, medium:, low:, major:, minor:, blocker:, p0:, or p1:.
    - Reject findings whose severity is only implied in prose or negated by surrounding text.
    - Reject findings that jump from lower severity back to higher severity later in the list.
  Test intent:
    - Reject change-requested findings that omit a severity prefix.
    - Accept findings that carry an explicit severity prefix.
    - Reject findings that only mention severity in prose without a stable prefix.
    - Reject findings whose order is not grouped from higher severity to lower severity.
- `findings_require_meaningful_entries`: Review findings must contain meaningful non-empty entries when findings are provided.
  Signals: `review_status`, `findings`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Trim each finding string before validation.
    - If review_status is changes_requested, reject findings that become empty after trimming.
  Test intent:
    - Reject changes_requested outputs whose findings are only blank strings.
- `approved_review_requires_no_findings`: An approved pre-merge review must not leave actionable findings behind.
  Signals: `review_status`, `findings`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Trim each finding string before validation.
    - If review_status is approved, require findings to be empty after trimming.
  Test intent:
    - Reject approved review outputs that still include findings.
    - Accept approved review outputs only when findings are empty.

### `verify_completion`

- `completion_evidence_lists_require_meaningful_entries`: Completion evidence and risk lists must contain meaningful non-empty entries after trimming whitespace.
  Signals: `verification_passed`, `verification_evidence`, `remaining_risks`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - Trim each list entry before validation.
    - Reject verification_evidence that becomes empty after trimming.
    - If verification_passed is false, reject remaining_risks when they contain only blank placeholders.
  Test intent:
    - Reject passing completion output with blank evidence items.
    - Reject failed completion output whose remaining_risks are only blank placeholders.
- `completion_requires_release_qa_and_review_approval`: Completion may pass only after release QA reached ship and pre-merge review reached approved; otherwise the workflow must keep iterating.
  Signals: `state.release_qa_verdict`, `state.review_status`, `verification_passed`, `state.open_issues`, `state.release_qa_blocked_checks`, `release_qa_risks_resolved`
  Implementation surfaces: `verifier`, `tests`
  Self-contained contract: keep this requirement-scoped verifier self-contained when practical.
  If reuse is needed, import stable helpers from shared modules outside verifiers.py.
  same-file helper dependencies as a blocking review issue.
  Hint pseudocode:
    - If verification_passed is true, require persisted state.release_qa_verdict == ship.
    - If verification_passed is true, require persisted state.review_status == approved.
    - If verification_passed is true, reject the output when persisted open_issues is non-empty.
    - If verification_passed is true and persisted release_qa_blocked_checks is non-empty, require release_qa_risks_resolved == true.
    - If release_qa_risks_resolved is true, require a non-empty release_qa_risk_resolution_summary that explains the fresh recheck evidence.
  Test intent:
    - Reject passing completion output when release QA did not end in ship.
    - Reject passing completion output when pre-merge review did not end in approved.
    - Reject passing completion output when unresolved open_issues are still recorded in state.
    - Reject passing completion output when release QA blocked checks are still unresolved.
    - Accept passing completion output when release QA blocked checks were rechecked and explicitly resolved.


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
