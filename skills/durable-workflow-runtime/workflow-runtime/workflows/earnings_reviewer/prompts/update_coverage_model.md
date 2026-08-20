/model-update {{ticker}} {{reporting_period}} using {{coverage_model_path}}, {{earnings_packet_path}}, and {{call_analysis_summary}}; write the updated workbook under out/ with the required variance table, and emit a model-builder handoff_request in structured output when a DCF rebuild is required.

Stage Context:

- Ticker: {{ticker}}
- Reporting period: {{reporting_period}}
- Existing coverage model: {{coverage_model_path}}
- Earnings packet: {{earnings_packet_path}}
- Call analysis: {{call_analysis_summary}}
- Beat/miss: {{beat_miss_summary}}
- Guidance changes: {{guidance_changes}}
- Thesis impact: {{thesis_impact}}
- Skip note: {{skip_note}}
- Unsourced flags: {{unsourced_flags}}

Stage Boundaries:

- Do not draft the earnings note in this stage.
- Do not start a DCF rebuild inside this workflow; if the thesis change requires one, set requires_model_builder_handoff true and emit handoff_target model-builder with a payload.
- The variance table must cover Revenue, GM, EBITDA, and EPS versus consensus and prior estimate.
- Every changed cell must be traceable to FactSet, Daloopa, a filing, or the transcript; otherwise mark [UNSOURCED].
- Write the updated workbook under out/.
- Echo skip_note from workflow state.
- Do not publish or post the model.

Blocked Conditions:

- Block if the coverage model cannot be opened or created.
- Block if actuals cannot be reconciled to the company's reported figures before projecting forward.
