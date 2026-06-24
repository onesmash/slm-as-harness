# Custom Verifier Requirements Incremental Regeneration Design

## Summary

`durable-workflow-runtime/workflow-creator/scripts/create_workflow.py` currently regenerates `verifiers.py` scaffolds from `workflow-runtime/workflows/<workflow_id>/spec.json`.

For `stages[].custom_verifier_requirements`, this causes a workflow author to reapply hand-written verifier logic after rerunning `create_workflow.py --force`, even when the requirement definition in `spec.json` has not changed.

This design adds requirement-level incremental regeneration for custom verifier scaffolds:

- If a `custom_verifier_requirement` definition is unchanged, preserve the existing hand-written verifier function body.
- If the requirement definition changes, regenerate that function's scaffold.
- If a requirement is added or removed, add or remove only the matching function.

## Problem

Today `custom_verifier_requirements` generate scaffold functions in `verifiers.py` with TODO bodies. Those functions are intended to be completed by a human during workflow authoring and review.

When the workflow is regenerated from `spec.json`, unchanged custom verifier requirements should not force the author to manually recreate the same implementation again. The generator should treat `spec.json` as the source of truth for when regeneration is necessary, but preserve verifier implementations when the relevant requirement contract is unchanged.

## Goals

- Preserve hand-written custom verifier implementations when the corresponding `custom_verifier_requirement` is unchanged in `spec.json`.
- Make regeneration decisions at individual requirement granularity, not whole-file granularity.
- Keep `spec.json` as the long-lived workflow blueprint.
- Keep generator behavior deterministic and easy to review in git diffs.
- Allow an explicit escape hatch to force scaffold regeneration when desired.

## Non-Goals

- Do not preserve arbitrary edits outside generated custom verifier requirement functions.
- Do not infer semantic equivalence from function body changes.
- Do not automatically migrate implementations across requirement renames.
- Do not change the meaning of `custom_verifier_requirements`; this is a regeneration-behavior improvement only.

## Recommended Approach

Use a hybrid requirement-level preservation model:

1. Compute a stable `spec_fingerprint` for each `custom_verifier_requirement`.
2. Optionally support an explicit `implementation_version` field in the requirement spec.
3. Track a generator-controlled `custom_verifier_template_version` so template-shape changes can invalidate preserved functions safely.
4. Embed requirement metadata directly above each generated custom verifier function in `verifiers.py`.
5. On regeneration, preserve an existing function body only when:
   - the same `stage_id` and `requirement_id` still exist,
   - the stored template version matches the generator's current template version,
   - the stored `spec_fingerprint` matches the newly computed fingerprint,
   - and `implementation_version` also matches when present.
6. Otherwise regenerate the scaffold for that requirement.

This balances automation with control:

- unchanged requirements keep hand-written code,
- changed requirements become visibly invalidated,
- generator template changes invalidate preserved bodies safely,
- authors can explicitly force regeneration even when textual content is otherwise stable.

## Alternatives Considered

### Option A: Preserve by `requirement.id` only

Rejected. This can silently retain stale implementations after the requirement contract changes in `spec.json`.

### Option B: Use only manual versioning

Rejected as the default. It is simple but depends on authors remembering to bump a version field whenever requirement content changes.

### Option C: Store preservation metadata in a separate lock file

Rejected. This creates a second long-lived state surface that can drift from `verifiers.py`.

## Spec Changes

### `spec.json`

Extend each `custom_verifier_requirement` object to optionally support:

```json
{
  "id": "require_visual_diff_summary",
  "description": "Verify the implementation stage records visual diff evidence when UI changed.",
  "implementation_version": 1
}
```

`implementation_version` is optional. If omitted, preservation depends only on the fingerprint derived from the normalized requirement content.

Within a single stage, every `custom_verifier_requirement.id` must already be unique. Regeneration should continue to rely on that uniqueness and must hard-fail if two requirements in the same stage would normalize to the same generated function identity.

### Fingerprint Inputs

