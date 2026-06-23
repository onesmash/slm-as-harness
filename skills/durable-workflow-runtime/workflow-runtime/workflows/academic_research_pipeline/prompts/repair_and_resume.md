修复 `academic_research_pipeline` 的当前阶段，然后回到 runtime 指定的返回阶段。

研究目标：
{{research_goal}}

来源阶段：`{{source_stage_id}}`
返回阶段：`{{return_stage_id}}`
修复类别：{{repair_category}}

修复摘要：
{{repair_summary}}

本轮必须满足的要求：
{{repair_requirements}}

与修复直接相关的证据：
{{repair_evidence}}

请执行最小修复动作。

不要在本阶段自行选择下一阶段；runtime policy 会根据 Observation 回到 `{{return_stage_id}}` 或继续修复。
