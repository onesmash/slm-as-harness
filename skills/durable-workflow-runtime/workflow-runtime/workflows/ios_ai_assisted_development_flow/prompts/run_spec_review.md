/brainstorming-nex review the approved design package at {{approved_design_path}} through independent development, design, and testing subagent reviews; hand in the concrete review artifacts and confirm whether the design is ready for implementation planning.

Stage Context:

- Approved design path: {{approved_design_path}}
- Approved design summary: {{approved_design_summary}}
- Subagent review authorization: {{authorization_summary}}
- Repository root: {{repo_root}}
- UI surface affected: {{ui_surface_affected}}
- Design comparison source: {{design_comparison_source}}
- Runtime visual comparison scope: {{runtime_visual_comparison_scope}}

Stage Boundaries:

- Use independent development, design, and testing subagent reviews; do not replace them with a single-thread summary.
- Hand in the concrete subagent review outputs, not just a combined summary, so the workflow can verify that development, design, and testing reviews really happened.
- Do not write the implementation plan in this stage.
- If the approved request affects a user-visible UI surface, preserve the implementation-ready visual detail and visual QA comparison inputs in the reviewed design package.

Blocked Conditions:

- Block if the user has not approved subagent review.
- Block if the subagent review outputs cannot be handed in as concrete review artifacts for later inspection.
- Block if the three-perspective spec review loop has not completed or did not include development, design, and testing perspectives.
