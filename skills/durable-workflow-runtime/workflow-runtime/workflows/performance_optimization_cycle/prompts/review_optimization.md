/requesting-code-review review {{implementation_summary}} using {{implementation_plan_path}} and {{submission_test_output}}; return actionable findings and whether the change is ready for knowledge-base maintenance.

Stage Context:

- Changed paths: {{changed_paths}}
- Success criteria: {{success_criteria}}

Stage Boundaries:

- Do not approve a change that modified tests/ or re-enabled multicore.
- Do not update the knowledge base in this stage.

Blocked Conditions:

- Block if submission-test evidence is missing.
