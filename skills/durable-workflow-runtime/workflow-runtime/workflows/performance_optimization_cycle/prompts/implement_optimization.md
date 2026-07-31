/subagent-driven-development implement {{planned_change_summary}} from {{research_brief_path}} in {{repo_root}} using {{verification_plan}}; use isolated task implementers and reviewers, run python tests/submission_tests.py, and return changed paths and verification evidence. Follow /systematic-debugging before any fix when tests or verification fail.

Stage Context:

- Success criteria: {{success_criteria}}
- Research evidence: {{evidence_summary}}
- Open risks: {{open_risks}}
- Research-defined change: {{planned_change_summary}}
- Research-defined verification: {{verification_plan}}

Stage Boundaries:

- Never modify anything under tests/.
- Keep N_CORES=1.
- Do not substitute .tmp/search_engine.py, .tmp/expL.py, or tools/ for submission testing.

Blocked Conditions:

- Block if the researched change or submission tests cannot run.
