Request the exact external input needed to unblock the workflow and preserve the original return stage.

Stage Context:

- Current step: {{current_step_id}}
- Return stage: {{return_stage_id}}
- Source stage: {{source_stage_id}}
- Repair category: {{repair_category}}
- Repair summary: {{repair_summary}}
- Required external inputs or approvals:
{{repair_requirements}}
- Relevant evidence:
{{repair_evidence}}

Stage Boundaries:

- Do not resume the workflow until the exact missing external dependency is identified.
- Do not invent files, credentials, or user decisions that are not already available.

Blocked Conditions:

- Stay blocked if the missing external input still cannot be named concretely.
