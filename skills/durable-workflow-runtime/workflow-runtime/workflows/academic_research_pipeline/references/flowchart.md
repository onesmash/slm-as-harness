# academic-research-pipeline Flowchart

Developer-facing overview for `academic-research-pipeline`.

Derived from:

- `policy.py`
- `graphbuilder_runtime.py`

This document is informational only. `policy.py` remains the runtime source of
truth, and host agents must not choose branches from this diagram.

Durable academic pipeline for research, writing, integrity gates, review,
revision, re-review, final integrity, publication packaging, and process
summary.

## Global Flow

```mermaid
flowchart TD
    start([start academic-research-pipeline]) --> collect_research_context[collect_research_context]
    collect_research_context --> plan_academic_pipeline[plan_academic_pipeline]
    plan_academic_pipeline --> run_research_stage[run_research_stage]
    run_research_stage --> run_write_stage[run_write_stage]
    run_write_stage --> run_pre_review_integrity[run_pre_review_integrity]
    run_pre_review_integrity --> run_review_stage[run_review_stage]

    run_review_stage --> review_decision{editorial decision}
    review_decision -->|accept| run_final_integrity[run_final_integrity]
    review_decision -->|revise| run_revision_stage[run_revision_stage]
    run_revision_stage --> run_rereview_stage[run_rereview_stage]
    run_rereview_stage -->|cleared| run_final_integrity
    run_rereview_stage -->|more revision budget| run_revision_stage

    run_final_integrity --> finalize_publication_package[finalize_publication_package]
    finalize_publication_package --> generate_process_summary[generate_process_summary]
    generate_process_summary --> finalize_summary([finalize_summary])

    collect_research_context -.->|context not ready| repair_loop[[repair / unblock loop]]
    run_pre_review_integrity -.->|integrity failed| repair_loop
    run_review_stage -.->|reject or unsupported| repair_loop
    run_rereview_stage -.->|budget exhausted with issues| repair_loop
    run_final_integrity -.->|integrity failed| repair_loop
    repair_loop -.->|return_stage_id| plan_academic_pipeline
```

## Policy Notes

- The diagram shows the publication pipeline, not every start-stage alias.
  `plan_academic_pipeline` can still jump into supported stages through
  `STAGE_TO_NODE`.
- Review has one global decision point: accept goes to final integrity, minor or
  major revision enters the revision/re-review loop, and reject or unsupported
  decisions enter repair.
- Any yielded stage first enters the shared repair loop on `blocked`,
  `partial`, `failed`, or verifier failure; shared repair may then escalate to
  `request_unblocking_input` when external help is truly required.
- Repair returns through `return_stage_id`. When unblock was requested by
  shared repair, a successful unblock returns to `repair_and_resume` first so
  repair can own the retry decision.
