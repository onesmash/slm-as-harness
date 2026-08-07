# co_storm_autonomous_research Flowchart

Developer-facing overview for `co_storm_autonomous_research`.

The Mermaid diagram shows the durable route; the table below explains what each stage does.

```mermaid
flowchart TD
    start([start co_storm_autonomous_research]) --> warm_start_shared_space[warm_start_shared_space]
    warm_start_shared_space -->|success| launch_expert_subagents[launch_expert_subagents]
    launch_expert_subagents -->|success| autonomous_roundtable[autonomous_roundtable]
    synthesize_report -->|success| verify_report[verify_report]
    verify_report -->|success| finalize_collaborative_report([finalize_collaborative_report])
    autonomous_roundtable -->|should_reorganize is_true| reorganize_knowledge_space[reorganize_knowledge_space]
    autonomous_roundtable -->|ready_for_report is_true| synthesize_report[synthesize_report]
    autonomous_roundtable -->|continue_roundtable is_true| launch_expert_subagents[launch_expert_subagents]
    autonomous_roundtable -.->|unmatched business output| autonomous_roundtable[autonomous_roundtable]
    reorganize_knowledge_space -->|reorganized is_true| launch_expert_subagents[launch_expert_subagents]
    reorganize_knowledge_space -.->|unmatched business output| reorganize_knowledge_space[reorganize_knowledge_space]
    verify_report -->|verifier_failed| repair_report[repair_report]
    verify_report -->|verifier missing| repair_loop
    repair_report -->|recovery complete| synthesize_report[synthesize_report]
    repair_report -.->|partial / failed / verifier| repair_report
    repair_report -.->|blocked| repair_loop
    unblock_loop[[request_unblocking_input]]
    repair_loop[[repair_and_resume]]
    resume_target[[return_stage_id / originating stage]]
    warm_start_shared_space -.->|blocked| repair_loop
    warm_start_shared_space -.->|partial / failed / verifier| repair_loop
    launch_expert_subagents -.->|blocked| repair_loop
    launch_expert_subagents -.->|partial / failed / verifier| repair_loop
    autonomous_roundtable -.->|blocked| repair_loop
    autonomous_roundtable -.->|partial / failed / verifier| repair_loop
    reorganize_knowledge_space -.->|blocked| repair_loop
    reorganize_knowledge_space -.->|partial / failed / verifier| repair_loop
    synthesize_report -.->|blocked| repair_loop
    synthesize_report -.->|partial / failed / verifier| repair_loop
    verify_report -.->|blocked| repair_loop
    verify_report -.->|partial / failed| repair_loop
    unblock_loop -.->|resume via repair owner or return_stage_id| resume_target
    unblock_loop -.->|stay when return_stage_id missing| unblock_loop
    repair_loop -.->|blocked after 3 tries| finalize_collaborative_report([finalize_collaborative_report])
    repair_loop -.->|retry via return_stage_id when repair succeeds| resume_target
    repair_loop -.->|blocked before 3 tries / partial / failed / missing return_stage_id| repair_loop
```

Global note: if `max_steps` is exceeded, the runtime may preempt normal business routing and emit the final step with degraded metadata; the final prompt must label the result as a partial handoff and must not claim that all gates passed.

## Stage Responsibilities

| Stage | Does | Produces | Done when |
|---|---|---|---|
| `warm_start_shared_space` | Create the initial shared conceptual space for autonomous research: diverse expert roles, grounded background evidence, an initial topic map, and a coverage baseline. | initial expert roster with stable expert identifiers, perspective-guided research transcript, evidence registry, and seeded knowledge map | At least two complementary expert perspectives are recorded.<br>The warm-start transcript contains grounded research turns.<br>The knowledge-map summary and coverage baseline are non-empty.<br>The evidence registry contains stable citation identifiers and source locators.<br>The shared space is ready for autonomous roundtable rotation. |
| `launch_expert_subagents` | Collect one grounded result and one distinct artifact for every expert before the Moderator makes a routing decision. | one grounded result and one distinct artifact for each expert | expert_results contains one result for every expert in expert_roster.<br>Every result has a non-empty grounded summary and a distinct artifact.<br>expert_round_index is exactly one greater than the last completed Moderator round.<br>The complete expert result set is ready for Moderator synthesis. |
| `autonomous_roundtable` | Advance the autonomous roundtable by exactly one moderated turn, preserving the shared transcript and evidence while deciding whether to continue, reorganize the knowledge map, or synthesize the report. | one Moderator synthesis turn over independent expert-subagent results, updated evidence and coverage, and an exclusive routing decision | Exactly one new grounded turn is added to the transcript.<br>The evidence registry and coverage map are carried forward or expanded.<br>round_index increases by one and remains within the configured autonomous budget.<br>round_decision and its boolean routing flags are mutually consistent.<br>The turn is ready for a continue, reorganize, or report transition. |
| `reorganize_knowledge_space` | Reorganize the shared knowledge map after a moderator-selected threshold so later expert turns can target gaps without losing evidence provenance. | expanded, deduplicated, and coverage-aware knowledge-map summary | The knowledge-map summary is materially updated or explicitly confirmed coherent.<br>Evidence provenance is preserved while redundant or unsupported branches are cleaned.<br>Coverage gaps remain visible for the next roundtable turn.<br>reorganization_count increases by one. |
| `synthesize_report` | Turn the reorganized shared knowledge space into a coherent report whose outline follows the map and whose claims remain traceable to the evidence registry. | structured report artifact with sections, inline citations, and a report summary | A report artifact exists.<br>The report has a clear outline with at least two substantive sections.<br>Inline numeric citations refer to the carried-forward evidence registry.<br>The report is ready for an independent quality and citation gate. |
| `verify_report` | Apply the final deterministic quality gate to the generated report and prove that its citations and sections are grounded in the shared evidence registry. | independent report quality verdict, citation coverage summary, and repair findings if needed | The report is read and checked against the evidence registry and coverage map.<br>quality_verdict is pass only when citation and section gates are satisfied.<br>Quality findings and the citation coverage summary are recorded.<br>The report is explicitly marked ready for finalization or repair. |
| `repair_report` | Translate report-audit findings into concrete repair actions so the report can be regenerated and rechecked without changing the research scope. | concrete report repair actions and a repaired-report handoff | The available audit or repair context is translated into concrete repair actions.<br>The repair handoff is ready for the report synthesis stage.<br>No unsupported new facts are introduced during repair. |
| `finalize_collaborative_report` | Finalize the autonomous Co-STORM research handoff. If {{report_path}} exists, {{quality_verdict}} is pass, and {{report_ready}} is true, return the validated report and include its summary ({{report_summary}}) and citation coverage ({{citation_coverage_summary}}). Otherwise, state that this is a partial handoff, do not claim validation, and include the available findings ({{quality_findings}}), repair summary ({{report_repair_summary}}), repair actions ({{repair_actions}}), and citation coverage ({{citation_coverage_summary}}). | Final workflow summary or handoff artifact. | Previous business stage completed successfully. |

## Maintenance Notes

- Keep this diagram aligned with `policy.py` and `graphbuilder_runtime.py`.
- If you add non-linear business gates, update `policy.py` and this diagram together.
- Keep repetitive repair edges summarized unless repair policy is the workflow's core behavior.
