执行 ARS Stage 3: REVIEW。

论文路径：`{{paper_path}}`
Material Passport：`{{material_passport_path}}`

Integrity 状态：`{{integrity_passed}}`

请按计划调用或遵循 `academic-paper-reviewer`。本阶段是只读评审：reviewer 只能产出报告、editorial decision 和 revision roadmap，不得修改手稿。

完成条件：
- 生成 review package，包括 EIC、methodology、domain、perspective、Devil's Advocate 或所选模式需要的报告。
- 生成 Editorial Decision：`accept`、`minor_revision`、`major_revision` 或 `reject`。
- 非 accept 决策必须给出 revision roadmap。
- 用户确认 Stage 3 checkpoint。
如果材料未通过 integrity、评审配置未确认、或 reviewer 试图改写手稿，返回 `blocked`。
