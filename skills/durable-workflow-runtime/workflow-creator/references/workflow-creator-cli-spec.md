# Workflow Creator CLI Spec

Read this file when invoking or maintaining:

- `<workflow-creator-skill-root>/scripts/create_workflow.py`
- the `durable-workflow-runtime:workflow-creator` authoring surface

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<workflow-creator-skill-root>/`.

## Purpose

`create_workflow.py` creates a new durable workflow in a runtime skill bundle.

This is an authoring surface, not an execution surface:

- it creates an empty workflow scaffold and keeps a workflow-local `spec.json`
- it regenerates workflow files from `workflow-runtime/workflows/<workflow_id>/spec.json`
- it generates `contract.py`, `state.py`, `policy.py`, `graphbuilder_runtime.py`,
  `verifiers.py`, prompt assets, and `references/flowchart.md`
- it writes a workflow `manifest.json`
- it registers a `workflow-binding.json` catalog entry
- it creates a slash-only shortcut skill at
  `workflow-shortcuts/<workflow_id>/SKILL.md` with `name: workflow:<workflow_id>`
- it writes `references/agent-review.md` so a reviewing agent can check the
  generated workflow before it is treated as complete
- it does not run dependency preflight
- it does not allocate host I/O paths
- it does not create or mutate runtime run state

## Command

Create the workflow scaffold first:

```bash
python3 <workflow-creator-skill-root>/scripts/create_workflow.py \
  --workflow-id <workflow_id> \
  --flow-description "<when this workflow should be selected>"
```

Then edit `workflow-runtime/workflows/<workflow_id>/spec.json` in place and
regenerate from that workflow-local blueprint:

```bash
python3 <workflow-creator-skill-root>/scripts/create_workflow.py \
  --workflow-id <workflow_id> \
  --force
```

When the runtime skill lives elsewhere:

```bash
python3 <workflow-creator-skill-root>/scripts/create_workflow.py \
  --runtime-skill-root <path/to/durable-workflow-runtime> \
  --workflow-id <workflow_id> \
  --flow-description "<when this workflow should be selected>"
