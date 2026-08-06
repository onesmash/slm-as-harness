/content-research-writer {{workflow_goal}} using {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, and {{conversation_transcript}}; synthesize the autonomous Co-STORM knowledge space into a structured, cited report at {{output_dir}} or an appropriate repository-relative output path, preserving evidence links for every substantive section.

Stage Context:

- Knowledge-map summary: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Conversation transcript: {{conversation_transcript}}
- Requested deliverable: {{deliverable_type}}
- Output directory: {{output_dir}}
- Previous report repair summary: {{report_repair_summary}}
- Concrete report repair actions to apply: {{repair_actions}}

Stage Boundaries:

- Do not introduce unsupported facts, uncited substantive claims, or sections absent from the knowledge map without marking them as limitations.
- Use stable numeric inline citations that refer to the evidence registry; do not fabricate URLs or citation entries.
- Write the report artifact before returning and keep the path repository-relative when possible.
- Do not declare final quality approval in this stage; the next verification stage owns that gate.

Blocked Conditions:

- Block when the knowledge map or evidence registry is empty or internally inconsistent.
- Block when the report cannot be written to a repository-accessible path.
- Block when the requested deliverable type cannot be expressed as a cited structured report.
