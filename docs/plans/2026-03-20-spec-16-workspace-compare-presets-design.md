# SPEC-16 Workspace Compare Presets Design

## Scope

This slice stays entirely inside the static catalog workspace compare drill-down. We do not add new compare sections, change compare payloads, or redesign the focused workspace card. Instead, we add a thin preset layer above the existing primary-plus-secondary section state.

The current dual-section workflow is expressive, but still a little manual. Users now have to pick both `workspace_detail_focus` and `workspace_secondary_detail_focus` themselves, even though the same pairings are likely to recur during analysis.

## Recommended Approach

Add one optional state key, `workspace_detail_preset`, whose only job is to set well-known section pairs. The preset layer should stay tiny and opinionated. A good initial set is:

- `summary-vs-estimated-layer`
- `grouped-vs-estimated-layer`
- `pressure-vs-fitted-layer`

Choosing a preset should set:

- `workspace_detail_focus`
- `workspace_secondary_detail_focus`

without changing any underlying compare content. The focused workspace card can display the active preset name in metadata/export output, but rendering should still be driven by the section ids so the preset layer stays strictly additive.

## Interaction Model

The focused workspace card remains the destination. Presets are shortcuts, not a new compare mode:

- users can still deep-link directly with explicit primary/secondary section ids
- users can alternatively pick one preset to establish a common comparison pair
- exports can say which preset was active when the snapshot was created

If explicit section ids and a preset disagree, the preset should win for rendering because it is the more intentional user action.

## Non-Goals

- No new compare payload fields
- No workbench-side preset state
- No attempt to expose every possible section combination
- No replacement of the explicit primary/secondary section ids

## Verification Shape

This slice is complete when:

- generated catalog assets expose `workspace_detail_preset`
- focused workspace helpers can resolve the preset into section ids
- export metadata preserves the active preset
- focused catalog unit, workflow, and smoke verification remain green
