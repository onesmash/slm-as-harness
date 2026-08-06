Record the exact external dependency that blocked the autonomous workflow; this compatibility fallback is not selected by the normal autonomous path.

Stage Context:

- Current step: {{current_step_id}}
- Return stage: {{return_stage_id}}
- Source stage: {{source_stage_id}}
- Repair category: {{repair_category}}
- Repair summary: {{repair_summary}}
- Required external inputs or approvals:
- {{repair_requirements}}
- Relevant evidence:
- {{repair_evidence}}

Stage Boundaries:

- Do not claim that autonomous research completed while the external dependency is missing.
- Do not invent files, credentials, or user decisions that are not already available.
- Use this helper only after repair has already attempted self-repair 3 times and still requires external help.

Blocked Conditions:

- Stay blocked if the missing external input still cannot be named concretely.
