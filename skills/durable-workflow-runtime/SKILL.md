---
name: durable-workflow-runtime
description: |
  Load when the user explicitly asks for `durable-workflow-runtime`, or when
  implementing or debugging this skill's bundled durable workflow wrapper with
  `start/resume`, workflow branching, retries, blocked handling, bridge
  payloads, or explicit workflow selection.
---

# Durable Workflow Runtime

This skill is an explicit entrypoint into the bundled runtime. Once it is
invoked, treat that as the decision to use the runtime contract instead of
re-evaluating applicability inside the conversation.

## Invocation contract

- If this skill is loaded, operate through the shipped runtime and bridge
  contract.
- The remaining selection is which published `workflow_id` to start, not
  whether the skill should keep governing the task.
- Keep workflow choice explicit when possible; otherwise rely on the configured
  default binding.

## Primary contract

If you review only one thing in this skill, review this loop:

```text
start -> yield -> host executes prompt -> Observation -> resume -> ... -> done
```

This loop is the product. Everything else in this skill exists to protect this
handoff from drifting into free-form chat behavior.

Ownership in that loop:

- `start`
  the host calls `bridge.py start`
- `yield`
  the runtime returns a `response.json` that asks the host to execute one step
- `Observation`
  the host's only valid structured reply after a yielded step
- `resume`
  the host sends that `Observation` back through `bridge.py resume`
- `done`
  the runtime, not the host, decides the workflow is terminal

Do not blur these two namespaces:

- `response.kind`
  runtime-to-host control signal: `yield | done | error`
- `Observation.status`
  host-to-runtime execution result: `succeeded | failed | blocked | partial`

They are not interchangeable. The host never emits `done`; the runtime never
emits `succeeded`.

## Default reading boundary

- Stay on the public wrapper surface first:
  `workflow-binding.json`, `scripts/bridge.py`, `references/bridge-cli-spec.md`,
  `references/host-loop.md`, and `references/observation-format.md`.
- Do not inspect workflow internals such as `contract.py`, `policy.py`,
  `state.py`, `verifiers.py`, `graphbuilder_runtime.py`, or workflow prompt
  assets unless the task is explicitly about authoring or debugging those
  internals.
- Treat verifier logic as runtime-owned implementation detail by default. The
  host agent normally does not need to read it to execute or resume a workflow
  correctly.

## Keep the layers separate

- `runtime`: owns state, pause/resume, branch selection, and terminal states
- `workflow`: owns internal step contracts, prompts, policy, and verifier logic
- `skill wrapper`: only routes into the skill-local bridge/runtime
- `host agent`: only executes the current prompt and returns an observation

If these blur together, the host agent will start improvising branch decisions
and step semantics in chat, which defeats the whole point of the runtime.

## First moves

1. Treat the skill invocation itself as the decision to use the bundled
   runtime.
2. Check whether this skill bundle already has `scripts/bridge.py`,
   `workflow-binding.json`, and the wrapper entry. If you need the concrete
   install path for the current environment, read `references/index.md`
   instead of assuming a Codex-specific directory layout.
3. Read `references/index.md`, then start with interface-level spokes only.
4. If the bridge or bundled runtime does not exist yet, say so explicitly and
   switch to design or implementation guidance instead of pretending the loop
   can already run.
5. If the caller needs to choose a workflow, use the published wrapper catalog
   in `workflow-binding.json` and read
   `references/workflow-selection-spec.md` for the exact selection contract.
6. For normal execution, use the inlined `start/resume` loop below. The
   reference docs are for examples and edge cases, not for the core path.

## Core execution loop

This is the minimum contract the host agent should follow without leaving this
file.

### 1. Allocate host I/O paths

Before writing any request, response, observation, or artifact file, allocate
the path through `scripts/host_io.py`. This is part of the execution contract,
not a cleanup preference.

For the first `start`, use the pending layout because no `run_id` exists yet:

