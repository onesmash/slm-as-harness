Repair the previous workflow step using the persisted failure details and prepare a safe retry.

Stage Context:

- Current step: {{current_step_id}}
- Return stage: {{return_stage_id}}
- Source stage: {{source_stage_id}}
- Repair reason: {{repair_reason}}
- Previous summary: {{repair_summary}}
- Blocked reason: {{blocked_reason}}
- Error message: {{error_message}}
- Missing inputs: {{missing_inputs}}
- Missing artifacts: {{missing_artifacts}}
- Failed commands: {{repair_failed_commands}}
- Failing checks: {{repair_failing_checks}}
- Structured repair details: {{repair_details_json}}

Stage Boundaries:

- Keep the retry scoped to the original return stage instead of changing workflow routing.
- Base the repair plan on the persisted failure details rather than generic retries.

Blocked Conditions:

- Return blocked if repair cannot proceed without additional external input or approval.
