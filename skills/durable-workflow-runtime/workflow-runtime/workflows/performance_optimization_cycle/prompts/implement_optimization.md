/subagent-driven-development implement {{planned_change_summary}} using {{implementation_plan_path}} in {{repo_root}}; use isolated task implementers and reviewers, run python tests/submission_tests.py, and return changed paths and verification evidence.

Stage Context:

- Success criteria: {{success_criteria}}
- Research evidence: {{evidence_summary}}

Stage Boundaries:

- Never modify anything under tests/.
- Keep N_CORES=1.
- Do not substitute .tmp/search_engine.py, .tmp/expL.py, or tools/ for submission testing.

Blocked Conditions:

- Block if the implementation plan is missing or submission tests cannot run.
