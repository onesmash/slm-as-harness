# Prompt Placeholder Spec

Unless explicitly marked as a repo-local example, paths in this file are
relative to `<skill-root>/`.

Read this file when authoring or editing prompt assets under:

```text
<skill-root>/workflow-runtime/workflows/<workflow_id>/prompts/
```

Use it to answer three questions:

1. 哪些 `{{placeholder}}` 语法是合法的？
2. placeholder 的值从哪里来？
3. 如何避免在模板里写出 runtime 永远不会提供的 key？

## 1. 渲染规则

当前 placeholder 渲染发生在：

```text
workflow-runtime/workflows/common/prompting.py
```

关键规则：

- 只支持 `{{name}}` 这种简单占位符
- `name` 只能由字母、数字、下划线组成
- `{{ workflow_goal }}` 这种带空格写法也可以
- 不支持条件、循环、点路径、过滤器或表达式
- 如果 prompt 文件里出现了 placeholder，但没有传入 `template_context`，会直接报错
- 如果传入了 `template_context`，但缺少某个 key，也会直接报错

这意味着：

- placeholder 不是“建议”
- placeholder 必须和代码里真正提供的 key 一一对应

## 2. placeholder 值的两个来源

当前 runtime 里，prompt 可用变量只来自两个地方。

### A. start 节点显式传入的 `template_context`

start graph 在 `build_prompt_envelope(...)` 时可以直接传：

```python
template_context={
    "workflow_goal": ctx.state.workflow_goal or "",
}
```

这种变量只对这个 start-yield prompt 生效。

不要误以为 start prompt 自动拥有 `build_template_context(...)` 里的所有 key。

### B. workflow 模块的 `build_template_context(...)`

对于 runtime 在 `resume` 后重新发出的 yielded prompt，以及 final `done` prompt，
`engine_graphbuilder.py` 会调用：

```python
def build_template_context(*, step_id: str, run_state) -> dict: ...
```

这里返回的 dict，就是这些 prompt 真正可用的 placeholder 集合。

如果某个 key 不在这个 dict 里，就不应该写进对应 prompt。

## 3. workflow skeleton 当前可用 placeholder

下面是模板骨架当前已经提供好的 placeholder 契约。

### `run_primary_stage.md`

可用：

- `workflow_goal`

来源：

- start graph 的显式 `template_context`

### `request_unblocking_input.md`

可用：

- `workflow_goal`
- `repair_reason`
- `repair_summary`

来源：

- `build_template_context(...)`

### `repair_and_resume.md`

可用：

- `workflow_goal`
- `return_stage_id`
- `repair_reason`
- `repair_summary`

来源：

- `build_template_context(...)`

### `finalize_summary.md`

可用：

- `workflow_goal`

来源：

- `build_template_context(...)`

## 4. `workflow_skeleton/build_template_context(...)` 当前返回什么

当前骨架实现返回：

```python
{
    "workflow_goal": ...,
    "current_step_id": ...,
    "return_stage_id": ...,
    "repair_reason": ...,
    "repair_summary": ...,
}
```

注意：

- `current_step_id` 现在虽然被提供了，但骨架 prompt 目前没有使用它
- 只有真正写进 prompt 文件的 key 才会参与渲染

## 5. `superpowers_delivery_chain` 当前返回什么

现有样例 workflow `superpowers_delivery_chain` 的 `build_template_context(...)`
当前返回：

- `workflow_goal`
- `current_step_id`
- `return_stage_id`
- `source_stage_id`
- `repair_reason`
- `spec_path`
- `plan_path`
- `execution_mode`
- `review_status`
- `verification_passed`
- `branch_outcome`
- `branch_summary`

这只是该 workflow 的实现面，不代表所有新 workflow 自动拥有这些 key。

## 6. 最容易犯错的地方

### 错误 1：把别的 workflow 的 placeholder 抄过来

例如在新 workflow 里直接写：

```md
当前 execution mode 是 `{{execution_mode}}`
```

但你自己的 `build_template_context(...)` 根本没返回 `execution_mode`。

结果：

- prompt 渲染时直接失败

### 错误 2：以为 start prompt 能读到 repair/final 阶段变量

例如在 `run_primary_stage.md` 里写：

```md
修补后将返回 `{{return_stage_id}}`
```

但 start graph 只传了 `workflow_goal`。

结果：

- 首次 `start` 就会因为缺 key 报错

### 错误 3：改了 prompt，没有同步改 `build_template_context(...)`

这类错误最隐蔽，因为 Markdown 文件本身看起来完全正常，但 runtime 发 prompt 时才会炸。

## 7. Author Checklist

写或改 prompt 之前，按这个顺序做：

1. 先列出该 prompt 里所有 `{{placeholder}}`
2. 判断它是 start prompt 还是 resume/final prompt
3. start prompt：
   检查 start builder 里显式传入的 `template_context`
4. resume/final prompt：
   检查 `build_template_context(...)`
5. 不要从别的 workflow 复制 placeholder，除非你也复制了对应 state/context 代码
6. 改完后补或更新测试，确保 prompt placeholders 和可用 key 一致

## 8. What To Read Next

- `workflow-authoring-guide.md`
  当你正在新增 workflow，并需要看完整 authoring 顺序时读它
- `runtime-layout.md`
  当你需要确认 prompt 资产、graphbuilder、state 和 engine 的关系时读它
