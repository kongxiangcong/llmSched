# SPEC-16 Workspace Analysis Flows Design

## Scope

This slice stays entirely inside the static catalog workspace compare flow. We do not add new compare sections or new compare presets. Instead, we add a thin user-intent layer above the preset system so common analysis tasks have stable names and direct links.

The current preset layer is functional, but still phrased in structural terms such as `summary-vs-estimated-layer`. That is useful for implementation, but less natural for day-to-day analysis than intent-oriented names like "summary hotspots" or "memory regression."

## Recommended Approach

Add one optional state key, `workspace_analysis_flow`, that maps directly to existing presets. A small initial set is enough:

- `summary-hotspots` -> `summary-vs-estimated-layer`
- `grouped-hotspots` -> `grouped-vs-estimated-layer`
- `memory-regression` -> `pressure-vs-fitted-layer`

The analysis-flow layer should only do three things:

- set a preset implicitly
- show a friendly label in the focused workspace card and export metadata
- expose direct analysis-flow links alongside the existing preset links

This keeps the implementation additive and low-risk while making the compare workflow feel more like a product surface and less like internal state wiring.

## Non-Goals

- No new compare sections
- No new preset combinations
- No workbench routing changes
- No replacement of explicit preset or section state

## Verification Shape

This slice is complete when:

- generated catalog assets expose `workspace_analysis_flow`
- focused workspace helpers can resolve flows into existing presets
- export metadata preserves the active analysis flow
- focused catalog unit, workflow, and smoke verification remain green
