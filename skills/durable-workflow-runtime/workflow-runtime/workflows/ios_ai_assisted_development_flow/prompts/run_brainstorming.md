/brainstorming-nex {{goal}} in {{repo_root}}; use knowledge-base as supporting context and produce a brainstorming design package under docs/superpowers/specs/ that is ready for subagent review authorization before any implementation planning begins.

Stage Context:

- Repository root: {{repo_root}}
- Source process doc: {{source_doc_url}}
- Brainstorming source: {{source_skill_url}}
- Latest spec review perspectives: {{spec_review_perspectives}}
- Latest spec review findings summary: {{spec_review_findings_summary}}
- Latest spec review subagent summaries: {{spec_review_subagent_summaries}}
- Latest spec review artifact paths: {{spec_review_artifact_paths}}
- Latest open questions carried forward: {{open_questions}}

Stage Boundaries:

- Do not implement code in this stage.
- Do not write the implementation plan until spec review confirms the design is ready.
- Keep knowledge-base usage as context lookup, not as separate user-visible stages.
- If this stage is revisiting the design after spec review, address the recorded review findings and preserve the link to the existing review artifacts.
- Write the brainstorming design as a Markdown document under docs/superpowers/specs/.
- Do not use implementation plan documents as the brainstorming design document.
- If the requested change affects a user-visible UI surface, the spec must include implementation-ready visual detail: view hierarchy, per-element properties, typography, colors, spacing, padding, alignment, sizing, constraints, states, assets, interaction behavior, layout relationships, and measurable expectations detailed enough to support code generation and visual verification without guessing.
- If the requested change affects a user-visible UI surface, the spec must name the design-comparison source for visual QA, such as a Figma frame, approved mock, or reference screenshot, and describe the expected app screenshot/view scope to capture for runtime visual comparison.
- Do not wait for the user to review or approve the spec in this stage.
- Do not launch subagent review in this stage; the workflow will ask for explicit authorization in the next stage.

Blocked Conditions:

- Block if the requested change still cannot be scoped to a concrete project objective after reviewing the request and asking the minimum clarification question(s) needed.
- Block if the requested change cannot be scoped to a concrete project objective.
- Block if a user-visible UI change lacks implementation-ready visual detail, a design-comparison source, or runtime screenshot/view scope.
