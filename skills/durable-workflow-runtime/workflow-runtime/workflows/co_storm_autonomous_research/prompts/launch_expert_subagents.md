/research-nex {{workflow_goal}} using {{expert_roster}}, {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, and {{round_index}}; use the host's independent subagent API/tool to launch one isolated subagent per expert in parallel for the next Co-STORM round, give each only its role-specific research brief plus the immutable shared-space snapshot, wait for every subagent, and return the complete fan-out manifest with grounded result artifacts for Moderator synthesis.

Stage Context:

- Workflow goal: {{workflow_goal}}
- Expert roster with stable identifiers: {{expert_roster}}
- Current shared knowledge-map summary: {{knowledge_map_summary}}
- Current evidence registry: {{evidence_registry}}
- Current coverage map: {{coverage_map}}
- Completed Moderator transcript: {{conversation_transcript}}
- Last completed round index: {{round_index}}
- Canonical subagent run history (runtime-owned; failed attempts are not included): {{subagent_run_history}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Use the host's independent subagent API/tool to launch exactly one new isolated subagent for every expert in expert_roster; do not substitute one model response for multiple experts.
- Launch the expert subagents in parallel and wait for all of them before returning the fan-out observation.
- Give each subagent an isolated role-specific prompt and the same immutable shared-space snapshot; subagents must not read or coordinate through sibling outputs.
- Each subagent must return a grounded perspective and write a distinct repository-relative result artifact under repo_root.
- Return one structured subagent_binding_records object per expert, linking expert_id, subagent_run_id, summary, artifact_path, spawn_receipt, and completion_receipt; a real batch join may use the same completion_receipt for every covered expert.
- Return tool-trace evidence for every spawn and wait/join operation in the host's canonical metadata shape; the host adapter may normalize flat trace fields, and one join entry may carry expert_ids[] and subagent_run_ids[] for a real batch receipt.
- Do not hand-copy persisted history or append failed attempts to it; runtime derives and promotes canonical history only after this contract passes.
- Do not let an expert subagent choose workflow routing; the later Moderator stage owns continue, reorganize, or report.
- Do not request user participation, approval, or checkpoints.

Blocked Conditions:

- Block when any expert cannot be assigned a distinct subagent run.
- Block when the host cannot prove that all expert subagents completed independently.
- Block when a subagent result or repository-relative artifact is missing, empty, duplicated, or ungrounded.
- Block when the fan-out would exceed the configured autonomous round budget.