```bash
python <skill-root>/scripts/host_io.py pending-start \
  --repo-root <repo-root> \
  --workflow-id <workflow-id-optional>
```

Write the start request to the returned path, and put the initial response file
in that same `host-io/pending/` directory. After the runtime returns a `run_id`,
use `host_io.py ensure-run`, `response-path`, and `observation-path` for all
run-scoped files.

Do not put bridge payload files in the repository root or arbitrary `/tmp`
paths. `bridge.py` rejects normal `start`, `preflight`, and `resume` payloads
outside `<repo-root>/.durable-workflow-runtime/host-io/`; the escape hatch
`--allow-unsafe-host-io-paths` is only for explicit transport debugging.

### 2. Build the `start` request

Write a JSON object with exactly these top-level fields:

```json
{
  "task_input": {},
  "context": {},
  "constraints": {}
}
```

If the caller already knows the intended workflow, treat `workflow_id` as a
separate start-time selector. It is not part of
`task_input/context/constraints`.

### 3. Call `bridge.py start`

```bash
python <skill-root>/scripts/bridge.py start \
  --repo-root <repo-root> \
  --request-file <start-request.json> \
  --response-file <response.json> \
  --workflow-id <workflow-id-optional>
```

Workflow selection rule:

- caller supplied `workflow_id`
  pass `--workflow-id <workflow_id>`
- caller omitted `workflow_id`
  omit `--workflow-id` and let the adapter fall back to
  `workflow-binding.json.default_workflow_id`

Start failure rule:

- if a supplied `workflow_id` is not published in
  `workflow-binding.json.workflows[]`, treat `start` as failed
- if a supplied `workflow_id` is published but not loadable as a runtime
  workflow module, treat `start` as failed
- do not silently fall back to `default_workflow_id` when the caller supplied
  an explicit but invalid `workflow_id`

### 4. Parse `response.json`

Do not parse the response by vibes or by looking only at prose fields. Parse it
in this order:

1. load the file as a JSON object
2. read `kind`
3. branch strictly on `kind`
4. then read the envelope fields required by that branch

Minimal parser shape:

```python
response = load_json(response_file)
kind = response["kind"]

if kind == "yield":
    envelope = response["prompt_envelope"]
elif kind == "done":
    envelope = response["final_prompt_envelope"]
elif kind == "error":
    raise BridgeRuntimeFailure(response["error_type"], response["message"])
else:
    raise ProtocolFailure(f"unknown response kind: {kind}")

if kind in {"yield", "done"}:
    if response["run_id"] != envelope["run_id"]:
        raise ProtocolFailure("top-level run_id must match envelope.run_id")
    if response["step_id"] != envelope["step_id"]:
        raise ProtocolFailure("top-level step_id must match envelope.step_id")
```

Do not use `intent`, `metadata.workflow_id`, or prompt text itself to decide
which control-flow branch to take. Control flow is determined only by `kind`.

#### `yield` response

Read these fields first:

- `response.kind`
- `response.run_id`
- `response.step_id`
- `response.prompt_envelope`
- `response.prompt_envelope.prompt`

Then treat these envelope fields as execution contract fields, not hints:

- `done_when`
- `output_schema`
- `failure_schema`
- `resume_instructions`

Identity invariants:

- `response.run_id == response.prompt_envelope.run_id`
- `response.step_id == response.prompt_envelope.step_id`
- the host must preserve that exact `(run_id, step_id)` pair into the next
  `Observation`

Reference shape:

```json
{
  "kind": "yield",
  "run_id": "run_123",
  "step_id": "collect_context",
  "prompt_envelope": {
    "run_id": "run_123",
    "step_id": "collect_context",
    "prompt": "...",
    "intent": "collect_context",
    "expected_artifact": "runtime scaffold status",
    "done_when": ["..."],
    "output_schema": {},
    "failure_schema": {},
    "resume_instructions": "...",
    "metadata": {
      "workflow_id": "demo_prompt_loop",
      "workflow_version": "v1"
    }
  }
}
```

