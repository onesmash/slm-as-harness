Present the refinement summary to the user and request explicit approval to proceed with implementation.

Stage Context:

- Refinement summary: {{refinement_summary}}
- Changed artifacts: {{changed_artifacts}}
- Change name: {{change_name}}
- Change path: {{change_path}}

Stage Boundaries:

- Do not modify any OpenSpec artifacts during this stage.
- Do not implement any code during this stage.
- This is purely a user confirmation gate.

Blocked Conditions:

- Block if the user explicitly rejects the refinement results.
- Block if the user asks for additional refinement before proceeding.
