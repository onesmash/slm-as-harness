# Observation Format

An `Observation` is the structured result returned by the host after executing
the current `PromptEnvelope`.

## Minimum shape

This is the smallest valid payload when you do not need structured tool trace
or a structured error object:

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
  "raw_output": "string"
}
```

Important boundary:

- `tool_trace: []` is valid.
- `error: null` is valid.
- If `tool_trace` is non-empty or `error` is an object, those sections must
  satisfy their own schemas below. The "minimum shape" example is not the full
  contract.

## Status guidance

- `succeeded`: the step completed and returned the expected structured result
- `partial`: some progress was made, but completion criteria were not met
- `blocked`: external help, permission, or new input is needed
- `failed`: the attempt failed and no useful partial completion exists

## `tool_trace`

Use `tool_trace` only when you have structured host trace data. If you only
have free-form notes, prefer `summary` plus `raw_output`.

Each non-empty `tool_trace` entry must include:

- `tool_name`: non-empty string such as `shell`
- `status`: non-empty string such as `succeeded`

Optional fields:

- `input_summary`
- `output_summary`
- `artifact_refs`
- `error_message`
- `started_at`
- `ended_at`
- `metadata`

Example:

```json
{
  "tool_name": "shell",
  "status": "succeeded",
  "input_summary": "检查 workflow-runtime 是否存在，并列出一级目录",
  "output_summary": "runtime_exists=True; top_level_entries=adapters,runtime,workflows",
  "artifact_refs": [],
  "error_message": null,
  "started_at": "2026-05-29T15:53:56Z",
  "ended_at": "2026-05-29T15:53:56Z",
  "metadata": {
    "path": "/abs/path/to/workflow-runtime",
    "action": "inspect_runtime_scaffold"
  }
}
```

Common gotcha:

- Do not send ad-hoc objects like `{"tool": "shell", "action": "ls"}`. If you
  cannot fill at least `tool_name` and `status`, leave `tool_trace` empty.

## `error`

When `error` is present, it must be an object with:

- `type`
- `message`
- optional `details` object

Example:

```json
{
  "type": "permission_error",
  "message": "cannot access workflow-runtime",
  "details": {}
}
```

## Rules

- Never change `run_id` or `step_id`.
- Keep `structured_output` aligned with the yielded step contract.
- Put machine-readable facts in `structured_output`, not only in `summary`.
- Use `tool_trace` when structured host trace is available.
- Use `error` only for actual failure or blocking conditions.
- When in doubt, prefer `tool_trace: []` over malformed partial entries.
- Treat an observation as a one-time runtime input. After `resume` accepts it,
  the run history has already consumed that attempt; editing the old file does
  not retroactively change persisted state.