The `spec_fingerprint` should be computed from a normalized JSON representation of:

- `id`
- `description`
- `signals`
- `implementation_surface`
- `implementation_notes`
- `hint_pseudocode`
- `test_intent`
- a stage-contract context digest derived from the current stage's verifier-relevant contract:
  - `step_id`
  - `output_schema`
  - verifier helper function signature contract for custom requirements
  - any generator-owned calling convention data needed by the requirement function

The normalization rules should:

- use stable key ordering,
- treat missing and `null` optional fields as equivalent,
- trim leading and trailing whitespace for scalar strings before hashing,
- preserve list order for `signals`, `implementation_surface`, `hint_pseudocode`, and `test_intent`,
- omit fields not present in the requirement after null-equivalence normalization,
- and produce the same fingerprint for semantically identical serialized content.

`implementation_version` should not be part of `spec_fingerprint`; it is a separate explicit invalidation mechanism.

Editorial guidance:

- Fields that directly describe verifier behavior or expected checks are semantic and should participate in invalidation.
- Pure wording changes that are intentionally non-semantic should either be avoided in hashed fields or paired with an unchanged semantic field structure so author expectations stay clear.
- Because `description`, `implementation_notes`, and `hint_pseudocode` can affect intended verifier behavior, changing them is treated as a semantic change unless the design is later narrowed explicitly.

## Template Version

The generator must own a `custom_verifier_template_version` constant for requirement preservation.

This version should change whenever the generated custom verifier function contract changes in a way that could make preserved bodies unsafe, including:

- function signature changes,
- return-value contract changes,
- required imports or helper dependencies,
- runner invocation contract changes,
- or other template-shape changes that preserved bodies must opt into deliberately.

## Generated Code Shape

Each generated custom verifier requirement function in `verifiers.py` should include requirement metadata directly above the function:

```python
# custom_verifier_stage_id: execute_implementation
# custom_verifier_requirement_id: require_visual_diff_summary
# template_version: 1
# spec_fingerprint: 8f3c0d...
# implementation_version: 1
def _custom_verifier_requirement_execute_implementation_require_visual_diff_summary(
    *,
    output: dict,
    state: dict | None,
    repo_root: str,
) -> str | None:
    ...
```

If `implementation_version` is absent from the requirement spec, the generated metadata should record a neutral value such as `none`.

The metadata key format must avoid ambiguous concatenation. The persisted identity should either:

- store `stage_id` and `requirement_id` in separate metadata lines, or
- use a lossless encoded representation that cannot be confused by valid identifier characters.

The implementation should prefer separate metadata lines for simplicity and parser safety.

## Regeneration Algorithm

When regenerating `verifiers.py`:

1. Parse the existing file and extract any existing generated custom verifier requirement function blocks, keyed by:
   - `stage_id`
   - `requirement_id`
2. For each extracted block, read:
   - stored template version
   - stored `spec_fingerprint`
   - stored `implementation_version`
   - full function source
3. Compute the new requirement map from `spec.json`.
4. For each current requirement:
   - If no prior block exists, generate a new scaffold.
   - If prior metadata exists and template version, fingerprint, and implementation version all match, reuse the prior function source verbatim.
   - If template version, fingerprint, or implementation version differ, generate a fresh scaffold.
5. Omit blocks whose requirements no longer exist in `spec.json`.

This preservation should apply only to the requirement-scoped helper functions, not to the surrounding runner function `_run_custom_verifier_requirements_<step_id>`, which can continue to be fully regenerated from spec.

If an existing function block is not safely parseable, has missing or partial metadata, or maps ambiguously to more than one current requirement, the generator must not silently preserve it. It should regenerate the affected scaffold and emit a clear warning that hand-written logic was not preserved automatically.

## Parser Contract

The preservation parser should operate on generated top-level custom verifier helper functions only.

