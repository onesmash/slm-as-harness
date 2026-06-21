from workflows.common.contracts import StepContract, StepVerifier, WorkflowInputContract


WORKFLOW_ID = "demo_prompt_loop"

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={
        "goal": "string",
    },
    context_schema={
        "repo_root": "string",
    },
    constraints_schema={
        "max_steps": "integer?",
    },
)

COLLECT_CONTEXT = StepContract(
    done_when=[
        "确认 skill bundle 自带的 workflow-runtime 是否存在",
        "返回一级目录列表或缺失原因",
    ],
    output_schema={
        "runtime_exists": "boolean",
        "top_level_entries": "string[]",
        "missing_paths": "string[]",
    },
    failure_schema={
        "blocked_reason": "string",
        "error_message": "string",
    },
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.demo_prompt_loop.verifiers:verify_runtime_scaffold",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REQUEST_MISSING_ACCESS = StepContract(
    done_when=[
        "明确阻塞原因",
        "请求用户提供替代路径或授权",
    ],
    output_schema={
        "user_action_needed": "string",
        "suggested_next_input": "string",
    },
    failure_schema={
        "blocked_reason": "string",
        "error_message": "string",
    },
)

RECHECK_RUNTIME_SCAFFOLD = StepContract(
    done_when=[
        "重新确认 skill bundle 自带的 workflow-runtime 是否存在",
        "解释本次结论与之前不一致的原因",
    ],
    output_schema={
        "runtime_exists": "boolean",
        "top_level_entries": "string[]",
        "missing_paths": "string[]",
    },
    failure_schema={
        "blocked_reason": "string",
        "error_message": "string",
    },
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.demo_prompt_loop.verifiers:verify_runtime_scaffold",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

STEP_CONTRACTS = {
    "collect_context": COLLECT_CONTEXT,
    "request_missing_access": REQUEST_MISSING_ACCESS,
    "recheck_runtime_scaffold": RECHECK_RUNTIME_SCAFFOLD,
}


def get_step_contract(step_id: str) -> StepContract:
    try:
        return STEP_CONTRACTS[step_id]
    except KeyError as exc:  # pragma: no cover - guarded by runtime protocol
        raise LookupError(f"unknown step contract: {step_id}") from exc


def list_step_contract_ids() -> list[str]:
    return list(STEP_CONTRACTS.keys())
