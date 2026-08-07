/research-nex {{workflow_goal}} using {{expert_roster}}, {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, and {{round_index}}; for every expert, delegate one independent subagent with its role-specific brief and the immutable shared-space snapshot, collect one grounded result and one distinct artifact, and return the completed expert results for Moderator synthesis.

Stage Context:

- Workflow goal: {{workflow_goal}}
- Expert roster with stable identifiers: {{expert_roster}}
- Current shared knowledge-map summary: {{knowledge_map_summary}}
- Current evidence registry: {{evidence_registry}}
- Current coverage map: {{coverage_map}}
- Completed Moderator transcript: {{conversation_transcript}}
- Last completed round index: {{round_index}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Delegate exactly one independent subagent for every expert in expert_roster; do not substitute one response for multiple experts.
- Give every subagent its role-specific brief and the same immutable shared-space snapshot; subagents must not read or coordinate through sibling outputs.
- Return expert_results as objects with exactly expert_id, summary, and artifact_path fields.
- Each summary and artifact must be grounded in the shared evidence, and each artifact_path must identify a distinct non-empty artifact.
- Keep expert results focused on the assigned perspective; the later Moderator stage makes the round decision.
- Do not request user participation, approval, or checkpoints.

Blocked Conditions:

- Block when any expert result or artifact is missing.
- Block when results are duplicated, empty, or not grounded in the shared evidence.
- Block when the next expert round would exceed the configured autonomous round budget.
