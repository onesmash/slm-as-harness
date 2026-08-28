为 `academic-research-pipeline` 生成 ARS 阶段计划。

研究目标：
{{research_goal}}

入口阶段：`{{entry_stage}}`

已有材料：
{{available_materials}}

已知路径：
- source_materials_path: `{{source_materials_path}}`
- paper_path: `{{paper_path}}`
- material_passport_path: `{{material_passport_path}}`
- output_dir: `{{output_dir}}`

请使用 Academic Research Skills 的主线阶段设计计划：
1. Stage 1 RESEARCH
2. Stage 2 WRITE
3. Stage 2.5 INTEGRITY
4. Stage 3 REVIEW
5. Stage 4 REVISE
6. Stage 3' RE-REVIEW
7. Stage 4.5 FINAL INTEGRITY
8. Stage 5 FINALIZE
9. Stage 6 PROCESS SUMMARY

要求：
- 根据入口阶段选择 `next_stage`，必须是 workflow 支持的阶段名。
- `stage_plan` 要列出将运行的阶段、推荐 ARS skill/mode、主要 artifact、checkpoint 类型。
- `checkpoint_policy` 必须明确 Stage 2.5 和 Stage 4.5 是不可静默跳过的 integrity gate。
- 需要用户确认计划后，才能返回 `user_confirmed_plan = true`。

如果用户没有确认计划，返回 `blocked`，不要让 runtime 继续进入执行阶段。
