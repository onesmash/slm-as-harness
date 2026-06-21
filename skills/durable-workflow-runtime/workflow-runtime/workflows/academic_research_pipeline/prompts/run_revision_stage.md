执行 ARS Stage 4: REVISE 或 Stage 4': RE-REVISE。

论文路径：`{{paper_path}}`
Review package：`{{review_package_path}}`
Revision roadmap：`{{revision_roadmap_path}}`
当前 revision loop：`{{revision_loop_count}}` / `{{max_revision_loops}}`

请按计划调用或遵循 `academic-paper` 的 `revision` / `revision-coach` 模式。目标是处理 review findings，不是重新发起无关研究。

完成条件：
- 产出 revised draft。
- 产出 point-by-point response 或 response-to-reviewers skeleton。
- 产出 delta report 或等价变更说明。
- 用户确认 revision checkpoint。
如果 revision loop 已耗尽、用户未确认修改、或缺少 review roadmap，返回 `blocked`。
