## Goal

检查当前 skill bundle 的 `workflow-runtime` 骨架是否存在。目标路径是
`{{runtime_root_path}}`。

## Required Work

1. 检查 `{{runtime_root_path}}` 是否存在。
2. 如果存在，列出一级目录。
3. 如果不存在，明确返回缺失路径。

## Deliverable Notes

只返回 observation 需要的字段，不要决定下一步分支。
