/writing-plans {{approved_design_path}}; write or revise the implementation plan under docs/superpowers/plans/, incorporate any recorded replanning feedback, have the user review the plan, and return subagent-driven as the selected execution approach when implementation is ready.

Stage Context:

- Approved design path: {{approved_design_path}}
- Approved design summary: {{approved_design_summary}}
- Repository root: {{repo_root}}
- Latest plan approval feedback: {{plan_user_feedback}}
- Latest plan update summary: {{plan_update_summary}}
- Latest debugging summary: {{debugging_summary}}
- Latest open issues: {{open_issues}}

Stage Boundaries:

- Do not implement code in this stage.
- Write the plan as a Markdown document under docs/superpowers/plans/.
- The plan must be concrete enough for subagent-driven-development to execute task by task.
- The plan review loop with the user must complete before this stage can finish.
- Recommend and capture subagent-driven execution explicitly; do not leave execution_mode open-ended when the workflow is ready to continue.
- Use the recorded replanning feedback and implementation-learned plan gaps when revising the plan.

Blocked Conditions:

- Block if the approved design is missing or ambiguous.
- Block if the plan file has not been written yet.
- Block if the user has not reviewed the written plan.
- Block if the execution approach has not been selected explicitly.
