/brainstorming {{workflow_goal}} in {{repo_root}}; use knowledge-base as supporting context, complete clarification and approval, write the approved design under docs/superpowers/specs/, and complete the required spec review loop.

Stage Context:

- Repository root: {{repo_root}}
- Source process doc: {{source_doc_url}}
- Brainstorming source: {{source_skill_url}}

Stage Boundaries:

- Do not implement code in this stage.
- Do not create or apply OpenSpec artifacts until the design direction is approved.
- Keep knowledge-base usage as context lookup, not as separate user-visible stages.
- Follow the normal design-approval flow before writing or finalizing the approved spec document.
- Write the approved brainstorming design as a Markdown document under docs/superpowers/specs/.
- Do not use openspec/changes/** artifacts as the brainstorming design document.
- If the approved request affects a user-visible UI surface, the spec must include implementation-ready visual detail: view hierarchy, per-element properties, typography, colors, spacing, padding, alignment, sizing, constraints, states, assets, interaction behavior, layout relationships, and measurable expectations detailed enough to support code generation and visual verification without guessing.
- If the approved request affects a user-visible UI surface, the spec must name the design-comparison source for visual QA, such as a Figma frame, approved mock, or reference screenshot, and describe the expected app screenshot/view scope to capture for runtime visual comparison.
- Complete the spec review loop before handing back from this stage.
- The spec review loop must launch three independent review subagents from development, design, and testing perspectives before the requirement stage can finish.
- The development perspective must evaluate whether the spec follows /software-design-philosophy, records key design decisions, records impact scope, and is implementation-ready for Dev.
- The design perspective must evaluate whether the spec accurately captures the Figma or approved design source, provides implementation-ready visual detail, and is concrete enough for Dev to build the UI without guessing.
- The testing perspective must evaluate whether the spec defines adequate unit-test expectations, explicit regression cases, and enough behavior detail for QA/Dev to verify the change.

Blocked Conditions:

- Block if no clarification question has been asked and answered.
- Block if the user has not approved the design direction.
- Block if the requested change cannot be scoped to a concrete iOS Client objective.
- Block if the approved spec document is written or finalized before the normal design-approval flow completes.
- Block if a user-visible UI change lacks implementation-ready visual detail, a design-comparison source, or runtime screenshot/view scope.
- Block if the three-perspective spec review loop has not completed or did not include development, design, and testing perspectives.
