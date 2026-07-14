/performance-nex diagnose {{goal}} in {{repo_root}}; establish the performance baseline, identify the dominant bottleneck, and produce a report that can constrain optimization ideation.

Stage Context:

- Repository root: {{repo_root}}
- Optimization goal: {{goal}}

Stage Boundaries:

- Do not modify source code or select an implementation approach.
- Separate measured evidence from assumptions and missing telemetry.

Blocked Conditions:

- Block when the target system, available measurements, or performance objective cannot be identified.