Handling rule:

- execute `prompt_envelope.prompt`
- build an `Observation`
- call `resume`
- do not invent or rewrite `run_id`
- do not invent or rewrite `step_id`

#### `done` response

Read these fields first:

- `response.kind`
- `response.run_id`
- `response.step_id`
- `response.final_prompt_envelope`
- `response.final_prompt_envelope.prompt`

Identity invariants:

- `response.run_id == response.final_prompt_envelope.run_id`
- `response.step_id == response.final_prompt_envelope.step_id`

Reference shape:

```json
{
  "kind": "done",
  "run_id": "run_123",
  "step_id": "finalize_summary",
  "final_prompt_envelope": {
    "run_id": "run_123",
    "step_id": "finalize_summary",
    "prompt": "...",
    "intent": "finalize_summary",
    "expected_artifact": "final user-facing summary",
    "done_when": ["输出最终总结"],
    "output_schema": {},
    "failure_schema": {},
    "resume_instructions": "No further resume.",
    "metadata": {
      "workflow_id": "demo_prompt_loop",
      "workflow_version": "v1"
    }
  }
}
```

Handling rule:

- execute `final_prompt_envelope.prompt` exactly once
- if `next_step_recommendations` is present, follow its instructions and read
  `workflow-binding.json` before recommending a follow-up workflow
- stop after that
- do not call `resume` again

#### `error` response

If the bridge fails, it may still write a response file. Parse it as:

```json
{
  "kind": "error",
  "error_type": "validation_error | protocol_error | bootstrap_error | execution_error | io_error",
  "message": "human-readable failure",
  "details": {}
}
```

Handling rule:

- treat it as bridge/runtime failure
- do not execute any prompt from it
- do not convert it into a successful workflow step

#### Exit-code interaction

Use both the process exit status and `response.json`:

- process exits `0` and `kind` is `yield` or `done`
  normal success path
- process exits non-zero and `response.json.kind == "error"`
  bridge/runtime failure path
- process exits non-zero and no readable response file exists
  transport/IO failure path
- process exits `0` but the JSON shape does not match the expected branch
  protocol/validation failure path

If a required branch field is missing, treat that as failure. Do not silently
continue with partial data.

### 5. Execute yielded work as host, not as runtime

When `kind == "yield"`, the host agent is only responsible for executing the
current prompt envelope and returning a machine-readable observation.

Do not:

- invent the next branch
- reinterpret `done_when` or `output_schema` as optional hints
- change `workflow_id` during `resume`

### 6. Build the `Observation`

There are two layers here. Keep them distinct:

- bridge minimum validation boundary
  what `bridge.py` currently requires before it will call runtime `resume`
- preferred full `Observation` shape
  the stable shape the host should normally send, even when some sections are
  empty

#### Bridge minimum validation boundary

`bridge.py` currently validates only these top-level fields on `resume`:

```json
{
  "run_id": "string",
  "step_id": "string",
  "status": "succeeded | failed | blocked | partial",
  "summary": "string",
  "structured_output": {}
}
```

This minimum exists so the CLI adapter can reject malformed payloads early. It
is not the full host-side contract.

#### Preferred full `Observation` shape

Normally send this fuller shape, even when the optional sections are empty:

```json
{
  "run_id": "string",
  "step_id": "string",
  "status": "succeeded | failed | blocked | partial",
  "summary": "string",
  "structured_output": {},
  "artifacts": [],
  "error": null,
  "tool_trace": [],
  "raw_output": ""
}
```

Execution rules:

- preserve the exact `run_id` from the most recent yielded response
- preserve the exact `step_id` from the most recent yielded response
- if execution is blocked, return `status = "blocked"` instead of pretending
  success
- prose-only summaries are not enough; put machine-readable facts in
  `structured_output`
- if `tool_trace` is present, each entry must satisfy the runtime
  `ToolTraceEntry` schema
