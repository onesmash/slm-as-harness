/brainstorming-nex {{goal}} in {{repo_root}}; use knowledge-base as supporting context and produce an approved design package under docs/superpowers/specs/ before any implementation planning begins.

Stage Goal:

- Turn the user's iOS Client development goal into clarified requirements and an approved design document before planning, implementation, or subagent review work begins.

Stage Context:

- Repository root: {{repo_root}}
- Source process doc: {{source_doc_url}}
- Brainstorming source: {{source_skill_url}}

Stage Boundaries:

- Do not implement code in this stage.
- Do not write the implementation plan until the design direction is approved.
- Keep knowledge-base usage as context lookup, not as separate user-visible stages.
- Follow the normal design-approval flow before writing or finalizing the approved spec document.
- Write the approved brainstorming design as a Markdown document under docs/superpowers/specs/.
- Do not use implementation plan documents as the brainstorming design document.
- If the approved request affects a user-visible UI surface, the spec must include implementation-ready visual detail: view hierarchy, per-element properties, typography, colors, spacing, padding, alignment, sizing, constraints, states, assets, interaction behavior, layout relationships, and measurable expectations detailed enough to support code generation and visual verification without guessing.
- If the approved request affects a user-visible UI surface, the spec must name the design-comparison source for visual QA, such as a Figma frame, approved mock, or reference screenshot, and describe the expected app screenshot/view scope to capture for runtime visual comparison.
- Do not launch subagent review in this stage; the workflow will ask for explicit authorization in the next stage.

Blocked Conditions:

- Block if no clarification question has been asked and answered.
- Block if the user has not approved the design direction.
- Block if the requested change cannot be scoped to a concrete iOS Client objective.
- Block if the approved spec document is written or finalized before the normal design-approval flow completes.
- Block if a user-visible UI change lacks implementation-ready visual detail, a design-comparison source, or runtime screenshot/view scope.
