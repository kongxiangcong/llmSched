# SPEC-16 Workspace Row Preset Actions Design

## Scope

This slice stays entirely inside the static catalog workspace compare table. We do not add new compare sections, new preset types, or any workbench behavior. Instead, we bring the new preset-backed compare workflow one step closer to the overview table by adding row-level preset actions.

The current state is close, but still split across two surfaces:

- the workspace table can jump directly to individual compare sections
- the focused workspace card can jump directly to common compare presets

That means users scanning the table still need to land in the focused card before they can switch from one-off section focus to a fuller preset-based workflow.

## Recommended Approach

Add a small row-level preset helper and wire it into the most natural cells:

- `Shared Metric Deltas` -> `grouped-vs-estimated-layer`
- `Sweep Layer Deltas` -> `summary-vs-estimated-layer`

This is intentionally not exhaustive. We should only add preset actions where the row context already strongly suggests the right follow-on analysis workflow.

## Interaction Model

The workspace overview remains scan-first. After this slice:

- row cells can still trigger direct section focus
- selected row cells can also trigger a richer preset-backed compare workflow
- both actions still resolve to the same focused workspace destination

Preset actions should clear any conflicting explicit section pairing and let the preset become the canonical active choice.

## Non-Goals

- No new presets
- No new columns
- No workbench preset routing
- No redesign of focused workspace card controls

## Verification Shape

This slice is complete when:

- generated catalog assets expose a row-level preset helper
- workspace row cells include preset-targeted focus actions
- preset continuity in focused workspace links/exports remains intact
- focused catalog unit, workflow, and smoke verification remain green
