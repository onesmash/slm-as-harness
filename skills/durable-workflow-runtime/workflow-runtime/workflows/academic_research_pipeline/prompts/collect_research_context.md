收集 `academic-research-pipeline` 的入口上下文。

用户目标：
{{research_goal}}

请识别这次学术研究任务的可执行入口，而不是直接进入写作或评审。

需要完成：
- 判断用户是从零开始研究、已有研究材料、已有论文草稿、已有 review comments，还是只需要最终格式化/流程总结。
- 记录已有材料路径、论文草稿路径、Material Passport 路径、目标输出目录。
- 如果缺少入口所需的核心材料，返回 `status = "blocked"`。
- 如果可以继续，返回 `status = "succeeded"`。

有效 `entry_stage`：
- `research`
- `write`
- `pre_review_integrity`
- `review`
- `revision`
- `rereview`
- `final_integrity`
- `finalize`
- `process_summary`

不要跳过 Stage 2.5 或 Stage 4.5 integrity gate；如果用户带来论文草稿，默认入口应先经过 `pre_review_integrity`，除非已有未修改内容对应的 integrity report。
