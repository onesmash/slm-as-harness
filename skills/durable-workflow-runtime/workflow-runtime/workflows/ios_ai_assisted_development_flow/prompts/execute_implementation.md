/openspec-apply-change {{change_name}}

Stage Context:

- Change name: {{change_name}}
- Change path: {{change_path}}
- Proposal path: {{proposal_path}}
- OpenSpec design path: {{openspec_design_path}}
- Tasks path: {{tasks_path}}
- Refinement summary: {{refinement_summary}}
- Refinement discussion summary: {{refinement_user_discussion_summary}}

Stage Boundaries:

- Keep edits scoped to the OpenSpec tasks.
- Do not mark tasks complete until the corresponding implementation work is done.
- If implementation exposes an OpenSpec or design issue, return enough structured detail to route back into refinement instead of improvising around the spec gap.
- Do not commit, push, or create an MR unless the user separately asks for it.
- Leave the change in a state that can be inspected by the later pre-merge code review using the local diff, branch state, and recorded verification evidence.

Blocked Conditions:

- Block if a task is ambiguous.
- Block if implementation reveals a design issue that requires OpenSpec artifact updates.
- Block if verification cannot run because a required environment dependency is unavailable.
