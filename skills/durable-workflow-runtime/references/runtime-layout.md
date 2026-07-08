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

- `demo_prompt_loop`
- `superpowers_delivery_chain`
- `academic_research_pipeline`

Selection happens at `start`:

- explicit `workflow_id` when the caller has a concrete choice
- `default_workflow_id` fallback otherwise

After `start`, `resume` follows persisted `RunState.workflow_id`.
