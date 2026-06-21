# Step Contract Spec

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Read this file when implementing:

- `<skill-root>/workflow-runtime/workflows/<workflow>/contract.py`
- runtime resume-path validation and verifier wiring

## Purpose

`StepContract` is the workflow-scoped source of truth for step execution
constraints and completion semantics.

It keeps these concerns separate:

- the prompt body tells the host what to do now
- `done_when` gives the host a concrete execution checklist
- `output_schema` and `failure_schema` define the return shape
- `verifier` gives the runtime a deterministic way to check whether the step
  actually satisfied its acceptance surface

This means `done_when` is guidance for the host, not the sole judge of
completion.

## Current shared types

Shared types live in:

```text
<skill-root>/workflow-runtime/workflows/common/contracts.py
```

Current public shapes:

```python
class StepVerifier:
    kind: Literal["python_callable", "shell_command"]
    ref: str
    timeout_seconds: int = 30
    run_on_status: list[str] = ["succeeded"]


class StepContract:
    done_when: list[str]
    output_schema: dict
    failure_schema: dict
    verifier: StepVerifier | None = None
```

Workflow-local `contract.py` should expose one lookup function:

```python
def get_step_contract(step_id: str) -> StepContract: ...
```

## Current runtime behavior

On `yield`, the runtime loads the step contract and copies these fields into
`PromptEnvelope`:

- `done_when`
- `output_schema`
- `failure_schema`

That happens in the graphbuilder runtime before the host sees the prompt
envelope.

On `resume`, the runtime:

1. Parses `Observation`.
2. Confirms `observation.step_id` matches the current node.
3. Loads the current step contract.
4. Validates `structured_output` against:
   - `output_schema` when `status == "succeeded"`
   - `failure_schema` for other statuses
5. Runs the verifier if one is configured and the status matches
   `verifier.run_on_status`.
6. Passes the verifier result into workflow policy.

## Current demo workflow contracts

The current demo workflow publishes step contracts for:

- `collect_context`
- `request_missing_access`
- `recheck_runtime_scaffold`

Current contract summary:

- `collect_context`
  - success schema includes `runtime_exists`, `top_level_entries`,
    `missing_paths`
  - failure schema includes `blocked_reason`, `error_message`
  - verifier checks runtime scaffold facts

- `request_missing_access`
  - success schema includes `user_action_needed`, `suggested_next_input`
  - failure schema includes `blocked_reason`, `error_message`
  - no verifier

- `recheck_runtime_scaffold`
  - same schema family as `collect_context`
  - verifier checks runtime scaffold facts again

## Important final-step nuance

The current implementation does not define a `StepContract` for the terminal
`finalize_summary` step.

Instead:

- the runtime emits `DoneResponse`
- `final_prompt_envelope` is assembled from graph node metadata
- `output_schema` and `failure_schema` are empty for that final envelope

So the current contract model applies to yielded steps, not to the final
terminal prompt.

## Verifier guidance

Prefer a verifier when completion can be checked objectively.

Good verifier use cases:

- file or directory exists
- output matches a required shape
- tests pass
- reported artifacts match filesystem facts

Use host reporting without a verifier when completion is mainly semantic or
subjective.

Important distinction:

- protocol failure means the host broke the resume contract
- verifier failure means the step ran but did not satisfy acceptance

Do not collapse those into the same error type.

## Authoring guidance

- Keep `done_when` observable and host-facing.
- Keep `output_schema` limited to fields the workflow actually uses later.
- Keep `failure_schema` limited to data needed for retry, repair, or
  escalation.
- Use stable field names because downstream workflow state and policy may
  depend on them.
