/research-nex {{workflow_goal}} using {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, and {{conversation_transcript}}; reorganize the shared Co-STORM knowledge space by expanding overloaded topics, merging redundant branches, and removing unsupported leaves without dropping or renumbering merged evidence ids, and return the updated map with a completion decision.

Stage Context:

- Current knowledge-map summary: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Conversation transcript: {{conversation_transcript}}
- Prior reorganization count: {{reorganization_count}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Preserve every merged citation identifier; mark duplicates in the knowledge-map summary instead of deleting, renumbering, or rewriting evidence_registry rows. New numbered evidence comes only from expert-result merge.
- Do not generate the final report in this stage.
- Return the reorganized evidence and completion decision without selecting a subsequent research activity.
- Keep the knowledge map aligned with actual evidence and observed coverage gaps.
- Return reorganization_count equal to the persisted reorganization_count plus one, and never exceed constraints.max_reorganizations.

Blocked Conditions:

- Block when the knowledge map cannot be reconstructed from the carried-forward evidence and transcript.
- Block when reorganization would leave the map without supported topics.
