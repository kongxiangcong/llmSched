# SPEC-16 Deeper Compare Workspace Drill-Down Design

## Scope

This slice stays entirely downstream of the current `SPEC-16` compare payload. We do not add new compare math, extend `SweepComparison`, or reopen the Phase D report contracts. Instead, we deepen the existing catalog workspace compare experience by introducing one explicit shared state: the currently focused workspace candidate. That state will drive a dedicated workspace compare drill-down section, workbench deep links, and workspace-local export metadata.

The user-facing gap is concrete. Today, catalog workspace compare rows already embed summary-grade compare details, layer drilldown links, and sweep links, but there is no persistent way to say "this is the candidate I am currently investigating." As a result, the workspace behaves like a dense table rather than a navigable drill-down surface, and copied links or exported snapshots do not capture which candidate row the user was actually inspecting.

## Recommended Approach

Promote `workspace_candidate` into the catalog workspace URL/state model and use it to render a dedicated focused drill-down card below the workspace table. The card should:

- resolve the selected baseline-versus-candidate pair from the existing workspace candidate set
- reuse the current compare summary helpers rather than inventing new compare rendering logic
- expose the same focus-aware grouped compare, pressure compare, estimated layer, and fitted layer sections that already exist in the row-level drilldown
- preserve current compare focus and layer-diff mode when linking back into workbench

This is the highest-value, lowest-risk slice because it turns current compare detail fragments into one coherent workflow without changing upstream artifacts. It also gives us a stable state primitive we can include in workspace link copy, JSON export, SVG snapshot metadata, and future screenshot flows.

## Interaction Model

The workspace table remains the overview. Each candidate row gains an explicit workspace-focus action. When a candidate is focused:

- the workspace URL persists `workspace_candidate=<target_profile_name>`
- the row can show a compact "Focused" state
- a dedicated `Focused Workspace Compare Drilldown` card renders below the table
- export metadata includes the focused candidate and a compact compare summary

If the focused candidate falls out of scope because the user changes filters or compare scope, the workspace falls back gracefully to the first visible candidate instead of leaving the drill-down empty while still preserving explicit empty-state messaging when no candidates remain.

## Non-Goals

- No new compare contracts or compare summary fields
- No live service/query layer
- No redesign of compare tray selection behavior
- No screenshot workflow expansion beyond carrying the new focused workspace state into existing JSON/SVG export

## Verification Shape

This slice is complete when:

- catalog generated assets expose focused workspace candidate state and dedicated drill-down rendering helpers
- workspace URL, JSON export, and SVG snapshot metadata preserve the focused workspace candidate
- focused drill-down continues to honor existing `compare_focus` and `layer_delta_focus` controls
- focused catalog, workflow, and smoke verification remain green
