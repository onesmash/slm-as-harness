# Workflow Authoring Guide

Read this file when you want to add a new workflow under
`<skill-root>/workflow-runtime/workflows/` and make it startable through the
bundled bridge/runtime.

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`. In this repo, `<skill-root>` currently resolves
to `.codex/skills/durable-workflow-runtime/`.

## What "adding a workflow" means here

In this skill, a workflow is not just a new prompt file.

A shipped workflow must be able to do all of these:

- be selected by a stable `workflow_id`
- validate start-time input with its own `WORKFLOW_INPUT_CONTRACT`
- emit yielded steps with `StepContract`
- accept `Observation` on `resume`
- let runtime, not the host agent, decide branch / retry / blocked / terminal transitions
- end through an explicit final node that becomes `DoneResponse.final_prompt_envelope`

If any one of those is missing, the workflow is only half integrated.

## Required files

Current runtime loading expects these importable modules:

```text
<skill-root>/workflow-runtime/workflows/<workflow_id>/
├── __init__.py
├── contract.py
├── graphbuilder_runtime.py
├── policy.py
├── spec.json
├── state.py
├── verifiers.py
├── references/
│   └── flowchart.md
└── prompts/
    └── *.md
```

Why each file exists:

- `contract.py`
  Publishes `WORKFLOW_INPUT_CONTRACT` and yielded-step `StepContract`.
- `state.py`
  Owns workflow-local persisted state and repair bookkeeping.
- `policy.py`
  Owns transition decisions after each observation.
- `spec.json`
  Stores the normalized workflow blueprint used to generate or revise this
  workflow. Read it before changing stages, prompts, outputs, dependencies,
  state promotion, or repair gates, and keep it aligned with those edits.
- `graphbuilder_runtime.py`
  Owns start preview, transition preview, node definitions, prompt asset
  mapping, and final-node metadata used by `engine_graphbuilder.py`.
- `verifiers.py`
  Owns deterministic acceptance checks when host reporting is not enough.
- `prompts/*.md`
  Own the real step prompt bodies. Do not move these into `SKILL.md`.
- `references/flowchart.md`
  Documents the workflow's global Mermaid flowchart for developers. Keep it
  aligned with `policy.py` and `graphbuilder_runtime.py`, but prefer the happy
  path plus major business gates over drawing every common failure edge.

`verifiers.py` can stay small, but keep the module present if step contracts
reference it.

## Starter scaffold

You do not need to start from a blank directory.

There is now a copyable starter here:

```text
<skill-root>/workflow-runtime/templates/workflow_skeleton/
```

Recommended usage:

1. Copy the skeleton into `workflow-runtime/workflows/<your_workflow_id>/`.
2. Replace `example_workflow` and the placeholder step IDs.
3. Rewrite prompts, contracts, state, and policy around your real workflow.
4. Create or update `spec.json` so it captures the workflow blueprint.
5. Update `references/flowchart.md` to show the real workflow's global shape.
6. Register the workflow in `workflow-binding.json`.
7. Add regression tests before treating it as shipped.

## End-to-end checklist

Author a new workflow in this order:

1. Pick the workflow boundary and `workflow_id`.
2. Add the workflow directory, required modules, and `spec.json` blueprint.
3. Define `WORKFLOW_INPUT_CONTRACT`.
4. Define yielded-step contracts.
5. Define workflow state and repair state.
6. Define transition policy.
7. Define node metadata, including an explicit final node.
8. Define GraphBuilder start and transition previews.
9. Write prompt assets.
10. Update `references/flowchart.md` from the final `policy.py` transitions,
    keeping repetitive repair edges in notes unless they change the global path.
11. Re-check `spec.json` against the final prompts, contracts, policy, manifest,
    and flowchart before treating it as the workflow's future edit blueprint.
12. Register the workflow in `workflow-binding.json`.
13. Add regression tests.
14. Update wrapper-level references if the public wrapper story changed.

Following this order helps keep the host/runtime/workflow boundaries separate.

## 1. Choose the workflow boundary first

A good workflow boundary is:

- specific enough that one `flow_description` can explain when to use it
- broad enough that the runtime, not chat history, owns the whole loop
- stable enough that downstream tests can assert exact step IDs and branch semantics

Use a stable `workflow_id`; new workflows use hyphen-separated (kebab-case)
ids, for example:

```text
superpowers-delivery-chain
```

The on-disk package under `workflow-runtime/workflows/<module_name>/` uses the
derived underscore form (`superpowers_delivery_chain`) because Python module
names cannot contain hyphens; the runtime derives it from the workflow_id
automatically, so keep the two in sync when authoring by hand.

Avoid IDs that encode temporary experiments or prompt wording.

## 2. Register the workflow in the catalog

Add the new workflow to:

```text
<skill-root>/workflow-binding.json
```

Minimum shape:

```json
{
  "workflow_id": "your-workflow-id",
  "flow_description": "一句话说明这个 workflow 适合什么任务，以及它和相邻 workflow 的边界。",
  "start_input_schema": {
    "task_input": {},
    "context": {},
    "constraints": {}
  }
}
```

Important boundary:

- `flow_description` is selector metadata for humans and agents
- `start_input_schema` is the catalog-published copy of
  `WORKFLOW_INPUT_CONTRACT.to_start_input_schema()`
- runtime does not semantically route from `flow_description`
- explicit `workflow_id` selection only works when both are true:
  - the ID appears in `workflow-binding.json`
  - the modules are loadable from `workflow-runtime/workflows/<workflow_id>/`

Do not rely on directory existence alone.

The adapter backfills a missing `start_input_schema` from the workflow contract
when a workflow is selected, and rejects an existing value that does not match
the contract. Keep the static catalog updated anyway so hosts can inspect the
workflow start contract before calling `start`.

## 3. Define `WORKFLOW_INPUT_CONTRACT`

In `contract.py`, publish one workflow-scoped input contract:

```python
WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={...},
    context_schema={...},
    constraints_schema={...},
)
```

Publish the same shape through manifest and binding metadata as:

```json
{
  "start_input_schema": {
    "task_input": {},
    "context": {},
    "constraints": {}
  }
}
```

Use it for start-time data only:

- `task_input_schema`
  Business input the workflow needs from the user request.
- `context_schema`
  Environment context such as repo paths that the workflow truly depends on.
- `constraints_schema`
  Explicit knobs such as `max_steps` or a permission flag.

Keep it narrow. Do not stuff yielded-step outputs into the workflow input
contract.

## 4. Define yielded-step contracts

Every yielded step must have a `StepContract` in `contract.py` and be reachable
via:

```python
def get_step_contract(step_id: str) -> StepContract: ...
```

Each contract should answer:

- what observable completion conditions the host should satisfy
- what machine-readable success payload the workflow needs later
- what failure payload repair logic needs
- whether a deterministic verifier should run

Current pattern:

```python
STEP_NAME = StepContract(
    done_when=[...],
    output_schema={...},
    failure_schema={...},
    verifier=StepVerifier(...),
)
```

Rules worth keeping:

- `done_when` should be host-facing and observable.
- `output_schema` should include only fields later state/policy/verifiers need.
- `failure_schema` should include only retry / repair / escalation facts.
- final terminal prompts do not need a `StepContract`; only yielded steps do.

## 5. Separate main stages, repair stages, and final stage

Model three kinds of nodes explicitly.

### Main stages

These are the normal business stages of the workflow. They usually:

- emit a yielded prompt
- accept `Observation`
- either continue forward or fall into repair

### Repair stages

These handle blocked / partial / failed / verifier-failed outcomes.

Typical examples:

- `request_unblocking_input`
- `repair_and_resume`

Rules:

- repair prompts may explain what to fix, but they do not choose the next node
- routing back to the original stage belongs in runtime policy via `return_stage_id`
- normal blocked handling should enter `repair_and_resume` first; let shared repair decide whether external unblock input is actually required
- shared repair should attempt self-repair three times before policy is allowed to escalate to `request_unblocking_input`
- when `repair_and_resume` escalates to `request_unblocking_input`, a successful unblock returns to `repair_and_resume` first so repair can own the retry decision
- if repair itself becomes blocked, it should still route through policy, not host improvisation
- if `return_stage_id` is missing when a shared recovery helper succeeds, keep
  the workflow on the recovery node and fix state bookkeeping instead of
  silently falling back to the first main stage

### Final stage

Keep an explicit final node such as `finalize_summary`.

Current runtime behavior is:

- `resume` computes the next step
- if the next step is the final node, runtime returns `kind = "done"`
- `DoneResponse.final_prompt_envelope` is built from final-node metadata
- after that, `resume` is no longer allowed for the run

Do not skip the explicit final node and jump straight from a yielded step to a
terminal state.

## 6. Design workflow state around routing, not transcript replay

In `state.py`, define a dataclass for durable workflow facts.

Keep three kinds of state separate:

- stage progress
  - current stage
  - completed stages
  - attempt counts
- durable artifacts
  - spec path
  - plan path
  - verification evidence
- repair bookkeeping
  - `return_stage_id`
  - `repair_context`
  - source-stage failure facts

Recommended workflow-local functions:

```python
def make_initial_state(request: dict) -> WorkflowState: ...
def serialize_state(state: WorkflowState) -> dict: ...
def deserialize_state(payload: dict | None) -> WorkflowState: ...
def record_observation(...): ...
def determine_return_stage_id(...): ...
def determine_repair_reason(...): ...
def apply_transition(...): ...
```

Two important patterns from `superpowers_delivery_chain`:

- `record_observation(...)` stores durable artifacts and prepares repair state.
- `apply_transition(...)` clears `return_stage_id` and `repair_context` only
  after repair successfully hands control back.
- when a prompt placeholder key exists in both start input and promoted state,
  later prompt rendering should prefer the promoted state value.

That keeps repair flow resumable across process restarts.

## 7. Put transition ownership in `policy.py`

`policy.py` should turn one observation plus optional verifier result into one
`TransitionDecision`.

Recommended structure:

- one top-level `choose_next_node(...)`
- one shared helper for common failure routing
- small special cases for business-specific branching

Current good pattern:

- `blocked` -> repair node requesting external help
- `partial` -> retry node
- `failed` -> retry node
- verifier failed -> retry node
- business-specific soft failure
  - review says `changes_requested`
  - verification says `verification_passed == False`
  -> retry node with `return_stage_id = execute_implementation`

Keep the host agent out of this logic. The host reports what happened; the
workflow policy decides what that means next.

## 8. Define node metadata in `graphbuilder_runtime.py`

`graphbuilder_runtime.py` is the workflow's node catalog in the current
runtime.

Current implementation benefits from:

- one `NodeDefinition` dataclass
- one concrete `PromptStepNode` base for yielded-step nodes
- one explicit final node subclass
- a `NODE_DEFINITIONS` mapping keyed by stable node ID

At minimum, each node definition should tell runtime:

- `step_id`
- prompt asset path
- intent
- expected artifact
- resume instructions
- whether the node is final

Keep these helper functions available on the prototype module:

```python
def build_graph() -> Graph: ...
def get_node_definition(node_key: str) -> NodeDefinition: ...
def load_prompt_body(node_key: str, template_context: dict | None = None) -> str: ...
```

If your prompts need state-derived interpolation, also expose:

```python
def build_template_context(*, step_id: str, run_state) -> dict: ...
```

`engine_graphbuilder.py` will use those helpers when emitting both yielded
prompts and the final prompt.

Important boundary:

- there is no global placeholder catalog
- start prompts only see the keys you explicitly pass in `build_prompt_envelope(..., template_context=...)`
- resume/final prompts only see the keys returned by `build_template_context(...)`
- missing keys fail prompt rendering immediately

Before editing prompt Markdown, read:

- `prompt-asset-template.md`
- `prompt-placeholder-spec.md`

Those files are the current references for:

- the standard prompt asset shape
- which content belongs in prompt assets vs `StepContract`
- supported `{{placeholder}}` syntax
- where values come from
- which keys the shipped skeleton currently exposes
- common authoring mistakes that lead to missing-template-key failures

## 9. `graphbuilder_runtime.py` is part of the runtime contract

The current engine imports:

- `workflows.<workflow_id>.graphbuilder_runtime`

So this file is not optional in the current architecture.

It should provide two preview paths:

- start preview
  - produce the first yielded step
- transition preview
  - apply state update
  - call workflow policy
  - return the next `step_id`

Current engine expectations are easiest to satisfy if you expose:

```python
def run_start_preview(...): ...
def run_transition_preview(...): ...
```

And ensure the transition preview result includes:

- `step_id`
- branch metadata for history
- `state_payload`

`state_payload` matters because `engine_graphbuilder.py` persists it back into
`RunState.graph_state` after each resume.

## 10. Keep prompts in `prompts/*.md`

Real prompt bodies live under:

```text
workflow-runtime/workflows/<workflow_id>/prompts/
```

Guidelines:

- one file per node
- follow `prompt-asset-template.md` unless the node has a clear reason to use a
  shorter shape
- prompt should match the contract and expected artifact exactly
- when a stage has routed skills, require one clear primary skill owner and use
  a slash-skill action line such as `/brainstorming {{workflow_goal}}` for that
  owner. Additional routed skills are supporting-only. If you cannot name a
  single primary owner, split or redefine the stage instead of writing a
  combined action sentence
- prompt assets should describe task semantics, stage boundaries, and blocked
  conditions; do not duplicate `output_schema` or `failure_schema`
- `Stage Boundaries` should capture workflow-owned limits such as scope,
  handoff, or approval gates. Do not restate the invoked skill's internal SOP
  unless the workflow adds a stricter rule that is specific to this stage.
- repair prompts should explain how to recover, not how to route
- final prompt should produce the final user-facing summary only once
- prompt placeholders must be traceable to either:
  - start-time explicit `template_context`
  - `build_template_context(...)`

Do not treat `SKILL.md` as the source of truth for step prompts.

## 11. Add verifiers only where they buy determinism

Use `verifiers.py` when success can be checked objectively:

- a path must exist
- an enum value must be one of an allowed set
- a list must be non-empty
- a reported artifact must match filesystem reality

Keep verifiers narrow and deterministic. They should validate acceptance, not
re-run the whole task mentally.

When a workflow has important acceptance logic that the built-in declarative
verifier DSL cannot express cleanly, record that requirement explicitly in the
spec as `custom_verifier_requirements`. The generated workflow will preserve
that declaration for review, and the agent-review pass should then add the
hand-written `verifiers.py` code and matching tests needed to enforce it. Keep
each generated requirement-scoped verifier self-contained when practical. If
it needs reusable logic, move that logic into a stable shared module and
import it into `verifiers.py`; do not add extra same-file helper functions and
call them from the preserved requirement function.

If a verifier fails:

- the protocol is still intact
- the workflow policy should receive `verifier_result`
- routing can move into retry / repair without pretending the host broke the contract

Two common spec patterns are worth writing explicitly:

- when a boolean readiness field enables a downstream target or artifact,
  declare that coupling with `verifier_templates` such as
  `conditional_required`
- when a downstream stage must prove it is still acting on the same target or
  artifact prepared earlier, declare that invariant in
  `custom_verifier_requirements` and add matching regression coverage

## 12. Test the full lifecycle

When adding a workflow, extend:

```text
<skill-root>/tests/test_durable_workflow_runtime.py
```

Minimum regression checklist:

- explicit `workflow_id` start selects the new workflow
- unpublished `workflow_id` is rejected even if a directory exists
- start-time input contract is enforced
- the first `start` yield matches the workflow's first stage
- success routing reaches the expected next stage
- blocked / partial / failed routing reaches repair stages
- verifier failure triggers retry / repair as designed
- repair success returns to `return_stage_id`
- shared recovery helpers do not silently fallback when `return_stage_id` is missing
- final main-stage success returns `kind = "done"` with the final node
- `done` after `resume` forbids another `resume`
- cross-instance resume still works from persisted run state
- bridge reports invalid workflow selection as `kind = "error"`
- existing workflows still pass without regression

For generated per-workflow regression tests, make sure the spec covers:

- the final happy-path tail through the last main stage into the final node
- any business gate that should block or repair before final completion
- prompt-context precedence when a start-input key and promoted state key share
  the same placeholder name

Run:

```bash
python3 -m unittest discover -s <skill-root>/tests
```

If you changed public wrapper behavior, add or update reference docs too.

## 13. Update public references when the wrapper story changed

If the new workflow affects how people discover or select workflows, update the
relevant spokes:

- `references/index.md`
- `references/workflow-selection-spec.md`
- `references/runtime-layout.md`
- `SKILL.md`

Good rule of thumb:

- if a caller now has a new valid `workflow_id` choice, update selection docs
- if the runtime now expects a new module or boundary, update layout docs
- if the skill should now trigger for a broader set of workflow tasks, update
  `SKILL.md`

## Quick checklist

Before calling the workflow "done", confirm all of these are true:

- the workflow is listed in `workflow-binding.json`
- `skill_host.start(..., workflow_id=...)` can load it
- `contract.py`, `policy.py`, `state.py`, and `graphbuilder_runtime.py` all
  import cleanly
- every yielded step has a `StepContract`
- repair routing never depends on host free-form judgment
- the workflow ends through an explicit final node
- tests cover `start`, `resume`, repair, terminal, and bridge error paths

If one of those is false, the workflow is not fully integrated yet.
