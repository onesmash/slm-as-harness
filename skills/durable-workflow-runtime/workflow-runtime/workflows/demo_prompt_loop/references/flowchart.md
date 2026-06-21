# demo_prompt_loop Flowchart

Developer-facing overview for `demo_prompt_loop`.

Derived from:

- `policy.py`
- `graphbuilder_runtime.py`

This document is informational only. `policy.py` remains the runtime source of
truth, and host agents must not choose branches from this diagram.

## Global Flow

```mermaid
flowchart TD
    start([start demo_prompt_loop]) --> collect_context[collect_context]
    collect_context --> outcome{context usable?}
    outcome -->|yes| finalize_summary([finalize_summary])
    outcome -->|needs access| request_missing_access[request_missing_access]
    outcome -->|needs recheck| recheck_runtime_scaffold[recheck_runtime_scaffold]
    request_missing_access --> finalize_summary
    recheck_runtime_scaffold --> finalize_summary
```

## Policy Notes

- The workflow is intentionally tiny: collect context, optionally repair the
  context report, then finalize.
- `blocked` routes to `request_missing_access`.
- verifier failure routes to `recheck_runtime_scaffold`.
- `request_missing_access` and `recheck_runtime_scaffold` both converge on the
  final summary.
