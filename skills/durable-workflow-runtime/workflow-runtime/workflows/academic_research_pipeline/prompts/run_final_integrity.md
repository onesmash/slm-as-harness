执行 ARS Stage 4.5: FINAL INTEGRITY。

最终论文路径：`{{paper_path}}`
Revised draft：`{{revised_draft_path}}`
Material Passport：`{{material_passport_path}}`
Claim audit enabled：`{{enable_claim_audit}}`

本阶段是零容忍 final gate。不要因为 Stage 2.5 通过就跳过本阶段；本阶段需要从最终内容重新验证。

需要完成：
- 重新运行 7-mode AI research failure checklist。
- 对 final draft 执行 100% claims/citation/data verification。
- 如果启用 claim audit，确认 unresolved HIGH-WARN annotations 不会进入 formatter。
- 向用户展示 final integrity report 并等待 ack。
只有 `final_integrity_passed = true` 且用户 ack 后才能进入 Stage 5。
