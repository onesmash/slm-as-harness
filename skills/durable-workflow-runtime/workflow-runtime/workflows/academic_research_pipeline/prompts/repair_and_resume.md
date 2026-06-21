修复 `academic_research_pipeline` 的当前阶段，然后回到 runtime 指定的返回阶段。

研究目标：
{{research_goal}}

来源阶段：`{{source_stage_id}}`
返回阶段：`{{return_stage_id}}`
修复原因：{{repair_reason}}

上一轮摘要：
{{repair_summary}}

缺少输入：
{{missing_inputs}}

未决问题：
{{open_questions}}

Integrity suspected failure modes：
{{suspected_failure_modes}}

Claim audit HIGH-WARN annotations：
{{high_warn_annotations}}

Critical review issues：
{{critical_issues}}

Residual issues：
{{residual_issues}}

请执行最小修复动作。

不要在本阶段自行选择下一阶段；runtime policy 会根据 Observation 回到 `{{return_stage_id}}` 或继续修复。
