# Durable Workflow Runtime References

Read only the spoke you need. Start with interface docs. Do not open runtime
internals such as workflow `contract.py`, `policy.py`, `state.py`,
`verifiers.py`, `graphbuilder_runtime.py`, or workflow prompt assets unless
the task is explicitly about authoring or debugging those internals.

Path convention used below:

- unless explicitly marked as a repo-local example, paths are relative to
  `<skill-root>/`, meaning the directory that contains this skill's
  `SKILL.md`
- in this repo, `<skill-root>` currently resolves to
  `.codex/skills/durable-workflow-runtime/`

- Default interface docs
  Start here for normal use, start/resume execution, or bridge debugging.
- `bridge-cli-spec.md`
  Read when invoking `scripts/bridge.py`, building a host loop around it, or
  checking what the response file should contain.
- `workflow-selection-spec.md`
  Read when deciding which `workflow_id` to start, how `flow_description`
  should be written, or how the default workflow fallback is supposed to work.
- `host-loop.md`
  Read when you need the concrete `start/resume` loop, bridge commands, or
  success-kind handling.
- `observation-format.md`
  Read when you need to build, validate, or debug `Observation` payloads,
  especially non-empty `tool_trace` or `error` objects.
- `skill-host-python-spec.md`
  Read when changing the thin Python adapter that the bridge loads, especially
  if you need to change workflow binding or bootstrap behavior.

- Internal authoring/debugging docs
  Read these only when the task explicitly requires runtime internals or
  workflow implementation details.
- `workflow-authoring-guide.md`
  Read when adding a new workflow to this skill bundle, wiring its catalog
  entry, contracts, state, graph, prompts, and regression tests end to end.
- `prompt-asset-template.md`
  Read when writing or reviewing workflow prompt assets and you need the
  standard prompt shape, including what belongs in prompt text versus
  `StepContract.output_schema` / `failure_schema`.
- `prompt-placeholder-spec.md`
  Read when authoring prompt assets and you need to know which
  `{{placeholder}}` keys are actually available, where they come from, or why
  a missing template key is failing prompt rendering.
- `workflow-input-contract-spec.md`
  Read when defining or debugging workflow start-time input semantics for
  `task_input`, `context`, and `constraints`.
- `step-contract-spec.md`
  Read when defining or debugging yielded-step tool constraints, schemas, or
  verifier behavior.
- `runtime-layout.md`
  Read when you need to modify this skill's `workflow-runtime/`, understand
  where contracts, policy, prompts, verifiers, and engines live, or explain
  new-vs-old engine boundaries.
