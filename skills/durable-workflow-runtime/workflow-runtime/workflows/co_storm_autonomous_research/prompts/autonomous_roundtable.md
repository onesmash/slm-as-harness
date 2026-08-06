/research-nex {{workflow_goal}} using {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, {{conversation_transcript}}, {{subagent_result_summaries}}, {{subagent_run_ids}}, and {{subagent_binding_records}}; act as the Co-STORM Moderator over the completed independent expert subagent fan-out, synthesize one grounded roundtable turn, update the shared conceptual space, and return exactly one of continue, reorganize, or report.

Stage Context:

- Current expert roster: {{expert_roster}}
- Shared knowledge-map summary: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Conversation transcript: {{conversation_transcript}}
- Completed independent subagent run IDs: {{subagent_run_ids}}
- Independent expert-subagent result summaries: {{subagent_result_summaries}}
- Independent result artifacts: {{subagent_artifact_paths}}
- Expert-to-subagent binding records: {{subagent_binding_records}}
- Current round index: {{round_index}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Do not request user participation or invent a user utterance; the Moderator owns autonomous question selection.
- Carry forward the persisted expert-roster records exactly as `{id, role, brief}`; do not collapse them back to strings or rewrite their briefs.
- Produce exactly one new research or moderation turn and preserve prior turns in the returned transcript.
- Do not choose a workflow node in prose; return the structured decision flags and let runtime policy route the next node.
- Do not mark report readiness before the coverage signal or the configured round limit justifies stopping.
- When coverage_threshold is supplied, coverage_map must contain at least that many distinct topics before declaring coverage_sufficient.
- Every new factual claim must be linked to an existing or newly added evidence entry.

Blocked Conditions:

- Block when the current knowledge map, expert roster, or evidence registry cannot be carried forward.
- Block when a grounded answer cannot be produced for the selected research action.
- Block when the round decision is ambiguous or more than one of continue, reorganize, and report is selected.
