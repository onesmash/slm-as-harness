/content-research-writer {{workflow_goal}} using {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, {{coverage_assessment}}, {{coverage_decision_rationale}}, {{next_round_validation_plan}}, {{report_scope_status}}, and {{conversation_transcript}}; synthesize the autonomous Co-STORM knowledge space into a structured, cited report, preserving evidence links and the Moderator's complete-or-partial scope decision for every substantive section.

Stage Context:

- Knowledge-map summary: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Moderator semantic coverage assessment: {{coverage_assessment}}
- Moderator coverage rationale: {{coverage_decision_rationale}}
- Outstanding next-round validation plan: {{next_round_validation_plan}}
- Report scope status: {{report_scope_status}}
- Conversation transcript: {{conversation_transcript}}
- Requested deliverable: {{deliverable_type}}
- Previous report repair summary: {{report_repair_summary}}
- Concrete report repair actions to apply: {{repair_actions}}

Stage Boundaries:

- Do not introduce unsupported facts, uncited substantive claims, or sections absent from the knowledge map without marking them as limitations.
- Use stable numeric inline citations that refer to the evidence registry; do not fabricate URLs or citation entries.
- Return the report artifact and its path before handoff.
- Do not declare final quality approval in this stage; return the report for an independent quality check.
- Include an exact `Report scope: complete` or `Report scope: partial` line. When partial, preserve every unresolved topic_id, open gap, validation metric, and top-level next-round plan item verbatim in a limitations and next-validation section; do not imply complete coverage.

Blocked Conditions:

- Block when the knowledge map or evidence registry is empty or internally inconsistent.
- Block when the report artifact is unavailable.
- Block when the requested deliverable type cannot be expressed as a cited structured report.
