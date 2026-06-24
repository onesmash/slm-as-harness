Present the implementation plan summary and request explicit approval to execute it with {{execution_mode}}.

Stage Context:

- Plan summary: {{plan_summary}}
- Plan path: {{plan_path}}
- Execution mode: {{execution_mode}}
- Planning revision reason: {{plan_revision_reason}}
- Open questions: {{open_questions}}

Stage Boundaries:

- Do not modify the implementation plan during this stage.
- Do not implement code during this stage.
- This is purely a user confirmation gate.

Blocked Conditions:

- Block if the user response is ambiguous about whether implementation may proceed or the plan needs another pass.
- Block if the plan context is missing and the user cannot meaningfully approve or redirect the work.
