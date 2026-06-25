# Custom Verifier Self-Contained Review Contract Design

## Summary

`durable-workflow-runtime` currently preserves hand-written
`custom_verifier_requirement` function bodies at requirement granularity when
their generator metadata still matches the current `spec.json`.

That preservation model works well for self-contained verifier functions, but
it breaks down when a preserved custom verifier depends on extra local helpers
defined in `verifiers.py`. Those helpers are generator-owned file content and
can be removed on regeneration, leaving the preserved verifier body referring
to code that no longer exists.

This design resolves the problem by tightening the authoring and review
contract instead of adding more generator complexity:

- A preserved custom verifier function must be self-contained.
- If a verifier needs reusable logic, it may depend only on stable shared
  modules imported into `verifiers.py`.
- Custom verifiers must not depend on extra local helpers defined in
  `verifiers.py`.
- The generator keeps its current requirement-level preservation behavior.
- The workflow authoring and review surfaces explicitly warn against local
  helper dependencies and require reviewers to check for them.

## Problem

Today the generator preserves individual
`_custom_verifier_requirement_<stage>_<requirement>()` functions when the
requirement contract is unchanged.

That preservation assumes the function body is the only hand-written unit that
matters. In practice, an author may factor verifier logic into additional
top-level helpers inside `verifiers.py` and call them from the preserved custom
verifier function.

This creates a mismatch in ownership:

- the requirement function body is treated as preservable author code,
- but the extra local helper is not part of the preserved unit and is therefore
  vulnerable to regeneration churn.

The result is a fragile workflow:

- the author believes the verifier implementation has been preserved,
- regeneration removes or rewrites the local helper,
- the preserved verifier body can become invalid or incomplete,
- and the failure appears later than the original authoring decision.

## Goals

- Keep the current requirement-level preservation model simple and predictable.
- Make the safe authoring boundary for custom verifiers explicit.
- Prevent silent reliance on `verifiers.py` local helpers that are not
  preservation-safe.
- Push reusable verifier logic into stable shared modules instead of generator-
  owned local helper regions.
- Add reviewer guidance so this class of issue is caught before workflows are
  treated as shipped.

## Non-Goals

- Do not add helper dependency tracking to the generator.
- Do not preserve arbitrary top-level helper functions in `verifiers.py`.
- Do not introduce AST-based hard validation or preservation invalidation in
  this change.
- Do not redesign the existing requirement-level metadata preservation model.
- Do not require a bulk migration of all existing workflows before future
  regeneration.

## Recommended Approach

Adopt a documentation and review contract:

1. Treat each generated
   `_custom_verifier_requirement_<stage>_<requirement>()` function as the only
   preservable authoring unit in `verifiers.py`.
2. Require that function to be self-contained by default.
3. Allow reusable logic only through imports from stable shared modules that
   are outside generator-owned `verifiers.py` content.
4. Explicitly prohibit adding or depending on extra top-level local helpers in
   `verifiers.py` for custom verifier logic.
5. Update generator-authored scaffold guidance and author-review guidance to
   call this out directly.
6. Make reviewer sign-off responsible for checking that custom verifier logic
   follows this boundary.

This solves the observed failure mode without making regeneration rules harder
to understand or maintain.

## Alternatives Considered

### Option A: Preserve custom verifier local helpers too

Rejected for now. This would require defining helper ownership, mapping helper
functions to requirements, and handling ambiguous or shared local helper usage.
That increases generator complexity and weakens the clean boundary between
generated file structure and preserved author code.

### Option B: Add AST-based invalidation for local helper usage

Rejected for now. It is feasible, but it adds implementation and maintenance
complexity that is not justified for the current need. It also introduces edge
cases around builtin detection, import alias handling, and local symbol
resolution that are avoidable if review contract is sufficient.

### Option C: Externalize all custom verifier implementations into separate
modules

Deferred. This is a strong long-term option, but it is a larger structural
change than needed here. The current need can be addressed by clarifying
authoring boundaries while keeping the existing generation shape intact.

## Authoring Contract

### Preservable Unit

Within `verifiers.py`, the only hand-written unit that the regeneration model
promises to preserve is the generated requirement-scoped function:

```python
def _custom_verifier_requirement_<stage>_<requirement>(...) -> str | None:
    ...
```

No other hand-written top-level function in `verifiers.py` is considered a
preservation-safe extension point.

### Allowed Dependencies

Each custom verifier function should prefer inline logic inside its own body.

If the logic is too complex to remain comfortably self-contained, the function
may depend on stable shared modules by importing them into `verifiers.py`.

Allowed patterns:

