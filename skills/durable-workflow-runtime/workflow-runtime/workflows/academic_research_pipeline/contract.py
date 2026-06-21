from workflows.common.contracts import (
    SkillRoute,
    SkillUseWhen,
    StepContract,
    StepVerifier,
    WorkflowInputContract,
)


WORKFLOW_ID = "academic_research_pipeline"

ACADEMIC_PIPELINE_ROUTE = SkillRoute(
    skill="academic-pipeline",
    use_when=SkillUseWhen(
        operations=[
            "academic_pipeline",
            "pipeline_orchestration",
            "material_passport",
            "integrity_gate",
            "process_summary",
        ],
    ),
)

DEEP_RESEARCH_ROUTE = SkillRoute(
    skill="deep-research",
    use_when=SkillUseWhen(
        operations=[
            "research_question",
            "deep_research",
            "literature_review",
            "systematic_review",
            "fact_check",
            "socratic_research",
        ],
    ),
)

ACADEMIC_PAPER_ROUTE = SkillRoute(
    skill="academic-paper",
    use_when=SkillUseWhen(
        operations=[
            "paper_writing",
            "paper_planning",
            "outline",
            "revision",
            "citation_check",
            "format_convert",
            "disclosure",
        ],
        file_patterns=["*.md", "*.tex", "*.bib", "*.docx", "*.pdf"],
    ),
)

ACADEMIC_PAPER_REVIEWER_ROUTE = SkillRoute(
    skill="academic-paper-reviewer",
    use_when=SkillUseWhen(
        operations=[
            "peer_review",
            "manuscript_review",
            "methodology_review",
            "re_review",
            "revision_roadmap",
            "reviewer_calibration",
        ],
        file_patterns=["*.md", "*.tex", "*.docx", "*.pdf"],
    ),
)

WORKFLOW_INPUT_CONTRACT = WorkflowInputContract(
    task_input_schema={
        "research_goal": "string",
        "workflow_scope": "string?",
        "entry_stage": "string?",
        "preferred_modes": "object?",
        "paper_type": "string?",
        "target_venue": "string?",
        "citation_format": "string?",
    },
    context_schema={
        "repo_root": "string",
        "source_materials_path": "string?",
        "paper_path": "string?",
        "material_passport_path": "string?",
        "output_dir": "string?",
    },
    constraints_schema={
        "max_steps": "integer?",
        "require_user_checkpoints": "boolean?",
        "enable_claim_audit": "boolean?",
        "allow_format_render": "boolean?",
        "max_revision_loops": "integer?",
    },
)

COLLECT_RESEARCH_CONTEXT = StepContract(
    done_when=[
        "识别用户已有材料、目标、入口阶段和关键缺口",
        "缺少研究目标、论文草稿或 passport 等入口必需材料时返回 blocked",
        "返回 research_goal、entry_stage、available_materials、missing_inputs、ready_for_pipeline",
    ],
    output_schema={
        "research_goal": "string",
        "entry_stage": "string",
        "available_materials": "object[]",
        "paper_path": "string?",
        "material_passport_path": "string?",
        "output_dir": "string?",
        "missing_inputs": "string[]",
        "open_questions": "string[]",
        "ready_for_pipeline": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "missing_inputs": "string[]?",
        "open_questions": "string[]?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_collect_research_context",
        timeout_seconds=15,
        run_on_status=["succeeded", "blocked"],
    ),
)

