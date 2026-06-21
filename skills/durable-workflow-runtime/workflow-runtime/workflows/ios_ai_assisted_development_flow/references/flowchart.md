# ios_ai_assisted_development_flow Flowchart

Developer-facing overview for `ios_ai_assisted_development_flow`.

The Mermaid diagram shows the durable route; the table below explains what each stage does.

```mermaid
flowchart TD
    start([start ios_ai_assisted_development_flow]) --> run_brainstorming[run_brainstorming]
    run_brainstorming -->|success| propose_openspec_change[propose_openspec_change]
    propose_openspec_change -->|success| refine_change_with_openspec[refine_change_with_openspec]
    refine_change_with_openspec -->|success| approve_refine[approve_refine]
    approve_refine -->|success| execute_implementation[execute_implementation]
    execute_implementation -->|success| run_agentic_release_qa[run_agentic_release_qa]
    run_agentic_release_qa -->|success| request_final_code_review[request_final_code_review]
    request_final_code_review -->|success| write_code_kb_feedback[write_code_kb_feedback]
    write_code_kb_feedback -->|success| finalize_delivery_summary([finalize_delivery_summary])
    run_brainstorming -->|verifier_failed| run_brainstorming[run_brainstorming]
    refine_change_with_openspec -->|ready_for_apply is_false| refine_change_with_openspec[refine_change_with_openspec]
    approve_refine -->|user_approved is_true| execute_implementation[execute_implementation]
    approve_refine -->|additional_refinement_needed is_true| refine_change_with_openspec[refine_change_with_openspec]
    run_agentic_release_qa -->|release_qa_verdict equals do_not_ship| execute_implementation[execute_implementation]
    request_final_code_review -->|changes_requested is_true| execute_implementation[execute_implementation]
    unblock_loop[[request_unblocking_input]]
    repair_loop[[repair_and_resume]]
    resume_target[[return_stage_id / originating stage]]
    run_brainstorming -.->|blocked| unblock_loop
    run_brainstorming -.->|partial / failed / verifier| repair_loop
    propose_openspec_change -.->|blocked| unblock_loop
    propose_openspec_change -.->|partial / failed / verifier| repair_loop
    refine_change_with_openspec -.->|blocked| unblock_loop
    refine_change_with_openspec -.->|partial / failed / verifier| repair_loop
    approve_refine -.->|blocked| unblock_loop
    approve_refine -.->|partial / failed / verifier| repair_loop
    execute_implementation -.->|blocked| unblock_loop
    execute_implementation -.->|partial / failed / verifier| repair_loop
    run_agentic_release_qa -.->|blocked| unblock_loop
    run_agentic_release_qa -.->|partial / failed / verifier| repair_loop
    request_final_code_review -.->|blocked| unblock_loop
    request_final_code_review -.->|partial / failed / verifier| repair_loop
    write_code_kb_feedback -.->|blocked| unblock_loop
    write_code_kb_feedback -.->|partial / failed / verifier| repair_loop
    unblock_loop -.->|resume via return_stage_id when present| resume_target
    unblock_loop -.->|stay when return_stage_id missing| unblock_loop
    repair_loop -.->|blocked| unblock_loop
    repair_loop -.->|retry via return_stage_id when repair succeeds| resume_target
    repair_loop -.->|partial / failed / missing return_stage_id| repair_loop
```

## Stage Responsibilities

| Stage | Does | Produces | Done when |
|---|---|---|---|
| `run_brainstorming` | Turn the user's iOS Client development goal into clarified requirements and an approved design before OpenSpec or implementation work begins. | clarified requirements, approved brainstorming design document, and design document path | Clarification questions and answer summary are recorded.<br>The user-approved design direction is recorded.<br>The approved brainstorming design document exists under docs/superpowers/specs/ and its path is included.<br>UI-impacting requests include implementation-ready visual detail and visual QA comparison inputs in the approved design document.<br>The spec review loop has completed with independent development, design, and testing perspective reviews. |
| `propose_openspec_change` | Create the OpenSpec change artifacts that make the approved design durable and implementation-ready. | OpenSpec proposal, design/spec, and tasks ready for implementation | The OpenSpec change directory exists.<br>Proposal, design/spec, and tasks artifacts are identified.<br>The change is apply-ready or the missing formalization inputs are reported. |
| `refine_change_with_openspec` | /openspec-explore {{change_name}} | refined OpenSpec artifacts ready for task execution | At least one exploratory conversation turn has occurred with the user.<br>Risks, ambiguities, and open questions have been surfaced and discussed.<br>Unresolved questions are documented (even if empty, with user confirmation).<br>The change is confirmed ready for apply after conversation. |
| `approve_refine` | Show the user what the OpenSpec refinement found, and get explicit approval before proceeding to implementation. | user approval to proceed from refinement to implementation | The user has reviewed the refinement summary.<br>The user has explicitly approved or rejected proceeding to implementation. |
| `execute_implementation` | Execute the pending OpenSpec tasks and leave the change ready for merged-final review. | completed OpenSpec task implementation with verification evidence | All selected OpenSpec implementation tasks are complete or the remaining blocked tasks are reported.<br>Changed files are summarized.<br>Verification commands and outcomes are reported. |
| `run_agentic_release_qa` | Run a release QA pass after implementation verification and before final merged-state review so regressions are caught before delivery closes. | change-aware release QA verdict with executed checks, blocked checks, and risk-based next steps | The QA pass identifies the code range or artifact under test.<br>Change-derived release risks are summarized.<br>Executed checks and blocked checks are reported separately.<br>The release QA verdict is ship, ship_with_risks, do_not_ship, or blocked.<br>Risk-based next steps are listed. |
| `request_final_code_review` | Review the final merged MR state, or block until an MR URL/snapshot is available, after implementation and release QA have completed. | merged-final review findings and merge-safety decision | Review snapshot is identified.<br>Findings are grouped by severity or explicitly reported as none.<br>The review status is approved, changes_requested, or blocked. |
| `write_code_kb_feedback` | Preserve reusable learning from the completed change by updating Code KB surfaces or explicitly recording why no KB update is needed. | knowledge-base page/backlog/QA feedback updates for the completed change | Knowledge-base updates are listed, or a skipped reason is provided.<br>Backlog or QA feedback changes are summarized when applicable.<br>Formatting or hygiene checks are reported when page updates were written. |
| `finalize_delivery_summary` | Prepare the final iOS Client AI-assisted development delivery summary. Include the approved design, OpenSpec change artifacts, implementation evidence, release QA verdict {{release_qa_verdict}}, release QA summary {{release_qa_summary}}, release QA executed checks {{release_qa_executed_checks}}, release QA blocked checks {{release_qa_blocked_checks}}, release QA risk next steps {{release_qa_risk_next_steps}}, review decision, knowledge-base feedback, remaining risks, and tests or checks run. | Final workflow summary or handoff artifact. | Previous business stage completed successfully. |

## Maintenance Notes

- Keep this diagram aligned with `policy.py` and `graphbuilder_runtime.py`.
- If you add non-linear business gates, update `policy.py` and this diagram together.
- Keep repetitive repair edges summarized unless repair policy is the workflow's core behavior.
