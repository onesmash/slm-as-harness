from workflows.common.contracts import StepContract, StepVerifier, WorkflowInputContract


WORKFLOW_ID = "example_workflow"

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={
        "goal": "string",
        "deliverable_type": "string?",
    },
    context_schema={
        "repo_root": "string",
    },
    constraints_schema={
        "max_steps": "integer?",
    },
)

RUN_PRIMARY_STAGE = StepContract(
    done_when=[
        "完成 workflow 的主阶段工作",
        "返回 artifact_paths、handoff_summary、ready_for_finish",
    ],
    output_schema={
        "artifact_paths": "string[]",
        "handoff_summary": "string",
        "ready_for_finish": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
        "missing_inputs": "string[]?",
    },
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.example_workflow.verifiers:verify_run_primary_stage",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REQUEST_UNBLOCKING_INPUT = StepContract(
    done_when=[
        "明确当前阻塞原因",
        "向用户请求继续所需的输入、批准或资源",
    ],
    output_schema={
        "blocking_reason": "string",
        "user_action_needed": "string",
        "suggested_next_input": "string?",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
)

REPAIR_AND_RESUME = StepContract(
    done_when=[
        "解释为什么需要重试",
        "返回 retry_reason、retry_notes、repair_actions",
    ],
    output_schema={
        "retry_reason": "string",
        "retry_notes": "string",
        "repair_actions": "string[]",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
)

STEP_CONTRACTS = {
    "run_primary_stage": RUN_PRIMARY_STAGE,
    "request_unblocking_input": REQUEST_UNBLOCKING_INPUT,
    "repair_and_resume": REPAIR_AND_RESUME,
}


def get_step_contract(step_id: str) -> StepContract:
    try:
        return STEP_CONTRACTS[step_id]
    except KeyError as exc:  # pragma: no cover - template usage path
        raise LookupError(f"unknown step contract: {step_id}") from exc


def list_step_contract_ids() -> list[str]:
    return list(STEP_CONTRACTS.keys())
