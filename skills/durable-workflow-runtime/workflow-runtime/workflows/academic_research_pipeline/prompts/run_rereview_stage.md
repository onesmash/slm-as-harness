执行 ARS Stage 3': RE-REVIEW。

Revised draft：`{{revised_draft_path}}`
Review package：`{{review_package_path}}`
Revision roadmap：`{{revision_roadmap_path}}`
当前 revision loop：`{{revision_loop_count}}` / `{{max_revision_loops}}`

请按计划调用或遵循 `academic-paper-reviewer` 的 `re-review` 模式。此阶段只验证修改是否回应评审意见，不重新打开完整首轮评审。

完成条件：
- 生成 revision response checklist。
- 输出 residual issues。
- 给出新 decision：`accept`、`minor_revision` 或 `major_revision`。
- 判断是否 `ready_for_final_integrity`。
如果仍有 residual issues 且 revision loop 尚可用，runtime policy 会回到 revision；不要在 prompt 中自行选择下一节点。
