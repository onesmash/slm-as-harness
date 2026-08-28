/research-nex {{workflow_goal}} using {{expert_roster}}, {{knowledge_map_summary}}, {{evidence_registry}}, {{coverage_map}}, and {{round_index}}; for every expert, delegate one independent subagent with its role-specific brief and the immutable shared-space snapshot, allow each subagent to retrieve new sources as unnumbered new_evidence, then merge those entries onto evidence_registry with contiguous global citation numbers and return the completed expert results for Moderator synthesis.

Stage Context:

- Expert roster with stable identifiers: {{expert_roster}}
- Current shared knowledge-map summary: {{knowledge_map_summary}}
- Current evidence registry: {{evidence_registry}}
- Current coverage map: {{coverage_map}}
- Carried-forward transcript: {{conversation_transcript}}
- Last completed round index: {{round_index}}
- Run constraints: {{constraints_json}}

Stage Boundaries:

- Delegate exactly one independent subagent for every expert in expert_roster; do not substitute one response for multiple experts.
- Give every subagent its role-specific brief and the same immutable shared-space snapshot; subagents must not read or coordinate through sibling outputs or assign global citation numbers.
- Each expert may retrieve new sources via research-nex/search-nex; return them as unnumbered new_evidence strings of the form source-locator — claim.
- Merge new_evidence in roster order into evidence_registry with the following deterministic algorithm: start from the persisted registry as the exact prefix; maintain a seen-locator set initialized from every persisted row's locator (the text before the first ' — ' separator, casefolded); for each expert's new_evidence in roster order, skip any item whose locator is already in the seen set (including duplicates introduced by later experts or repeated within one expert), otherwise append `[<next_id>] <item>` verbatim, add the locator to the seen set, and increment next_id starting at max(persisted id)+1. Return the full registry as persisted prefix plus those numbered entries; do not merge, abbreviate, or rewrite any item text.
- Return expert_round_index equal to the persisted {{round_index}} plus one, and do not exceed constraints.max_rounds.
- Return expert_results as objects with exactly expert_id, summary, artifact_path, and new_evidence fields.
- Every expert summary or artifact must cite at least one persisted or newly merged citation number, and no expert may cite unknown numbers or invent registry rows the merge did not produce. IMPORTANT: reference new_evidence items in the summary with their ASSIGNED numeric ids in the form [n] (e.g. '新证据引用：[25][26][27]'); bare locator strings are NOT recognized as citations. Keep at most 3 new_evidence items per expert unreferenced by the summary or artifact.
- Each expert may include at most three unused retrieved items that are not cited in that expert's summary or artifact; the merged registry must contain at most 128 entries.
- Keep expert results focused on the assigned perspective; the later Moderator stage makes the round decision.
- Do not request user participation, approval, or checkpoints.
- Do not build or persist a hierarchical knowledge graph in this stage.
- Compress expert payloads so graph_state serialization stays within runtime limits: keep every new_evidence claim (the part after the locator, never the locator itself) to at most 120 characters and never abbreviate or truncate the source locator, keep expert summaries under 800 characters, and keep per-expert artifacts focused on the assigned perspective.
- artifact_path must be a repository-relative path — no leading '/', no '\\', no '.' or '..' path segments — identifying a real, non-empty, non-symlink regular file inside the repository; never return absolute paths.

Blocked Conditions:

- Block when any expert result or artifact is missing.
- Block when results are duplicated, empty, or not grounded in the merged evidence registry.
- Block when newly retrieved evidence cannot be merged without rewriting the persisted registry prefix, skipping citation ids, duplicating locators, or exceeding the registry budget.
- Block when the next expert round would exceed the configured autonomous round budget.
