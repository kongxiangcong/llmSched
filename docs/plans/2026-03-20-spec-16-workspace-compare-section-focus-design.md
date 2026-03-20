# SPEC-16 Workspace Compare Section Focus Design

## Scope

This slice stays entirely inside the static catalog workspace experience. We do not extend Phase D compare contracts, add new compare rows, or modify the current compare-focus taxonomy. Instead, we add one more drill-down state above the recently introduced `workspace_candidate`: a focused workspace compare section.

The current focused workspace card already surfaces richer compare content, but it still behaves like a long composite block. Users can preserve the candidate they are inspecting, yet they still cannot say "keep me on pressure compare" or "show me the fitted layer section first" when copying a workspace link, exporting a snapshot, or moving between row-level actions and the focused drill-down card.

## Recommended Approach

Promote a new URL/state key, `workspace_detail_focus`, with a small fixed section set:

- `summary`
- `grouped-metrics`
- `pressure`
- `estimated-layer`
- `fitted-layer`

Use that state only inside the catalog workspace. Candidate rows and the focused drill-down card should expose compact section links that retarget the current workspace state to the selected detail section. The focused drill-down card should then emphasize the selected section first and label the active section in metadata/export output.

This is the lowest-risk path because the section content already exists in `buildMatchedCompareSummaryRows`, `renderPressureCompareSummary`, and the existing workspace layer-drilldown helpers. We are only introducing a stable navigation primitive around current content, not rethinking rendering or compare semantics.

## Interaction Model

The focused workspace card remains the main compare destination. After this slice:

- the URL persists both `workspace_candidate` and `workspace_detail_focus`
- row-level actions can jump directly into one section of the focused workspace card
- the focused card can display the currently active section name and keep the requested section visually first
- JSON/SVG export metadata can say which compare section was active when the snapshot was created

If a selected section has no content for the current candidate pair, the card should still render a clear empty-state section rather than silently falling back to another section.

## Non-Goals

- No new compare payload fields
- No workbench-side state changes
- No redesign of compare tray selection
- No live query/service behavior

## Verification Shape

This slice is complete when:

- catalog generated assets expose `workspace_detail_focus`
- focused workspace section links and helpers are present in generated app code
- focused workspace export metadata preserves the active section
- focused catalog unit, workflow, and smoke verification remain green
