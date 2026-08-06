/research-nex {{workflow_goal}} using {{task_input_json}} and {{context_json}}; run an autonomous Co-STORM warm start that identifies complementary expert perspectives with stable identifiers, conducts grounded background conversations, and seeds the shared knowledge map and evidence registry before independent expert subagent fan-out begins.

Stage Context:

- Task input: {{task_input_json}}
- Execution context: {{context_json}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Do not wait for or request user input, approval, or checkpoints.
- Do not write the final report in this stage; produce research material and a knowledge-map seed.
- Every evidence entry must use the form [n] source-locator — supported claim or question, preserving a stable citation number, source locator, and claim.
- Keep expert perspectives complementary rather than duplicating the same general-background role.
- Return `expert_roster` as records with exactly `id`, `role`, and `brief` string fields; ids must be stable and unique.
- Give every expert a stable, unique identifier that can be passed to an independent subagent in later rounds.

Blocked Conditions:

- Block when the research goal or retrieval scope is missing.
- Block when grounded retrieval is unavailable and no source materials are supplied.
- Block when fewer than two distinct expert perspectives or a traceable evidence registry can be produced.
