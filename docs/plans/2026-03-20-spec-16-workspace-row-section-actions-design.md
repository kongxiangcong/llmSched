# SPEC-16 Workspace Row Section Actions Design

## Scope

This slice stays entirely inside the static catalog workspace compare surface. We do not add new compare data, change compare contracts, or expand the workbench. Instead, we make the workspace overview table itself participate in the new focused compare-section workflow by adding section-targeted actions inside the row cells.

The gap is straightforward. We now let users persist both the focused candidate and the active compare section, but row interactions still require two steps: first focus the candidate, then use the focused drill-down card to switch sections. That is workable, but it still forces extra navigation when the row itself already tells us which section the user is acting from.

## Recommended Approach

Add compact section-targeted actions directly to the workspace summary cells so row interactions can retarget the focused workspace state in one click. The natural mapping is:

- `Primary Delta` and `Primary Ratio` -> `summary`
- `Shared Metric Deltas` -> `grouped-metrics`
- `Sweep Layer Deltas` -> `estimated-layer`

This is intentionally narrow. We do not add separate row columns, and we do not invent new UI state. We reuse the existing `workspace_candidate` and `workspace_detail_focus` URL state by emitting more precise links from the row-level content helpers already responsible for those cells.

## Interaction Model

The workspace table remains the overview. Each relevant summary cell can now include a compact action like `Focus Compare Section`, which updates:

- `workspace_candidate`
- `workspace_detail_focus`

in a single workspace-local link. The focused workspace drill-down card then opens on the target section immediately. This gives users a direct path from overview table scan to the exact compare section they want without reopening the candidate first.

## Non-Goals

- No new compare payload fields
- No new workspace columns
- No workbench routing changes
- No change to compare focus taxonomy

## Verification Shape

This slice is complete when:

- generated catalog assets expose row-to-section focus helpers
- workspace row summary cells include section-targeted focus links
- focused workspace link/export state continues to preserve the chosen section
- focused catalog unit, workflow, and smoke verification remain green
