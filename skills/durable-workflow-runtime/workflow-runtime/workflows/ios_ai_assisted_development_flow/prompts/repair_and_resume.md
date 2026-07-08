/research-nex investigate the {{repair_category}} failure affecting {{return_stage_id}} using the persisted repair requirements and evidence; use search-nex when fresh source discovery or first-pass verification is needed, then synthesize evidence-backed repair options before the workflow retries or requests external unblocking input.

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
- Blocked self-repair attempts in this repair episode: {{repair_blocked_attempts}}

Stage Boundaries:

- Keep the retry scoped to the original return stage instead of changing workflow routing.
- Base the repair plan on the persisted repair requirements rather than generic retries.
- Use search-nex only as supporting source discovery for research-nex; do not replace research-nex as the primary owner.
- Do not implement code changes in this stage; produce evidence-backed repair options and retry guidance only.
- Attempt self-repair within this repair episode before requesting external help, and only escalate to request_unblocking_input after 3 blocked self-repair attempts in the same repair episode.

Blocked Conditions:

- Return blocked if repair cannot proceed without additional external input or approval.
