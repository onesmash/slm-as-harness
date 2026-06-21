Request the exact external input needed to unblock the workflow and preserve the original return stage.

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

- Do not resume the workflow until the exact missing external dependency is identified.
- Do not invent files, credentials, or user decisions that are not already available.

Blocked Conditions:

- Stay blocked if the missing external input still cannot be named concretely.