- direct self-contained checks implemented in the requirement function body
- calls to Python builtin functions
- calls to symbols imported from stable shared modules

### Disallowed Dependencies

A custom verifier function must not depend on:

- extra top-level helper functions authored directly in `verifiers.py`
- other `_custom_verifier_requirement_*` functions
- local wrapper functions that indirectly hide shared logic inside the same
  generated file

This prohibition applies even if the helper seems harmless or is currently used
by only one requirement. The key issue is ownership: those helpers are not part
of the generator's preservation guarantee.

### Escalation Rule for Complex Logic

If a verifier implementation becomes too large or repetitive for one function,
the author should move the reusable logic into a stable shared module instead
of growing `verifiers.py`-local helper layers.

This keeps `verifiers.py` aligned with the generator's preservation model and
makes reuse explicit and durable across regenerations.

## Generator Behavior

This design intentionally keeps generator behavior simple:

- requirement-level preservation logic remains unchanged
- `stage_id`, `requirement_id`, `template_version`,
  `spec_fingerprint`, and `implementation_version` remain the preservation
  inputs
- regeneration continues to preserve only requirement-scoped custom verifier
  functions
- regeneration does not attempt to preserve or reconstruct extra local helpers
  in `verifiers.py`

The generator does not become responsible for tracking local helper
dependencies. Instead, the workflow authoring contract makes those dependencies
invalid by convention.

## Documentation Changes

The generated scaffold and authoring references should state the boundary
clearly.

### `verifiers.py` Scaffold Guidance

Each generated custom verifier scaffold should include a short note that says
the implementation:

- should stay self-contained when practical
- may call stable imported shared-module helpers when necessary
- must not introduce or depend on `verifiers.py`-local top-level helpers,
  because those helpers are not preserved across regeneration

### Workflow Authoring Guidance

The workflow authoring guide should add explicit wording that
`custom_verifier_requirements` are preserved only at the requirement-function
level, and that any shared logic should live outside `verifiers.py`.

### Agent Review Guidance

The workflow review guidance should add an explicit custom verifier check:

- verify that preserved custom verifier logic is self-contained or uses stable
  imported shared modules
- verify that no custom verifier depends on `verifiers.py`-local helper
  functions
- if complex logic is present, verify that the reuse boundary is implemented in
  a stable shared module instead of the generated file

## Review Contract

Because this change relies on documentation and review rather than generator
enforcement, reviewer guidance must be concrete.

The review checklist should treat the following as blocking issues:

- a custom verifier calls a top-level helper defined in `verifiers.py`
- a custom verifier indirectly relies on same-file wrapper layers
- repeated local helper extraction was used when the logic should have been
  inlined or moved into a shared module

The review checklist should treat the following as acceptable:

- a custom verifier with a longer but understandable inline implementation
- a custom verifier that imports and calls a stable shared-module helper

The goal is not to force tiny functions. The goal is to keep the preservation
boundary clear and durable.

## Migration Strategy

This change should be forward-looking and non-disruptive.

- Do not run a one-time mass migration across all existing workflows.
- Apply the new guidance to newly generated and newly reviewed workflows.
- When an existing workflow is regenerated in the future, any custom verifier
  still relying on same-file local helpers should be corrected during the
  normal authoring or review pass.

This keeps the rollout lightweight while still improving future workflow
quality.

## Validation and Testing

Testing for this design should focus on documentation and scaffold coverage
rather than new static analysis behavior.

Recommended coverage:

1. Generator tests confirm the scaffold text for custom verifier requirements
   includes the self-contained/shared-module/local-helper warning.
2. Authoring guide or review artifact tests confirm the review checklist
   includes a custom verifier dependency boundary check.
3. Existing preservation tests remain unchanged, confirming this design does
   not alter preservation semantics.

## Risks

- Review-only enforcement is weaker than generator-enforced validation and can
  miss violations if reviewers are inattentive.
- Some authors may initially prefer helper extraction inside `verifiers.py`
  because it feels locally convenient.
- Without tooling, a workflow can still regress if the contract is ignored.

These risks are acceptable because the design intentionally favors simplicity
over more sophisticated regeneration logic. If review-based enforcement proves
insufficient later, the project can add targeted static analysis as a follow-up
change without undoing the authoring boundary defined here.

## Decision

Adopt a self-contained custom verifier authoring contract with review-driven
enforcement:

- preserve requirement-scoped custom verifier functions only
- allow reuse only through stable imported shared modules
- prohibit `verifiers.py`-local helper dependencies
- communicate the rule in scaffold text, authoring docs, and review guidance
- keep generator preservation logic unchanged