```

Do not keep a second checked-in workflow spec elsewhere in the repo. The only
long-lived workflow blueprint is
`workflow-runtime/workflows/<workflow_id>/spec.json`.

## Workflow Spec Shape

Write the workflow-local `spec.json` as JSON. This keeps the generator
dependency-free and easy to test.

```json
{
  "workflow_id": "paper_review_flow",
  "flow_description": "Review academic drafts through context intake, critique, and final synthesis.",
  "start_input_schema": {
    "task_input": {
      "goal": "string",
      "manuscript_path": "string?"
    },
    "context": {
      "repo_root": "string"
    },
    "constraints": {
      "max_steps": "integer?"
    }
  },
  "stages": [
    {
      "step_id": "collect_review_context",
      "stage_kind": "main",
      "intent": "collect_review_context",
      "expected_artifact": "review scope and manuscript context",
      "prompt": "/academic-paper-reviewer collect the manuscript context, target venue, review criteria, and missing inputs.",
      "prompt_sections": {
        "stage_goal": "Collect the manuscript context, target venue, review criteria, and missing inputs.",
        "context": [
          "Task input: {{task_input_json}}"
        ],
        "boundaries": [
          "Do not critique the manuscript yet",
          "Do not invent unavailable manuscript facts"
        ],
        "blocked_conditions": [
          "Block if the manuscript path or source text is unavailable"
        ]
      },
      "skill_routing": [
        {
          "skill": "academic-paper-reviewer",
          "operations": ["review scope intake", "manuscript review planning"],
          "file_patterns": ["*.md", "*.docx", "*.pdf"],
          "usage_notes": [
            "Use when the manuscript or target venue requires academic review judgment"
          ]
        }
      ],
      "done_when": [
        "The manuscript scope is clear",
        "Missing inputs are listed or confirmed absent"
      ],
      "output_schema": {
        "review_scope": "string",
        "missing_inputs": "string[]",
        "ready_for_critique": "boolean"
      },
      "state_updates": [
        {
          "state_key": "review_scope",
          "output_key": "review_scope",
          "kind": "string"
        },
        {
          "state_key": "missing_review_inputs",
          "output_key": "missing_inputs",
          "kind": "list"
        }
      ],
      "template_context_keys": ["review_scope", "missing_review_inputs"],
      "transitions": [
        {
          "output_key": "ready_for_critique",
          "operator": "is_false",
          "next_node": "collect_review_context",
          "branch_kind": "retry",
          "reason": "review context needs another intake pass"
        }
      ],
      "failure_schema": {
        "blocked_reason": "string?",
        "error_message": "string?",
        "missing_inputs": "string[]?"
      }
    },
    {
      "step_id": "run_structured_critique",
      "stage_kind": "main",
      "intent": "run_structured_critique",
      "expected_artifact": "structured critique findings",
      "prompt": "Review the manuscript for claims, evidence, structure, method, and revision risks.",
      "done_when": [
        "Major findings are grouped by severity",
        "Each finding has evidence and an actionable recommendation"
      ],
      "output_schema": {
        "findings": "string[]",
        "overall_risk": "string",
        "ready_for_synthesis": "boolean"
      },
      "verifier_rules": [
        {
          "output_key": "findings",
          "operator": "non_empty",
          "message": "findings must not be empty"
        },
        {
          "output_key": "overall_risk",
          "operator": "one_of",
          "value": ["low", "medium", "high"],
          "message": "overall_risk must be low, medium, or high"
        }
      ],
      "verifier_templates": [],
      "outcome_routes": [
        {
          "outcome": "verifier_failed",
          "next_node": "repair_structured_critique",
          "branch_kind": "repair",
          "reason": "critique verifier failed; route to critique-specific repair"
        }
      ],
      "failure_schema": {
        "blocked_reason": "string?",
        "error_message": "string?"
      }
    },
    {
      "step_id": "repair_structured_critique",
      "stage_kind": "recovery",
      "recovery_return_node": "run_structured_critique",
      "intent": "repair_structured_critique",
      "expected_artifact": "repaired structured critique findings",
      "prompt": "Repair structured critique findings and rerun the critique verifier.",
      "done_when": [
        "Critique findings have required evidence fields",
        "The critique can be rechecked"
      ],
      "output_schema": {
        "repair_summary": "string"
      },
      "failure_schema": {
        "blocked_reason": "string?",
        "error_message": "string?"
      }
    }
  ],
  "shared_repair_helpers": {
    "request_unblocking_input": {
      "prompt": "Request the exact external input needed to unblock the workflow and preserve the original return stage.",
      "expected_artifact": "user action needed to unblock the workflow",
      "done_when": [
        "Identify the blocking reason",
        "Ask the user for the input, approval, or resource required to continue"
      ],
      "output_schema": {
        "blocking_reason": "string",
        "user_action_needed": "string",
        "suggested_next_input": "string?"
      }
    },
    "repair_and_resume": {
      "prompt": "Repair the previous workflow step using the persisted failure details and prepare a safe retry.",
      "expected_artifact": "repair actions needed before returning to the original stage",
      "done_when": [
        "Explain why the original step needs repair",
        "Return retry_reason, retry_notes, and repair_actions"
      ],
      "output_schema": {
        "retry_reason": "string",
        "retry_notes": "string",
        "repair_actions": "string[]"
      }
    }
  },
  "final_step_id": "finalize_review_report",
  "final_prompt": "Prepare the final review report and summarize follow-up actions.",
  "dependencies": [
    {
      "id": "academic-paper-reviewer",
      "type": "skill",
      "required": true,
      "scope": "either",
      "source": "skill-catalog:academic-paper-reviewer",
      "purpose": "Route academic review stages to the reviewer skill"
    }
  ],
  "installed": [
    {
      "id": "academic-paper-reviewer",
      "type": "skill",
      "scope": "either",
      "source": "skill-catalog:academic-paper-reviewer",
      "recorded_at": "2026-06-03T00:00:00Z",
      "recorded_by": "workflow-creator"
    }
  ],
  "regression_tests": [
    {
      "name": "context_not_ready_routes_to_context",
      "type": "transition",
      "current_step_id": "collect_review_context",
      "observation": {
        "status": "succeeded",
        "summary": "Context still needs source text.",
        "structured_output": {
          "review_scope": "Draft review",
          "missing_inputs": ["manuscript"],
          "ready_for_critique": false
        }
      },
      "expected_next_node": "collect_review_context",
      "expected_branch_kind": "retry"
    },
    {
      "name": "critique_rejects_unknown_risk",
      "type": "verifier",
      "step_id": "run_structured_critique",
      "observation": {
        "status": "succeeded",
        "summary": "Critique done.",
        "structured_output": {
          "findings": [],
          "overall_risk": "unknown",
          "ready_for_synthesis": true
        }
      },
      "expected_passed": false
    }
  ]
}
```

`prompt` is rendered directly as the first line of the prompt asset. Write it as
the clear execution action the host agent should take, not as a generic stage
summary. A good `prompt` names the primary skill owner, the action, the execution
object, and the minimum inputs needed to start the step. When a stage uses routed
skills, it should still have one primary skill owner; prefer direct slash
invocation for that owner and keep any additional routed skills in supporting
roles. If you cannot point to one primary owner, treat that as a stage-design
problem and split or redefine the stage instead of writing a combined action
line.

Prefer this shape:

```md
/academic-paper-reviewer collect the manuscript context, target venue, review criteria, and missing inputs.
```

or, when the stage depends on concrete workflow artifacts:

```md
/openspec-apply-change {{change_name}} using {{change_path}}, {{tasks_path}}, and {{openspec_design_path}}; address {{issues_found}} and {{failed_commands}} if present before returning review-ready evidence.
```

Avoid vague prompts whose required execution handles only appear later in
`prompt_sections.context`, such as:

```md
/openspec-apply-change implement the selected OpenSpec change and leave it ready for review.
```

Do not rely on `skill_routing` to generate this sentence. `skill_routing`
describes when tools/skills are relevant; keep the primary route first and any
auxiliary routes after it, but still write the executable instruction yourself.
Use `prompt_sections.context` for background summaries, long JSON, prior review
or verification evidence, and other auxiliary context that should inform the
step but is not the short handle the action operates on. Do not duplicate
`prompt_sections.stage_goal` or add a generic `Workflow goal` entry there.

The generator creates a linear happy path through `stage_kind: "main"` stages,
plus shared `request_unblocking_input` and `repair_and_resume` fallback stages
for blocked, partial, failed, and verifier-failed observations. Add
`stages[].outcome_routes` when a common runtime outcome should go to a
business-specific recovery node. Add `stages[].transitions` when a successful
stage should branch based on structured output. Each transition uses
`output_key`, `operator`, optional `value`, `next_node`, `branch_kind`, and
`reason`; target nodes must be another declared stage, the final step, or a
shared repair node.

Use `stages[].verifier_rules` for deterministic checks beyond schema shape. The
supported operators are the repair-condition operators plus `one_of` and
`path_exists`. Use `stages[].verifier_templates` for whitelistable complex
checks that should still generate static Python verifier code. When the
acceptance logic is too domain-specific for the built-in templates, record it
in `stages[].custom_verifier_requirements` so the generator can emit
requirement-scoped custom verifier scaffolds in `verifiers.py` and preserve the
same intent in `spec.json` and `agent-review.md`. Use `regression_tests` to generate
`workflow-runtime/workflows/<workflow_id>/tests/test_workflow.py` with
transition and verifier assertions.
If the business workflow needs routing or validation semantics that cannot be
expressed in these fields, edit the generated workflow and keep `spec.json`
aligned.

Generated observability contract:

- generated workflows preserve compact repair state in `state.repair_context`
  and `repair_payload`
- runtime `yield` responses should surface a compact host-visible
  `retry_context` when a step is re-yielded because of repair, blocked input,
  or verifier failure
- preferred minimum mapping:
  - `repair_payload.category -> retry_context.category`
  - `repair_payload.summary -> retry_context.summary`
  - `repair_payload.requirements -> retry_context.requirements`
- this transport surface is intentionally smaller than persisted run state; do
  not require hosts to inspect `runs/<run_id>.json` for ordinary retry
  diagnosis

## Generated Policy Evaluation Order

For each business stage, generated `policy.py` evaluates routing in this order:

1. `stages[].outcome_routes` route declared `blocked`, `partial`, `failed`, or
   `verifier_failed` outcomes to business-specific recovery nodes.
2. Common runtime outcomes not matched above route to the shared unblock or
   repair nodes.
3. `stages[].repair_conditions` route a successful observation into repair when
   the output is structurally present but not acceptable for continued business
   progress.
4. `stages[].transitions` route a successful observation to another normal
   workflow node or the final node.
5. If no condition matches, the workflow follows the default linear happy path
   across `stage_kind: "main"` stages only. `stage_kind: "recovery"` stages
   return to `recovery_return_node` on success. Shared recovery helpers
   (`request_unblocking_input` and `repair_and_resume`) require
   `return_stage_id` on success and stay on the recovery node when that routing
   state is missing.

Use `transitions` for normal business branches. Use `repair_conditions` only
when the next action should be repair/unblock behavior. Do not declare the same
`output_key` + `operator` + `value` in both lists for the same stage; the creator
rejects that spec because repair conditions run first.

## Declarative Field Quick Reference

### `stages[].stage_kind`

Use this to separate happy-path stages from recovery-only stages:

- `main`: default. The stage participates in the generated linear happy path.
- `recovery`: the stage is generated as a normal node and prompt, but it is not
  part of the default happy path. It must be entered through an explicit route,
  usually `outcome_routes`, and must declare `recovery_return_node`.

### `stages[].outcome_routes`

Use this when a common runtime outcome should go to a business-specific node
instead of the shared fallback repair nodes. Fields:

- `outcome`: one of `blocked`, `partial`, `failed`, or `verifier_failed`.
- `next_node`: required target. It must be a declared stage, the final step, or a
  shared repair node.
- `branch_kind`: optional branch label for the generated `TransitionDecision`.
  Defaults to `repair` for `blocked` and `verifier_failed`, and `retry` for
  `partial` and `failed`.
- `reason`: transition reason written into trace output.

Only declare one route per outcome for a given stage. If no route is declared
for an outcome, generated policy uses the shared default route.

### `stages[].recovery_return_node`

Required for `stage_kind: "recovery"`. On a successful recovery observation,
generated policy returns to this node. Recovery stages default to retrying
themselves for `partial`, `failed`, or failed verifier results, and route
`blocked` to `request_unblocking_input`. This is separate from the shared
recovery-helper path, which depends on `return_stage_id` recorded in workflow
state.

### `shared_repair_helpers`

Optional top-level blueprint for the shared recovery helpers
`request_unblocking_input` and `repair_and_resume`. Use this when the workflow
needs source-of-truth helper prompts, helper output contracts, or helper
expected-artifact text instead of relying on generator defaults. Each helper
supports:

- `prompt`: action line for the helper prompt asset.
- `prompt_sections`: optional structured prompt sections using the same shape as
  workflow stages.
- `expected_artifact`: developer-facing node summary used by generated runtime
  metadata.
- `done_when`: helper completion checklist for generated `StepContract`.
- `output_schema`: helper success payload contract.
- `failure_schema`: optional helper failure payload contract; defaults to the
  workflow creator's standard blocked/error/missing-input shape.

### `stages[].repair_conditions`

Use this when a stage reports `status: "succeeded"` but its structured output
means the workflow should enter repair before progressing. Fields:

- `output_key`: key inside `observation.structured_output`.
- `operator`: one of `equals`, `not_equals`, `is_true`, `is_false`, `truthy`,
  `falsey`, `missing`, `non_empty`, or `empty`.
- `value`: comparison value for `equals` and `not_equals`; optional for boolean,
  emptiness, and missing checks.
- `reason`: transition reason written into trace output and repair context.
- `next_node`: optional; defaults to `repair_and_resume`.
- `branch_kind`: optional; defaults to `retry`.

### `stages[].transitions`

Use this for successful business branches that should stay in normal workflow
routing rather than entering repair. Fields:

- `output_key`, `operator`, and optional `value`: same condition shape as
  `repair_conditions`.
- `next_node`: required target. It must be a declared stage, the final step, or a
  shared repair node.
- `branch_kind`: required branch label for the generated `TransitionDecision`;
  use `continue`, `retry`, or `complete` consistently with the target.
- `reason`: transition reason written into trace output.

### `stages[].verifier_rules`

Use this for deterministic checks after schema validation. Fields:

- `output_key`: key inside `observation.structured_output`.
- `operator`: any repair-condition operator, plus `one_of` or `path_exists`.
- `value`: required for `one_of` as an allowed-values list; used as the expected
  value for `equals` and `not_equals`; ignored by `path_exists`.
- `message`: failure message returned by the generated verifier.

`path_exists` resolves relative paths against the verifier `repo_root`.

### `stages[].verifier_templates`

Use this for common complex checks that are too structured for one operator but
too common to require custom Python. Each template item must include:

- `id`: stable Python-identifier-style rule ID for review and tests.
- `template`: one of the supported template names below.
- `output_key`: key inside `observation.structured_output`.
- `message`: failure message returned by the generated verifier.

Supported templates:

- `conditional_equals`: when `when.output_key` satisfies `when.operator` and
  optional `when.value`, `output_key` must equal `expected_value`.
- `conditional_required`: when `when.output_key` satisfies `when.operator` and
  optional `when.value`, `required_key` must be present and truthy.
- `min_count`: `output_key` must be a list with length at least `min_count`.
- `artifact_file_contains_sections`: `output_key` must be a file path whose text
  contains every string in `sections`. Relative paths resolve against
  `repo_root`.

Use `verifier_templates` before introducing custom verifier code when the
template DSL expresses the invariant cleanly.

### `stages[].custom_verifier_requirements`

Use this when the acceptance contract matters, but it cannot be expressed
cleanly through `verifier_rules` or `verifier_templates`. Each item must
describe the invariant clearly enough that the authoring pass can generate
requirement-scoped `verifiers.py` logic or scaffolds and matching regression
tests before review. Each item includes:

- `id`: stable Python-identifier-style rule ID for review, code, and tests.
- `description`: the invariant the verifier must enforce.
- `signals`: optional list of relevant output keys, paths, state fields, or
  artifacts the custom verifier should inspect.
- `implementation_surface`: optional list of authoring surfaces to touch, such
  as `verifier`, `policy`, `state`, or `tests`. This is a hand-written code
  hint, not an execution surface declaration.
- `implementation_notes`: optional extra guidance for the authoring agent or
  reviewer, such as edge cases, helper functions to reuse, or why the DSL was
  insufficient.
- `hint_pseudocode`: optional ordered pseudocode steps for the human author who
  will finish the generated scaffolds or companion workflow files. The creator
  preserves this verbatim; it does not execute or compile it.
- `test_intent`: optional list of behaviors that workflow-specific tests should
  cover when this requirement is implemented.

The generator validates these requirements, preserves them in normalized
`spec.json` and the generated `agent-review.md`, and emits requirement-scoped
custom verifier scaffolds in `verifiers.py` that the authoring pass should
complete before review sign-off. `implementation_surface`, `hint_pseudocode`,
and `test_intent` are carried into generated scaffolds and review docs as
authoring aids for hand-written code; they are not interpreted as deterministic
codegen instructions.

### `regression_tests`

Use this to generate
`workflow-runtime/workflows/<workflow_id>/tests/test_workflow.py`. Supported
types:

- `transition`: provide `name`, `current_step_id`, `observation`,
  `expected_next_node`, and optional `expected_branch_kind`, `state`, and
  `verifier_result`.
- `verifier`: provide `name`, `step_id`, `observation`, and `expected_passed`;
  optional `state` is supported when verifier semantics depend on previously
  promoted workflow state.

In addition to workflow-specific declared tests, generated workflow tests should
preserve host-visible observability for the shared repair helpers. At minimum,
the generated suite should make it easy to verify:

- normal `yield` without `retry_context`
- blocked recovery that surfaces `retry_context.category == "blocked"`
- verifier-driven retry that surfaces
  `retry_context.category == "verifier_failed"`

## Validation Boundary

`create_workflow.py` validates scaffold and spec concerns:

- `workflow_id` is a Python-package-safe identifier matching
  `[A-Za-z_][A-Za-z0-9_]*`
- the runtime skill root exists
- `workflow_skeleton` exists
- existing workflow directories or binding entries are rejected unless
  `--force` is present
- `workflow-binding.json.workflows` is a list
- spec stages have import-safe `step_id` values
- each stage has prompt text, `done_when`, `output_schema`, and `failure_schema`
- `start_input_schema` contains `task_input`, `context`, and `constraints`
- `dependencies` entries have `id`, supported `type`, boolean `required`,
  supported `scope`, `source`, and `purpose`; `cli` dependencies must include
  `command`, and `python_package` dependencies must include `module`
- `installed` entries have `id`, `type`, `scope`, `source`, `recorded_at`, and
  `recorded_by`; missing recorder metadata is filled by the creator
- `source` means the installation or provenance source, such as a package name,
  repository URL, marketplace/catalog ID, or MCP server name. Do not put local
  resolved paths such as `.codex/skills/foo/SKILL.md`, `/abs/path`, or
  `~/.agents/skills/foo` in `source`; preflight reports resolved local paths in
  dependency result `location` instead.
- Declare dependencies at the installable top-level skill boundary. Package-
  internal child skills must not become separate workflow dependencies. When a
  stage needs a child capability, route through the parent skill and describe the
  operation in `stages[].skill_routing.operations`. The creator treats
  `source: skill-catalog:<parent>/<child>` as a package-internal child skill
  reference: matching child dependency IDs, installed entries, and stage routes
  are normalized to `<parent>`.
- `stages[].skill_routing` entries preserve `skill`, `operations`,
  `file_patterns`, and `usage_notes` for generated `SkillRoute` constants
- `stages[].prompt` becomes the first line of the generated prompt asset. Use it
  to describe the stage goal, primary skill owner, execution object or artifact,
  and minimum workflow inputs. Do not use it to teach the invoked skill its own
  checklist; detailed skill procedure belongs in the skill body, not in the
  workflow prompt.
- `stages[].prompt_sections` drives generated prompt assets with stage goal,
  context, boundaries, and blocked conditions. Put stage intent and short
  execution handles in `prompt`; do not declare a separate `tasks` field under
  `prompt_sections`. Keep `context` for background, summaries, long JSON, and
  auxiliary evidence. Keep `boundaries` workflow-specific: record scope guards,
  ownership limits, and cross-stage handoff rules, but do not copy the routed
  skill's internal SOP unless the workflow is imposing an extra constraint
  beyond that skill.
- `stages[].state_updates` promotes structured output keys into named workflow
  state fields; generated template context exposes those names to later prompts
  and prefers promoted state over start input when both expose the same
  placeholder key
- `stages[].stage_kind` is either `main` or `recovery`; recovery stages must
  declare a valid `recovery_return_node`
- `stages[].outcome_routes` expresses stage-specific routes for `blocked`,
  `partial`, `failed`, and `verifier_failed` before shared repair fallback
- `stages[].repair_conditions` expresses simple output-based gates that route to
  repair before the linear happy path continues
- `stages[].transitions` expresses simple output-based success branches before
  the default linear happy path continues
- `stages[].verifier_rules` adds deterministic checks such as enum membership,
  path existence, and non-empty output enforcement after schema checks
- `stages[].verifier_templates` adds whitelistable static verifier code for
  common complex checks such as list item keys, conditional required fields,
  uniqueness, minimum counts, and artifact section checks
- `stages[].custom_verifier_requirements` preserves complex verifier intent and
  generates requirement-scoped custom verifier scaffolds in `verifiers.py`; the
  generator validates the declaration shape and wires those helpers into stage
  verifier execution
- `shared_repair_helpers` lets workflows override the shared helper prompts,
  expected-artifact metadata, and helper `StepContract` schemas in a
  source-of-truth way instead of depending on hard-coded defaults
- `regression_tests` generates workflow-specific transition and verifier tests
  under `workflow-runtime/workflows/<workflow_id>/tests/test_workflow.py`; the
  generator also appends default structural tests for shared recovery-helper
  resume behavior, host-visible blocked retry summaries, and prompt-context
  precedence when applicable

It intentionally does not validate:

- whether the workflow can satisfy a future user task
- complex non-linear branch correctness beyond declared outcome routes and
  transitions
- business-specific verifier semantics that are not declared as deterministic
  `verifier_rules` or whitelistable `verifier_templates`
- whether declared `custom_verifier_requirements` are sufficiently specific or
  whether the generated custom verifier scaffolds have been fully tightened into
  workflow-correct verifier logic after generation
- whether the declared outcome, repair, transition, or recovery return target is
  the best business return point for a failed workflow

Those checks belong to authoring review and regression tests.

## Post-Generation Agent Review

The generated scaffold is intentionally split into two ownership layers:

- `create_workflow.py` owns deterministic generation: import-safe files, declared
  stage contracts, main-stage happy-path routing, declared outcome routes,
  recovery-stage return routing, prompt assets, manifest metadata, and the
  binding entry.
- The authoring agent owns spec-first semantic review: workflow boundary, stage
  responsibilities, prompt intent, output semantics, state promotion, business
  outcome routing, repair routing, recovery return points, transitions, verifier
  rules, verifier templates, final gates, and regression tests should be correct
  in `spec.json` before generated files are treated as evidence.

Every generated workflow includes:

```text
workflow-runtime/workflows/<workflow_id>/references/agent-review.md
```

Run one subagent-backed review pass from that checklist before calling the
workflow shipped. Before spawning the review subagents, explicitly ask the user
for authorization and wait for consent. That authorization gate is required:
if consent is missing or denied, stop and report the workflow as blocked rather
than replacing the review with a single-thread pass. Once authorized, use
multiple review subagents to inspect the spec, generated code, or tests from
different angles. Typical angles include prompt review (`prompts/*.md`),
verifier review (`verifiers.py` and verifier declarations), contract review
(`contract.py` and output schemas), and graph/runtime-flow review
(`graphbuilder_runtime.py`, `policy.py`, and `references/flowchart.md`).
Start by reading `spec.json`; generated Python, prompt, flowchart, manifest,
and test files should then be checked for faithful implementation of that blueprint.
This catches the known generator limits: undeclared domain semantics, ambiguous
repair return points, and missing state carry-forward for fields that only
become important in later prompts.

Keep generated-workflow tests separate from core runtime tests. Add them under
`workflow-runtime/workflows/<workflow_id>/tests/test_workflow.py` so workflow
policy, prompt, verifier, and happy-path checks stay beside their workflow and
do not mix with bridge/runtime/pack/register/inject tests.

Every generated workflow also keeps a normalized copy of the generation spec at
`workflow-runtime/workflows/<workflow_id>/spec.json`. Treat this as the workflow
blueprint for future changes: update it when stage order, prompts, outputs,
dependencies, state promotion, or repair gates change, then regenerate or apply
matching code edits.

## Generated Files

The script creates:

```text
durable-workflow-runtime/
├── workflow-binding.json
├── workflow-shortcuts/
│   └── <workflow_id>/
│       └── SKILL.md
├── workflow-runtime/workflows/
│   └── <workflow_id>/
│       ├── __init__.py
│       ├── contract.py
│       ├── graphbuilder_runtime.py
│       ├── manifest.json
│       ├── policy.py
│       ├── spec.json
│       ├── state.py
│       ├── verifiers.py
│       ├── references/
│       │   ├── agent-review.md
│       │   └── flowchart.md
│       ├── prompts/
│       └── tests/
│           └── test_workflow.py   # only when regression_tests are declared
```

Once `spec.json` is filled in and the creator is rerun with `--force`,
generated files are business-specific to the declared stages. The generator
owns declared transitions, declared verifier rules, declared verifier
templates, declared custom verifier scaffolds, and declared regression tests.
It preserves declared `custom_verifier_requirements` for the review pass and
emits requirement-scoped helpers in `verifiers.py`, but the author still owns
tightening any branch, verifier, or regression coverage that cannot be
expressed in the JSON spec. `spec.json` is the normalized workflow-local
blueprint after defaults and validation have been applied, so it may include
generated defaults that were omitted from the hand-edited file.

When reviewing generated runtime behavior, check both layers:

- persisted repair state under `state.py` / runtime state serialization
- transport-facing `yield` responses that expose compact `retry_context`

If a generated workflow records verifier failure only in persisted state but not
in `response.json`, treat that as an observability bug in the generated runtime
surface rather than acceptable host behavior.

## Success Output

On success, `create_workflow.py` prints a JSON object:

```json
{
  "kind": "workflow_scaffold",
  "workflow_id": "pdf_processing",
  "workflow_dir": "/abs/path/workflow-runtime/workflows/pdf_processing",
  "binding_file": "/abs/path/workflow-binding.json",
  "shortcut_skill_name": "workflow:pdf_processing",
  "shortcut_skill_dir": "/abs/path/workflow-shortcuts/pdf_processing",
  "shortcut_skill_file": "/abs/path/workflow-shortcuts/pdf_processing/SKILL.md",
  "spec_blueprint_file": "/abs/path/workflow-runtime/workflows/pdf_processing/spec.json",
  "agent_review_required": true,
  "agent_review_file": "/abs/path/workflow-runtime/workflows/pdf_processing/references/agent-review.md",
  "regression_tests_file": "/abs/path/workflow-runtime/workflows/pdf_processing/tests/test_workflow.py",
  "next_actions": [
    "Use spec.json as the workflow blueprint before making future workflow changes.",
    "Edit workflow-runtime/workflows/pdf_processing/spec.json, then rerun create_workflow.py with --workflow-id pdf_processing --force to regenerate workflow files.",
    "Translate any generated custom verifier scaffolds and domain-specific routing needs into concrete workflow code before review sign-off.",
    "Run the required subagent-backed agent review using references/agent-review.md before treating the workflow as shipped.",
    "Tighten generated verifiers, business repair routing, state promotion, and tests based on that review."
  ],
  "replaced_existing": false,
  "created_files": 13
}
```

On failure, it prints a human-readable error to stderr and exits non-zero.
