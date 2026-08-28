# performance-optimization-cycle Flowchart

Developer-facing overview for `performance-optimization-cycle`.

The Mermaid diagram shows the durable route; the table below explains what each stage does.

```mermaid
flowchart TD
    start([start performance-optimization-cycle]) --> diagnose_performance[diagnose_performance]
    diagnose_performance -->|success| brainstorm_optimization[brainstorm_optimization]
    brainstorm_optimization -->|success| research_optimization[research_optimization]
    research_optimization -->|success| implement_optimization[implement_optimization]
    implement_optimization -->|success| review_optimization[review_optimization]
    review_optimization -->|success| update_optimization_knowledge_base[update_optimization_knowledge_base]
    update_optimization_knowledge_base -->|default success| finalize_optimization_cycle([finalize_optimization_cycle])
    diagnose_performance -->|blocked| capture_blocked_cycle_knowledge[capture_blocked_cycle_knowledge]
    brainstorm_optimization -->|blocked| capture_blocked_cycle_knowledge[capture_blocked_cycle_knowledge]
    research_optimization -->|blocked| capture_blocked_cycle_knowledge[capture_blocked_cycle_knowledge]
    implement_optimization -->|blocked| capture_blocked_cycle_knowledge[capture_blocked_cycle_knowledge]
    review_optimization -->|blocked| capture_blocked_cycle_knowledge[capture_blocked_cycle_knowledge]
    update_optimization_knowledge_base -->|blocked| capture_blocked_cycle_knowledge[capture_blocked_cycle_knowledge]
    update_optimization_knowledge_base -->|continue_optimization is_true and cycle limit remains| diagnose_performance[diagnose_performance]
    update_optimization_knowledge_base -->|continue_optimization is_true and max_cycles limit reached| finalize_optimization_cycle([finalize_optimization_cycle])
    capture_blocked_cycle_knowledge -->|blocked| diagnose_performance[diagnose_performance]
    capture_blocked_cycle_knowledge -->|partial| diagnose_performance[diagnose_performance]
    capture_blocked_cycle_knowledge -->|failed| diagnose_performance[diagnose_performance]
    capture_blocked_cycle_knowledge -->|verifier_failed| diagnose_performance[diagnose_performance]
    capture_blocked_cycle_knowledge -->|verifier missing| diagnose_performance[diagnose_performance]
    capture_blocked_cycle_knowledge -->|recovery complete| diagnose_performance[diagnose_performance]
    unblock_loop[[request_unblocking_input]]
    repair_loop[[repair_and_resume]]
    resume_target[[return_stage_id / originating stage]]
    diagnose_performance -.->|partial / failed / verifier| repair_loop
    brainstorm_optimization -.->|partial / failed / verifier| repair_loop
    research_optimization -.->|partial / failed / verifier| repair_loop
    implement_optimization -.->|partial / failed / verifier| repair_loop
    review_optimization -.->|partial / failed / verifier| repair_loop
    update_optimization_knowledge_base -.->|partial / failed / verifier| repair_loop
    unblock_loop -.->|resume via repair owner or return_stage_id| resume_target
    unblock_loop -.->|stay when return_stage_id missing| unblock_loop
    repair_loop -.->|blocked after 3 tries| unblock_loop
    repair_loop -.->|retry via return_stage_id when repair succeeds| resume_target
    repair_loop -.->|blocked before 3 tries / partial / failed / missing return_stage_id| repair_loop
```

Global note: if `max_steps` is exceeded, the runtime may preempt normal business routing and emit the final step with degraded metadata; the final prompt must label the result as a partial handoff and must not claim that all gates passed.

## Stage Responsibilities

| Stage | Does | Produces | Done when |
|---|---|---|---|
| `diagnose_performance` | Produce a measurable baseline and a prioritized bottleneck diagnosis before optimization hypotheses are generated. | performance baseline, bottleneck summary, and diagnostic report | Baseline metrics and their measurement context are recorded.<br>A dominant bottleneck and a diagnostic report path are recorded.<br>The diagnosis is ready to constrain hypothesis generation. |
| `brainstorm_optimization` | Establish the next optimization hypothesis, measurable success criteria, and scored ideation artifact without changing implementation code. | scored optimization-hypothesis shortlist and ideation artifact | At least one testable hypothesis is recorded.<br>Success criteria and a scored ideation artifact path are recorded.<br>The work is ready for evidence gathering. |
| `research_optimization` | Turn the selected hypothesis into traceable technical evidence, a bounded change summary, and a verification plan for implementation. | research brief, implementation-ready change summary, verification plan, and evidence map | A research brief path, evidence summary, implementation-ready change summary, and verification plan are recorded.<br>Implementation risks and open questions are explicit. |
| `implement_optimization` | Implement the planned optimization and prove correctness with the repository submission tests. | implemented candidate with submission-test evidence | The smallest testable change and verification commands are recorded.<br>The implemented change and changed paths are recorded.<br>python tests/submission_tests.py has passed. |
| `review_optimization` | Review correctness, performance evidence, and compliance with the optimization constraints before knowledge-base maintenance. | review findings and acceptance decision for the optimized kernel | Review findings and a readiness decision are recorded. |
| `update_optimization_knowledge_base` | Persist the evidence, implementation outcome, and review decision in the repository knowledge base, then make an explicit next-cycle decision. | updated durable knowledge-base record and next-cycle decision | The updated knowledge-base artifacts and update summary are recorded.<br>The workflow explicitly decides whether to start another optimization iteration. |
| `capture_blocked_cycle_knowledge` | Persist the blocker and any usable evidence as a concise durable learning record, so the next optimization cycle starts without asking the user to unblock this one. | durable knowledge-base record of the blocked stage and its next-cycle learning | A concise record of the blocked stage, blocker, evidence, and next-cycle lead is written to the knowledge base.<br>The workflow is ready to begin a fresh performance diagnosis without waiting for user input. |
| `finalize_optimization_cycle` | Summarize the optimization handoff, including its hypothesis, evidence, implementation verification, review result, knowledge-base artifacts, and why no further iteration is scheduled. If {{degraded}} is true or {{terminal_reason}} is max_steps_exceeded, explicitly label the result partial and do not claim that the optimization cycle completed or passed all gates. Include whether another iteration was requested ({{continue_optimization}}) and the configured cycle limit ({{max_cycles}}). | Final workflow summary or handoff artifact. | Previous business stage completed successfully. |

## Maintenance Notes

- Keep this diagram aligned with `policy.py` and `graphbuilder_runtime.py`.
- If you add non-linear business gates, update `policy.py` and this diagram together.
- Keep repetitive repair edges summarized unless repair policy is the workflow's core behavior.
