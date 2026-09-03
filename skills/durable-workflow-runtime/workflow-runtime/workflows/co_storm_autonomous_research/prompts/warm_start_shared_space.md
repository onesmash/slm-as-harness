/research-nex {{workflow_goal}} using {{task_input_json}} and {{context_json}}; run an autonomous Co-STORM warm start that identifies complementary expert perspectives with stable identifiers, conducts grounded background conversations, and seeds the shared knowledge map and evidence registry before independent expert result collection begins.

Stage Context:

- Task input: {{task_input_json}}
- Execution context: {{context_json}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Do not wait for or request user input, approval, or checkpoints.
- Do not write the final report in this stage; produce research material and a knowledge-map seed.
- Every evidence entry must use the form [n] source-locator — supported claim or question, preserving a stable citation number, source locator, and claim.
- Keep expert perspectives complementary rather than duplicating the same general-background role.
- Return expert_roster as records with exactly id, role, and brief string fields; ids must be stable and unique and later bindings must reference only id.
- Give every expert a stable, unique identifier that can be passed to an independent subagent in later rounds.
- Create at least two expert perspectives with genuinely distinct, non-overlapping roles (for example technical implementer, historical or ecosystem evolution, security and risk, adoption and business, and future-trend perspectives); add as many additional complementary roles as the research scope needs, with no numeric ceiling.
- Seed coverage_map with the full planned topic decomposition of the research goal: derive concise, stable topic ids from research_scope in task_input_json (falling back to the goal itself) covering every planned facet, with no numeric ceiling, so the Moderator rounds must adjudicate the entire planned topic set instead of stopping at the deterministic floor.
- Record at least two grounded evidence entries per perspective and capture each perspective's key open question in the conversation transcript, so the expert subagents and the Moderator have concrete material to work from.

Blocked Conditions:

- Block when the research goal cannot be resolved into a retrievable scope and no source materials are supplied.
- Block when grounded retrieval is unavailable and no source materials are supplied.
- Block when fewer than two distinct expert perspectives or a traceable evidence registry can be produced.
