执行 ARS Stage 5: FINALIZE。

论文路径：`{{paper_path}}`
Final integrity report：`{{final_integrity_report_path}}`
Final integrity passed：`{{final_integrity_passed}}`
允许格式渲染：`{{allow_format_render}}`

请按计划调用或遵循 `academic-paper` 的 `format-convert` / `disclosure` 能力。格式化前必须确认用户选择的输出格式和 venue disclosure 需求。

完成条件：
- 输出 publication-ready Markdown / DOCX / LaTeX / PDF 中用户确认的格式。
- 如果需要 AI disclosure，生成 disclosure artifact。
- 不得在 unresolved HIGH-WARN claim audit annotation 存在时继续 formatter 输出。
如果用户没有确认格式、Pandoc/LaTeX 环境缺失且无可接受 fallback，返回 `blocked`。