- Metadata comments must appear immediately above the target `def`.
- Decorators are not supported on preservable generated requirement functions.
- The function block ends at the next top-level `def` or end-of-file.
- Top-level comments or blank lines between metadata and `def` make the block non-preservable.
- Unexpected top-level statements inside the generated custom verifier region must cause that block to be treated as non-preservable rather than best-effort parsed.
- The parser should prefer a structured Python parse strategy when practical; if a text parser is used, it must follow the same strict block-boundary rules.

## Identifier and Naming Rules

- `stage_id` already follows the workflow creator's Python identifier validation rules and remains the stage identity key.
- `custom_verifier_requirement.id` must be validated as a Python-safe identifier for generated helper naming, or else the generator must reject the spec with a hard error before writing files.
- The generated function identity must be injective: two distinct requirements must never normalize to the same helper function name or metadata identity.
- Any collision in stage/requirement identity or generated helper naming must hard-fail regeneration.

## Edge Cases

### Added requirement

Generate a new scaffold function for the new requirement only.

### Removed requirement

Remove the corresponding function from generated output.

The generator should also emit an explicit notice that the preserved implementation for that requirement was removed because the requirement no longer exists in `spec.json`.

### Renamed requirement

Treat as delete plus add. Do not attempt automatic migration.

The generator should emit an explicit notice that the old implementation was discarded because the requirement identity changed.

### Unchanged requirement, hand-written function body changed

Preserve the hand-written function body. The preservation decision is based on the requirement contract, not on whether the body still matches the original scaffold.

### Changed requirement, same `id`

Invalidate preservation and regenerate scaffold for that requirement.

### Forced regeneration without content change

If the author increments `implementation_version`, regenerate the scaffold even when the fingerprint is unchanged.

### Template version changed

If `custom_verifier_template_version` changes, all requirement-scoped preserved custom verifier helper functions become non-preservable and are regenerated.

## Validation and Testing

Add generator-level tests covering:

1. Initial generation writes metadata and scaffold functions for custom verifier requirements.
2. Regeneration preserves a hand-written function body when requirement content is unchanged.
3. Regeneration replaces the hand-written body with a scaffold when requirement content changes.
4. Regeneration adds only newly introduced requirement functions.
5. Regeneration removes functions for deleted requirements.
6. Regeneration forces scaffold replacement when `implementation_version` changes.
7. Regeneration forces scaffold replacement when `custom_verifier_template_version` changes.
8. Existing `verifiers.py` files without preservation metadata follow an explicit upgrade path: no preservation occurs, scaffolds are regenerated, and the generator emits a clear warning.
9. Partially missing or malformed metadata causes warning plus safe non-preservation, never silent best-effort reuse.
10. Duplicate requirement ids or generated helper naming collisions hard-fail regeneration.
11. Parser boundary tests cover consecutive generated functions, file-end functions, unsupported decorators, and unexpected top-level statements near preservable blocks.
12. Fingerprint normalization tests cover missing-versus-null equivalence, scalar string trimming, and ordered-list stability for the hashed requirement fields.

## Risks

- Fingerprint coverage that is too narrow could preserve stale implementations when important requirement meaning changes.
- Fingerprint coverage that is too broad could trigger unnecessary regeneration for purely editorial changes.
- Parsing and preserving function blocks from existing `verifiers.py` must be strict enough to avoid preserving the wrong block.
- Generator template evolution can silently invalidate preserved bodies unless template versioning is enforced consistently.

## Open Implementation Notes

- Keep the preservation parser intentionally narrow: it only needs to recognize generated custom verifier metadata headers and the immediately following function block.
- Prefer preserving exact source text for matching functions rather than reconstructing AST nodes. This keeps user formatting and comments intact inside preserved functions.
- If an existing function is missing required metadata, treat it as non-preservable, regenerate the scaffold, and surface a warning.
- The generator output should summarize preservation decisions so authors can see which requirement functions were preserved, regenerated, newly added, or removed.

## Success Criteria

The design is successful when rerunning `create_workflow.py --force` no longer causes authors to manually recreate unchanged `custom_verifier_requirements` implementations, while still making changed verifier contracts clearly visible and safely regenerable.
