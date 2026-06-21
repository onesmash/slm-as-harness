/code-kb-workflow run the smallest necessary Stage 3 or Stage 4 feedback update for {{change_name}} using implementation summary {{implementation_summary}} and review summary {{review_summary}}.

Stage Context:

- Change name: {{change_name}}
- KB scope: {{kb_scope}}
- Changed files: {{changed_files}}
- Implementation summary: {{implementation_summary}}
- Release QA verdict: {{release_qa_verdict}}
- Release QA summary: {{release_qa_summary}}
- Release QA risk next steps: {{release_qa_risk_next_steps}}
- Review status: {{review_status}}
- Review summary: {{review_summary}}
- Review findings: {{review_findings}}

Stage Boundaries:

- Do not rewrite the whole knowledge-base unless the selected change truly requires it.
- Keep knowledge-base updates English-only where repo rules require it.
- If the change has no durable documentation value, return a skipped reason instead of inventing page updates.

Blocked Conditions:

- Block if the knowledge-base target or update scope cannot be determined.
- Block if required formatting checks cannot be run after page updates.