PLAN_ACADEMIC_PIPELINE = StepContract(
    done_when=[
        "生成 ARS 阶段计划、入口路由、模式选择和 checkpoint 策略",
        "必须保留 Stage 2.5 与 Stage 4.5 integrity gate，不得静默跳过",
        "返回 stage_plan、next_stage、checkpoint_policy、user_confirmed_plan",
    ],
    output_schema={
        "stage_plan": "object[]",
        "next_stage": "string",
        "mode_selection": "object",
        "checkpoint_policy": "object",
        "user_confirmed_plan": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "missing_inputs": "string[]?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_plan_academic_pipeline",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_RESEARCH_STAGE = StepContract(
    done_when=[
        "完成 Stage 1 RESEARCH 或明确返回 blocked",
        "产出 RQ brief、methodology blueprint、bibliography/synthesis 等可交接材料",
        "返回 research_artifact_paths、research_summary、user_confirmed_checkpoint、ready_for_write",
    ],
    output_schema={
        "research_artifact_paths": "string[]",
        "research_summary": "string",
        "source_verification_summary": "object",
        "user_confirmed_checkpoint": "boolean",
        "ready_for_write": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "missing_inputs": "string[]?",
        "error_message": "string?",
    },
    skill_routing=[DEEP_RESEARCH_ROUTE, ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_run_research_stage",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_WRITE_STAGE = StepContract(
    done_when=[
        "完成 Stage 2 WRITE 或明确返回 blocked",
        "用户已确认 paper configuration 与 outline checkpoint",
        "返回 draft_path、paper_configuration_path、outline_path、user_confirmed_checkpoint、ready_for_integrity",
    ],
    output_schema={
        "draft_path": "string",
        "paper_configuration_path": "string?",
        "outline_path": "string?",
        "citation_audit_summary": "object",
        "user_confirmed_checkpoint": "boolean",
        "ready_for_integrity": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "missing_inputs": "string[]?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PAPER_ROUTE, ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_run_write_stage",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_PRE_REVIEW_INTEGRITY = StepContract(
    done_when=[
        "完成 Stage 2.5 integrity gate",
        "运行 7-mode AI research failure checklist 并要求用户 ack",
        "返回 integrity_passed、material_passport_path、suspected_failure_modes、user_acknowledged_gate",
    ],
    output_schema={
        "integrity_passed": "boolean",
        "material_passport_path": "string",
        "integrity_report_path": "string?",
        "suspected_failure_modes": "string[]",
        "user_acknowledged_gate": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "suspected_failure_modes": "string[]?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_run_pre_review_integrity",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_REVIEW_STAGE = StepContract(
    done_when=[
        "完成 Stage 3 REVIEW 或明确返回 blocked",
        "reviewer 只输出报告、decision 与 revision roadmap，不修改手稿",
        "返回 review_package_path、editorial_decision、revision_roadmap_path、user_confirmed_checkpoint",
    ],
    output_schema={
        "review_package_path": "string",
        "editorial_decision": "string",
        "revision_roadmap_path": "string?",
        "critical_issues": "object[]",
        "user_confirmed_checkpoint": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PAPER_REVIEWER_ROUTE, ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_run_review_stage",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_REVISION_STAGE = StepContract(
    done_when=[
        "完成 Stage 4 REVISE 或 Stage 4' RE-REVISE",
        "保留 point-by-point response 与 delta report",
        "返回 revised_draft_path、response_to_reviewers_path、revision_loop_count、revision_complete",
    ],
    output_schema={
        "revised_draft_path": "string",
        "response_to_reviewers_path": "string?",
        "delta_report_path": "string?",
        "revision_loop_count": "integer",
        "user_confirmed_checkpoint": "boolean",
        "revision_complete": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PAPER_ROUTE, ACADEMIC_PAPER_REVIEWER_ROUTE, ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_run_revision_stage",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_REREVIEW_STAGE = StepContract(
    done_when=[
        "完成 Stage 3' RE-REVIEW",
        "输出 revision response checklist、residual issues 与新 decision",
        "返回 rereview_decision、residual_issues、ready_for_final_integrity",
    ],
    output_schema={
        "rereview_package_path": "string",
        "rereview_decision": "string",
        "residual_issues": "object[]",
        "traceability_matrix_path": "string?",
        "ready_for_final_integrity": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PAPER_REVIEWER_ROUTE, ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_run_rereview_stage",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

RUN_FINAL_INTEGRITY = StepContract(
    done_when=[
        "完成 Stage 4.5 FINAL INTEGRITY",
        "零容忍复查通过并由用户 ack 后才能进入 Stage 5",
        "返回 final_integrity_passed、material_passport_path、user_acknowledged_gate",
    ],
    output_schema={
        "final_integrity_passed": "boolean",
        "material_passport_path": "string",
        "final_integrity_report_path": "string?",
        "claim_audit_enabled": "boolean",
        "high_warn_annotations": "string[]",
        "user_acknowledged_gate": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "high_warn_annotations": "string[]?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_run_final_integrity",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

FINALIZE_PUBLICATION_PACKAGE = StepContract(
    done_when=[
        "完成 Stage 5 FINALIZE",
        "用户已选择格式， unresolved HIGH-WARN 不得进入 formatter 输出",
        "返回 output_package_paths、format_selected、final_package_ready",
    ],
    output_schema={
        "output_package_paths": "string[]",
        "format_selected": "string",
        "ai_disclosure_path": "string?",
        "final_package_ready": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PAPER_ROUTE, ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_finalize_publication_package",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

GENERATE_PROCESS_SUMMARY = StepContract(
    done_when=[
        "完成 Stage 6 PROCESS SUMMARY",
        "输出 paper creation process record 与 collaboration quality review",
        "返回 process_summary_path、collaboration_quality_reviewed、summary_ready",
    ],
    output_schema={
        "process_summary_path": "string",
        "self_reflection_report_path": "string?",
        "collaboration_quality_reviewed": "boolean",
        "summary_ready": "boolean",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
    skill_routing=[ACADEMIC_PIPELINE_ROUTE],
    verifier=StepVerifier(
        kind="python_callable",
        ref="workflows.academic_research_pipeline.verifiers:verify_generate_process_summary",
        timeout_seconds=15,
        run_on_status=["succeeded"],
    ),
)

REQUEST_UNBLOCKING_INPUT = StepContract(
    done_when=[
        "明确当前阻塞原因",
        "请求用户提供下一步所需输入、材料或授权",
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
        "解释修复原因并执行可验证的修补动作",
        "返回 retry_reason、retry_notes、repair_actions",
    ],
    output_schema={
        "retry_reason": "string",
        "retry_notes": "string",
        "repair_actions": "object[]",
    },
    failure_schema={
        "blocked_reason": "string?",
        "error_message": "string?",
    },
    skill_routing=[
        ACADEMIC_PIPELINE_ROUTE,
        DEEP_RESEARCH_ROUTE,
        ACADEMIC_PAPER_ROUTE,
        ACADEMIC_PAPER_REVIEWER_ROUTE,
    ],
)

STEP_CONTRACTS = {
    "collect_research_context": COLLECT_RESEARCH_CONTEXT,
    "plan_academic_pipeline": PLAN_ACADEMIC_PIPELINE,
    "run_research_stage": RUN_RESEARCH_STAGE,
    "run_write_stage": RUN_WRITE_STAGE,
    "run_pre_review_integrity": RUN_PRE_REVIEW_INTEGRITY,
    "run_review_stage": RUN_REVIEW_STAGE,
    "run_revision_stage": RUN_REVISION_STAGE,
    "run_rereview_stage": RUN_REREVIEW_STAGE,
    "run_final_integrity": RUN_FINAL_INTEGRITY,
    "finalize_publication_package": FINALIZE_PUBLICATION_PACKAGE,
    "generate_process_summary": GENERATE_PROCESS_SUMMARY,
    "request_unblocking_input": REQUEST_UNBLOCKING_INPUT,
    "repair_and_resume": REPAIR_AND_RESUME,
}


def get_step_contract(step_id: str) -> StepContract:
    try:
        return STEP_CONTRACTS[step_id]
    except KeyError as exc:  # pragma: no cover - guarded by runtime protocol
        raise LookupError(f"unknown step contract: {step_id}") from exc


def list_step_contract_ids() -> list[str]:
    return list(STEP_CONTRACTS.keys())
