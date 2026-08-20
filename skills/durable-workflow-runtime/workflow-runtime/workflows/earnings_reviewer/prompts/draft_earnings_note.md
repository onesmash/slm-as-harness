/morning-note {{ticker}} {{reporting_period}} using {{variance_rows}}, {{call_analysis_summary}}, {{estimate_change_summary}}, and {{audit_summary}}; draft the post-earnings note as a staged draft for senior-analyst markup and do not publish.

Stage Context:

- Ticker: {{ticker}}
- Reporting period: {{reporting_period}}
- Updated model: {{updated_model_path}}
- Headline read: {{headline_read}}
- Beat/miss: {{beat_miss_summary}}
- Call analysis: {{call_analysis_summary}}
- Variance rows: {{variance_rows}}
- Estimate changes: {{estimate_change_summary}}
- Audit summary: {{audit_summary}}
- Thesis impact: {{thesis_impact}}
- Unsourced flags: {{unsourced_flags}}
- Model-builder handoff: {{handoff_target}} / {{handoff_reason}}

Stage Boundaries:

- Stage the note as a draft; never publish or distribute externally.
- Include the variance table for Revenue, GM, EBITDA, and EPS.
- Cite every number or mark it [UNSOURCED].
- Do not treat this draft as a rating or investment recommendation.
- If a model-builder handoff is pending, do not present DCF or price-target changes as final.
- Write the note under out/.

Blocked Conditions:

- Block if the audited model, variance table, or call analysis is missing.
