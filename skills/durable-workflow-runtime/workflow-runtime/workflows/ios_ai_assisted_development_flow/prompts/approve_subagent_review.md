/brainstorming ask the user whether they approve launching independent development, design, and testing subagent reviews for {{approved_design_path}} before implementation planning continues.

Stage Context:

- Approved design path: {{approved_design_path}}
- Approved design summary: {{approved_design_summary}}
- Repository root: {{repo_root}}

Stage Boundaries:

- Do not launch any review subagents in this stage.
- Do not write the implementation plan in this stage.
- Wait for an explicit yes-or-no authorization decision from the user.
- If the user declines subagent review, summarize the decision clearly and do not continue into spec review or implementation planning.

Blocked Conditions:

- Block if the user has not provided an explicit yes-or-no authorization decision yet.
- Block if the approved design package is missing.
