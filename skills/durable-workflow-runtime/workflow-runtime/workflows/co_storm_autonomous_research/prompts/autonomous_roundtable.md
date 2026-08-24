/research-nex {{workflow_goal}} using {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, {{coverage_assessment}}, {{conversation_transcript}}, and {{expert_results}}; act as the Co-STORM Moderator over the completed expert results, synthesize one grounded roundtable turn, adjudicate semantic coverage topic by topic, record the next validation work, and return exactly one of continue, reorganize, or report.

Stage Context:

- Current expert roster: {{expert_roster}}
- Shared knowledge-map summary: {{knowledge_map_summary}}
- Evidence registry: {{evidence_registry}}
- Coverage map: {{coverage_map}}
- Prior semantic coverage assessment: {{coverage_assessment}}
- Prior next-round validation plan: {{next_round_validation_plan}}
- Conversation transcript: {{conversation_transcript}}
- Completed expert results: {{expert_results}}
- Current round index: {{round_index}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Do not request user participation or invent a user utterance; the Moderator owns autonomous question selection.
- Carry forward the persisted expert_roster records exactly as {id, role, brief}; do not collapse them back to strings or rewrite their briefs.
- Produce exactly one new research or moderation turn and preserve prior turns in the returned transcript.
- Return the structured decision flags and select exactly one of continue, reorganize, or report.
- The Moderator is the semantic authority for coverage. Return coverage_assessment records with exactly topic_id, status, evidence_refs, open_gaps, and next_validation_metrics; status must be covered, bounded_gap, or missing.
- Use each trimmed coverage_map topic verbatim as its stable topic_id, keep topic_id stable across rounds, and do not silently drop a warm-start or previously assessed topic. Cite evidence_refs only with identifiers present in evidence_registry.
- coverage_threshold is only a deterministic lower bound on the number of distinct assessed topics. Meeting it never proves semantic completion by itself.
- Set coverage_sufficient true only when the threshold guardrail is met, no topic is missing, every covered topic has evidence and no gaps or metrics, and every bounded_gap topic records evidence, open gaps, and measurable validation metrics. These are one-way eligibility guards: the Moderator may still judge a bounded gap material and keep coverage_sufficient false.
- When coverage_sufficient is false, return next_round_validation_plan as the exact set of `topic_id — metric` strings derived from every missing or materially unresolved bounded_gap topic. For report with complete scope, coverage_sufficient must be true and that plan must be empty.
- When max_rounds is reached with unresolved coverage, report is allowed only as report_scope_status=partial with coverage_sufficient=false and an explicit non-empty next_round_validation_plan; never present forced stopping as complete coverage.
- Cite only the already merged {{evidence_registry}}; do not assign new global citation numbers, rewrite persisted rows, or drop merged ids. Send new source retrieval back through another expert-result round.

Blocked Conditions:

- Block when the current knowledge map, expert roster, or evidence registry cannot be carried forward.
- Block when a grounded answer cannot be produced for the selected research action.
- Block when the round decision is ambiguous or more than one of continue, reorganize, and report is selected.
