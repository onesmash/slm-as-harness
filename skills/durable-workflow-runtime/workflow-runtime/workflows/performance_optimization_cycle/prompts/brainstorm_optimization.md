/brainstorming-nex {{goal}} in {{repo_root}} using {{baseline_metrics}} and {{bottleneck_summary}}; generate, score, and shortlist testable, implementation-independent optimization hypotheses before research begins.

Stage Context:

- Repository root: {{repo_root}}
- Current goal: {{goal}}
- Performance diagnosis: {{performance_report_path}}
- Prior cycle summary: {{knowledge_base_update_summary}}

Stage Boundaries:

- Do not define the implementation change or modify source code.
- Do not prescribe .tmp/search_engine.py, .tmp/expL.py, or tools/ as required workflow inputs.

Blocked Conditions:

- Block when the optimization objective or measurable success criteria are not clear.
