/brainstorming ask the user whether they approve launching independent development, design, and testing subagent reviews for {{approved_design_path}} before implementation planning continues.

Stage Context:

- Approved design path: {{approved_design_path}}
- Approved design summary: {{approved_design_summary}}
- Repository root: {{repo_root}}

Stage Boundaries:

- Do not launch any review subagents in this stage.
- Do not write the implementation plan in this stage.
- Wait for an explicit authorization decision from the user.

Blocked Conditions:

- Block if the user has not made an explicit authorization decision yet.
- Block if the approved design package is missing.
