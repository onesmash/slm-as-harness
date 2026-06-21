/openspec-explore {{change_name}}

Stage Boundaries:

- This stage REQUIRES conversational exploration with the user before filling structured_output.
- Do NOT skip the /openspec-explore conversation loop. Talk through risks, open questions, and design ambiguities with the user first.
- Only after at least one user-agent conversation turn about findings, populate structured_output.
- You must surface at least 2-3 substantive questions or risks to the user for discussion.
- Empty unresolved_questions[] is valid ONLY if the user explicitly confirmed no open issues after discussion.
- Do not treat structured_output field requirements as a checklist to fill without conversation.
- Do not choose the next workflow stage; runtime policy owns routing.
- Do not implement code or modify OpenSpec artifacts during this stage.

Blocked Conditions:

- Block if you have not had at least one conversational exchange with the user about the artifacts before completing this stage.
- Block if unresolved_questions is empty but you never asked the user about potential issues.
- Block if you presented a mechanical checklist instead of conversational exploration.
- Block if refinement reveals an unresolved product or architecture decision without user discussion.
- Block if the OpenSpec artifacts are missing or inconsistent.
- Block if the agent attempts to apply or implement code changes.
- If required input, approval, credentials, files, or decisions are missing, return blocked instead of inventing them.
