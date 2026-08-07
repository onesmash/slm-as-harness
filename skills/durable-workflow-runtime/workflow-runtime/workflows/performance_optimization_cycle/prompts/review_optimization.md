/requesting-code-review review {{implementation_summary}} against {{research_brief_path}}, {{verification_plan}}, and {{submission_test_output}}; return actionable findings and whether the change is ready for knowledge-base maintenance.

Stage Context:

- Changed paths: {{changed_paths}}
- Success criteria: {{success_criteria}}
- Research brief: {{research_brief_path}}
- Verification plan: {{verification_plan}}

Stage Boundaries:

- Do not approve a change that modified tests/ or re-enabled multicore.
- Do not update the knowledge base in this stage.

Blocked Conditions:

- Block if submission-test evidence is missing.
- Do not approve knowledge-base maintenance while review_findings contains an unresolved critical, blocker, P0, high, or P1 finding.
