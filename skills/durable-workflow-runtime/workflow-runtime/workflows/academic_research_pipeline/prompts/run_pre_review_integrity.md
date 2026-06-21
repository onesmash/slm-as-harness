执行 ARS Stage 2.5: INTEGRITY。

论文草稿路径：`{{paper_path}}`
当前 draft_path：`{{draft_path}}`
Material Passport：`{{material_passport_path}}`

本阶段是强制 gate。不要跳过，不要把“难以验证”当作通过。

需要完成：
- 运行 pre-review integrity 检查，包括引用/数据/claim provenance，以及 7-mode AI research failure checklist。
- 生成或更新 Material Passport。
- 向用户展示 integrity report 并等待 ack。
路由规则由 runtime policy 决定：
- `integrity_passed = true` 才能进入 Stage 3 REVIEW。
- `integrity_passed = false` 必须返回同一 gate 的修复/重跑路径。

如果用户没有 ack gate 结果，返回 `blocked`。