- `artifacts: []` is valid
- `error: null` is valid
- `tool_trace: []` is valid
- if `error` is an object, it must follow the structured `error` contract
- if `tool_trace` is non-empty, each entry must follow the structured
  `ToolTraceEntry` contract

### 7. Call `bridge.py resume`

```bash
python <skill-root>/scripts/bridge.py resume \
  --repo-root <repo-root> \
  --run-id <run-id> \
  --observation-file <observation.json> \
  --response-file <response.json>
```

The CLI `--run-id` must match `observation.run_id`.

Resume identity contract:

- `observation.run_id` must equal the CLI `--run-id`
- `observation.run_id` must equal the most recent yielded `response.run_id`
- `observation.step_id` must equal the most recent yielded `response.step_id`
- `resume` does not accept `workflow_id`; workflow selection is frozen after
  `start`

If those invariants do not hold, treat the call as invalid instead of trying to
"repair" the payload on behalf of the runtime.

### 8. Repeat until terminal

Keep looping:

1. inspect `response.kind`
2. if `yield`, execute the envelope and send a new observation through
   `resume`
3. if `done`, execute the final envelope exactly once and stop
4. if `done` includes `next_step_recommendations`, follow its instructions,
   inspect `workflow-binding.json`, and recommend the next workflow instead of calling `resume`
5. if `error`, stop and treat it as a bridge/runtime failure

Compact mental model:

```text
start -> yield -> host executes prompt -> Observation -> resume -> ... -> done
```

## Interface surface only

- Workflow selection is a wrapper-level start contract. Read
  `references/workflow-selection-spec.md` instead of inferring from internal
  workflow files.
- `start/resume` execution is summarized in this file; use
  `references/host-loop.md` for extended examples.
- `Observation` payload rules are summarized in this file; use
  `references/observation-format.md` for the full schema.
- If the task is not explicitly about runtime authoring, stay on these
  interface docs and do not descend into runtime implementation files.

## Non-negotiable rules

- Do not let the host agent invent the next branch; branch and retry decisions belong to runtime policy.
- Do not add a second-layer applicability gate inside the wrapper; if this
  skill is loaded, stay within the runtime contract.
- Do not inspect `verifiers.py`, workflow `contract.py`, workflow `policy.py`,
  or prompt assets during normal start/resume execution unless the task
  explicitly asks for runtime internals.
- Do not drop or rewrite `run_id` and `step_id`; resume safety depends on them.
- Do not write bridge payloads to the repository root. Use `scripts/host_io.py`
  and keep normal host files under `.durable-workflow-runtime/host-io/`.
- Do not treat missing structure as success; missing contract fields are validation failures.
- Do not rewrite runtime semantics in the skill wrapper or choose workflow IDs ad hoc.
- Do not assume a catalog entry changes runtime behavior by itself; only adapter-supported selection or config changes can change the started workflow.
- Do not bypass the published workflow catalog; explicit `workflow_id` must still be catalog-published and loadable.

## Common failure modes

- `blocked` is a first-class outcome, not an embarrassing variant of success.
- `done` does not mean "no more host work"; it means one final envelope still needs to run once.
- `done_when` and `output_schema` are contract fields, not hints.
- Prose-only summaries are not enough for resume or verification; put machine-readable facts in `structured_output`.
- A non-empty `tool_trace` is not free-form metadata; each entry must satisfy the
  runtime `ToolTraceEntry` schema or `resume` will fail validation.
- If the bridge reports `kind = "error"`, treat it as a bridge-level failure, not a successful runtime response.

## Read next

- Default interface docs:
  `references/index.md`,
  `references/bridge-cli-spec.md`,
  `references/workflow-selection-spec.md`,
  `references/host-loop.md`,
  `references/observation-format.md`,
  `references/skill-host-python-spec.md`
- Internal authoring/debugging only:
  `references/workflow-authoring-guide.md`,
  `references/workflow-input-contract-spec.md`,
  `references/step-contract-spec.md`,
  `references/runtime-layout.md`
