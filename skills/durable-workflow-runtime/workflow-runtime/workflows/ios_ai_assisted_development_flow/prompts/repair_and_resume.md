Repair the previous workflow step using the persisted failure details and prepare a safe retry.

Stage Context:

- Current step: {{current_step_id}}
- Return stage: {{return_stage_id}}
- Source stage: {{source_stage_id}}
- Repair category: {{repair_category}}
- Repair summary: {{repair_summary}}
- Repair requirements:
{{repair_requirements}}
- Relevant evidence:
{{repair_evidence}}

Stage Boundaries:

- Keep the retry scoped to the original return stage instead of changing workflow routing.
- Base the repair plan on the persisted repair requirements rather than generic retries.

Blocked Conditions:

- Return blocked if repair cannot proceed without additional external input or approval.
