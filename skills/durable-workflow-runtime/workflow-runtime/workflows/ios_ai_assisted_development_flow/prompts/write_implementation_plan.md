/writing-plans {{design_path}}; write or revise the implementation plan under docs/superpowers/plans/, incorporate any recorded replanning feedback, and default the recorded execution mode to subagent-driven without asking the user to choose between execution styles.

Stage Context:

- Design path: {{design_path}}
- Design summary: {{design_summary}}
- Repository root: {{repo_root}}
- Latest plan update summary: {{plan_update_summary}}
- Latest debugging summary: {{debugging_summary}}
- Latest open issues: {{open_issues}}

Stage Boundaries:

- Do not implement code in this stage.
- Write the plan as a Markdown document under docs/superpowers/plans/.
- The plan must be concrete enough for subagent-driven-development to execute task by task.
- Do not require a manual user review of the written plan in this stage.
- Default and record execution_mode as subagent-driven; do not ask the user to choose between execution styles.
- Use the recorded replanning feedback and implementation-learned plan gaps when revising the plan.

Blocked Conditions:

- Block if the design package is missing or ambiguous.
- Block if the design package is missing or still ambiguous after incorporating the recorded replanning feedback.
- Block if the recorded execution mode is not subagent-driven.
