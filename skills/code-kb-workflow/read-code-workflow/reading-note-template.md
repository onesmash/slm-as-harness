# Reading Note Template

Use this template when producing the final artifact for a code-reading session.

## 1. Reading Goal

- Primary question:
- Goal mode:
- Scope:
- Time or depth limit:

## 2. Environment Status

- Can the project be built or run?
- What was actually executed?
- What was only read statically?
- What environment simplifications were made?

## 3. High-Level Map

| Component | Responsibility | Why it matters |
| --- | --- | --- |
|  |  |  |

## 4. Main Storyline

1. Entrypoint:
2. Major calls:
3. Data transformations:
4. State transitions:
5. External boundaries:
6. Success path:
7. Failure path:

## 5. Parked Side Plots

- What was intentionally treated as a black box?
- What interface or contract is known about it?
- Why was it deferred?

## 6. Core Data Structures

| Structure | Represents | Created by | Mutated in | Consumed by | Notes |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## 7. Tests and Scenarios

- Most useful tests to read:
- Happy-path scenario:
- Boundary scenario:
- Failure scenario:

## 8. Open Questions

- What remains uncertain?
- What should be verified next by running code, tracing, or reading tests?

## 9. Confidence

- High / Medium / Low
- Why:

## 10. Reading Memo

Write a short explanation that another engineer could read quickly.

Recommended shape:

- One paragraph on the system shape.
- One paragraph on the main execution path.
- A short list of the most important data structures.
- A short list of remaining questions or risks.
