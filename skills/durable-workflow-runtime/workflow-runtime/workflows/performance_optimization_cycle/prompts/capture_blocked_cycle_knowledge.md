/code-kb-workflow record the blocked optimization stage {{source_stage_id}} in the knowledge base at {{repo_root}} using {{repair_summary}} and {{repair_requirements}}; preserve the blocker, available evidence, and next-cycle hypothesis, then hand off directly to a fresh diagnosis.

Stage Context:

- Blocked source stage: {{source_stage_id}}
- Blocked reason: {{repair_summary}}
- Missing or constrained inputs: {{repair_requirements}}
- Relevant evidence: {{repair_evidence}}

Stage Boundaries:

- Do not request user input, approval, credentials, or a decision.
- Record only observed facts, explicit assumptions, and actionable next-cycle leads.
- After this stage succeeds, routing must begin a fresh diagnose_performance cycle rather than retry the blocked stage.

Blocked Conditions:

- If the knowledge base itself cannot be updated, retain the blocker in runtime state and begin a fresh diagnosis without requesting user input.
