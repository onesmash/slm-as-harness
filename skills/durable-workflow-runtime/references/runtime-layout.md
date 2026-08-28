# Runtime Layout

Unless noted otherwise, paths in this file are relative to `<skill-root>/`.
In this repo, `<skill-root>` currently resolves to
`.codex/skills/durable-workflow-runtime/`.

The durable workflow runtime implementation lives under:

```text
<skill-root>/workflow-runtime/
```

## Main areas

- `runtime/`
  Shared runtime infrastructure such as engines, persistence, validation,
  module loading, and verifier execution.
- `workflows/common/`
  Shared contracts, policies, and prompting helpers.
- `workflows/demo_prompt_loop/`
  A concrete workflow with `contract.py`, `policy.py`, `state.py`,
  `verifiers.py`, `graphbuilder_runtime.py`, and `prompts/`.
- `workflows/superpowers_delivery_chain/`
  A multi-stage workflow covering brainstorming, planning, implementation,
  final review, completion verification, branch finishing, repair nodes, and
  an explicit terminal `finalize_summary` step.
- `workflows/academic_research_pipeline/`
  A durable Academic Research Skills workflow covering research, writing,
  integrity gates, review, revision, finalization, process summary, repair
  nodes, and an explicit terminal `finalize_summary` step.
- `templates/workflow_skeleton/`
  A copyable starter skeleton for authoring a new workflow without beginning
  from a blank directory.
- `references/workflow-authoring-guide.md`
  The recommended authoring checklist for adding another workflow to this tree.
- `adapters/skill_host.py`
  The skill-facing adapter used by the skill-local `scripts/bridge.py`.
- `tests/`
  Skill-local regression tests for the bridge, runtime, workflow, and verifier
  behavior.

## Current engine picture

- `runtime/engine_graphbuilder.py`
  The active runtime path, using GraphBuilder-oriented recomputation plus
  persisted `RunState`.

Run the bundled regression suite with:

```bash
python3 -m unittest discover -s <skill-root>/tests
```

## Prompt ownership

Real step prompt bodies live under:

```text
<skill-root>/workflow-runtime/workflows/<workflow>/prompts/*.md
```

`SKILL.md` should never become the source of truth for those prompt bodies.

## Current workflow catalog

The shipped binding catalog now includes at least:

- `demo-prompt-loop`
- `superpowers_delivery_chain`
- `academic-research-pipeline`

Selection happens at `start`:

- explicit `workflow_id` when the caller has a concrete choice
- `default_workflow_id` fallback otherwise

After `start`, `resume` follows persisted `RunState.workflow_id`.

## Runtime protocol guardrails

- `constraints.max_steps` is a positive runtime budget. Each newly accepted
  observation consumes one step; a duplicate `observation_id` replay does not.
  If the budget would yield another ordinary node, the runtime completes through
  the workflow's declared final node with `metadata.degraded=true` and
  `terminal_reason=max_steps_exceeded`.
- Observation and request envelopes are bounded before contract validation or
  verifier execution. This includes total bytes, raw/structured output, strings,
  lists, object depth, trace metadata, and artifacts.
- A stable `observation_id` (or the compatibility alias `attempt_id`) is
  idempotent. Reusing it with a different payload is a protocol conflict.
  Replay responses are retained under bounded count/byte limits; the oldest
  replay entries are evicted before they can make a long-lived run exceed the
  persistence budget.
- Run state is versioned and updated under a per-run lock with revision/CAS;
  persisted files and preflight metadata use atomic replacement.
- Runtime history stores compact diagnostic facts only. State snapshots and
  sensitive values are omitted or redacted; retention can set
  `history_degraded=true`.
- Runtime-owned `artifact_refs` and `diagnostic_refs` contain only bounded
  content-addressed metadata (`size_bytes`, `sha256`, media type and path
  reference). Raw observation output is externalized when possible; an
  artifact-store failure keeps the transition usable but marks
  `artifacts_degraded=true` and exposes `diagnostics_degraded` on terminal
  metadata.
- Operational metrics live outside `RunState` in a private, bounded JSONL
  telemetry sink. Events contain only safe labels and numeric measurements such
  as latency, payload/state/history bytes, duplicate replay and degraded state.
- Terminal-run cleanup is explicit through the retention helper. It removes
  only expired `done`/`failed_terminal` state files and their matching artifact
  directory; it does not infer ownership from arbitrary paths or delete active
  runs. Cleanup takes the per-run lock before re-reading/deleting state and
  leaves the lock inode in place so an active resume cannot lose its lock path.
- Host adapters may provide `native_receipts`; the adapter converts them into
  canonical `tool_trace` entries carrying stable receipt/tool/trace/phase,
  timeout, partial-failure, join and artifact-reference facts. A bounded opaque
  metadata map may be carried through for a workflow-owned adapter contract;
  Runtime does not interpret those keys. Business fields and native-operation
  name mappings remain owned by the workflow contract.
