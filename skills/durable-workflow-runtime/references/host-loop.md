# Host Loop

Use this loop whenever the host agent is executing a yielded workflow step.

For the exact CLI contract and example payloads, read `bridge-cli-spec.md`
first.

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Current wrapper behavior:

- the skill-local adapter still supports a default workflow via
  `<skill-root>/workflow-binding.json`
- `start` may also accept an explicit `workflow_id`
- once `start` succeeds, `resume` always follows persisted
  `RunState.workflow_id`
- host-side request/response/observation files should use the stable layout
  described below instead of ad hoc repo-root or `/tmp` paths

## Start

First allocate the request path through `scripts/host_io.py`; do not hand-write
bridge payloads into the repository root:

```bash
python <skill-root>/scripts/host_io.py pending-start \
  --repo-root <repo-root> \
  --workflow-id <workflow_id-optional>
```

Build a request object with:

```json
{
  "task_input": {},
  "context": {},
  "constraints": {}
}
```

Optional skill-side parameter:

- `workflow_id`
  When the caller already knows the intended workflow, pass it to `start`.
  When omitted, fall back to `default_workflow_id`.

This optional parameter is a start-time selector, not part of
`task_input/context/constraints`.

Write the request object to the returned pending path, choose a response file in
that same `host-io/pending/` directory, then call:

```bash
python <skill-root>/scripts/bridge.py start \
  --repo-root <repo-root> \
  --request-file <start-request.json> \
  --response-file <response.json> \
  --workflow-id <workflow-id-optional>
```

If the task clearly matches a specific workflow, choose it before `start`. If
not, let the adapter fall back to `default_workflow_id`.

Before `start`, the runtime has not issued a `run_id` yet. Store the request in
the stable pending path:

```text
<repo-root>/.durable-workflow-runtime/host-io/pending/<workflow_id>-start-request.json
```

After `start` returns a `yield` or `done` response with a `run_id`, allocate the
run-scoped layout:

```bash
python <skill-root>/scripts/host_io.py ensure-run \
  --repo-root <repo-root> \
  --run-id <run_id> \
  --workflow-id <workflow_id-optional>
```

Then copy or move the request into the returned `start_request` path if you need
a run-scoped replay record.

Practical mapping:

- caller supplied `workflow_id`
  add `--workflow-id <workflow_id>`
- caller omitted `workflow_id`
  omit `--workflow-id`

Branch on `response.kind`:

- `yield`: execute `prompt_envelope.prompt`
- `done`: execute `final_prompt_envelope.prompt` once, then stop
- `error`: treat as bridge/runtime failure, not as a successful workflow result

## Resume

After host execution, allocate observation and response paths through
`host_io.py`:

```bash
python <skill-root>/scripts/host_io.py observation-path \
  --repo-root <repo-root> \
  --run-id <run_id> \
  --step-id <step_id> \
  --sequence <n>

python <skill-root>/scripts/host_io.py response-path \
  --repo-root <repo-root> \
  --run-id <run_id> \
  --step-id <step_id> \
  --sequence <n>
```

Write the `Observation`, then call:

```bash
python <skill-root>/scripts/bridge.py resume \
  --repo-root <repo-root> \
  --run-id <run-id> \
  --observation-file <observation.json> \
  --response-file <response.json>
```

Repeat until `kind == "done"`.

## Host I/O Layout

The runtime owns durable run state under:

```text
<repo-root>/.durable-workflow-runtime/runs/<run_id>.json
```

The host agent owns bridge payloads and artifacts under:

```text
<repo-root>/.durable-workflow-runtime/host-io/<run_id>/
  start-request.json
  latest-response.json
  manifest.json
  responses/
    001_collect_context.json
  observations/
    001_collect_context.json
  artifacts/
    ...
```

Use `<skill-root>/scripts/host_io.py` to allocate these paths. The helper keeps
host files grouped by run, rejects path traversal in `run_id`, `step_id`, and
artifact paths, and avoids scattering `.durable-workflow-*.json` files in the
repository root.

Naming convention:

- `responses/<sequence>_<step_id>.json` stores raw bridge responses
- `observations/<sequence>_<step_id>.json` stores host observations sent to
  `resume`
- `latest-response.json` may be overwritten as a convenience pointer
- `artifacts/` stores user-facing or step-produced files that should survive the
  session

Do not store normal host I/O in random `/tmp` paths unless debugging a transport
failure before the repo root is known.

`bridge.py` enforces this layout for normal `start`, `preflight`, and `resume`
payloads. Use `--allow-unsafe-host-io-paths` only for an explicit transport
debugging run where writing inside the repo-local host I/O tree is impossible.

## Required handling rules

- Preserve `run_id` exactly.
- Preserve `step_id` exactly.
- Treat `done_when` and `output_schema` as contract fields, not as hints.
- If execution is blocked, return `status = "blocked"` instead of pretending
  success.
- If the bridge exits non-zero and still writes `response.json`, treat
  `kind = "error"` as a bridge-level failure, not a runtime success response.
- If `response.kind == "done"`, execute `final_prompt_envelope` exactly once
  and do not call `resume` again.
- If a `done` response includes `next_step_recommendations`, follow its
  instructions and read the `workflow-binding.json` catalog before recommending
  a follow-up workflow.
  Starting the chosen workflow is a new `start` call with the selected
  `workflow_id`, not a `resume`.
