/research-nex {{workflow_goal}} using {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, and {{conversation_transcript}}; reorganize the shared Co-STORM knowledge space by expanding overloaded topics, merging redundant branches, removing unsupported leaves, and returning the map to the autonomous roundtable.

Stage Context:

- Current knowledge-map summary: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Conversation transcript: {{conversation_transcript}}
- Prior reorganization count: {{reorganization_count}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Do not discard an evidence entry unless it is explicitly marked duplicate or unsupported and its provenance is preserved in the result.
- Do not generate the final report in this stage.
- Do not choose the next workflow node; return reorganized evidence to runtime policy.
- Keep the knowledge map aligned with actual evidence and observed coverage gaps.

Blocked Conditions:

- Block when the knowledge map cannot be reconstructed from the carried-forward evidence and transcript.
- Block when reorganization would leave the map without supported topics.
