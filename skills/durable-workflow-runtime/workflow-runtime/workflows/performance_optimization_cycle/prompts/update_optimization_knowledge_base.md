/code-kb-workflow update the optimization knowledge base in {{repo_root}} using {{research_brief_path}}, {{implementation_summary}}, and {{review_summary}}; record durable findings and decide whether another brainstorm iteration is required.

Stage Context:

- Review findings: {{review_findings}}
- Submission-test evidence: {{submission_test_output}}

Stage Boundaries:

- Use the smallest Code KB stage that updates the affected durable artifacts.
- Do not rewrite the entire knowledge base unless the evidence requires it.

Blocked Conditions:

- Block if review approval or implementation evidence is missing.
