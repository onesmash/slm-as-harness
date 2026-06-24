Repair the previous workflow step using the persisted failure details, and decide whether the workflow can retry directly or must first ask for external unblocking input after exhausting the allowed self-repair attempts.

Stage Context:

- Current step: {{current_step_id}}
- Return stage: {{return_stage_id}}
- Source stage: {{source_stage_id}}
- Repair category: {{repair_category}}
- Repair summary: {{repair_summary}}
- Repair requirements:
- {{repair_requirements}}
- Relevant evidence:
- {{repair_evidence}}

Stage Boundaries:

- Keep the retry scoped to the original return stage instead of changing workflow routing.
- Base the repair plan on the persisted repair requirements rather than generic retries.
- Attempt self-repair within this repair episode before requesting external help, and only escalate to request_unblocking_input after 3 blocked self-repair attempts in the same repair episode.

Blocked Conditions:

- Return blocked if repair cannot proceed without additional external input or approval.
