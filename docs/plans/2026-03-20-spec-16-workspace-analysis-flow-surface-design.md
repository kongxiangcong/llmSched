# SPEC-16 Workspace Analysis Flow Surface Design

## Scope

This slice bundles three tightly related improvements around the new `workspace_analysis_flow` layer:

- row-level analysis-flow shortcuts
- a focused workspace flow-summary surface
- stronger export continuity for the active flow

We still do not change compare payloads, add new sections, or touch workbench behavior. The goal is to make the existing analysis-flow state feel like a real analyst workflow rather than a hidden routing layer.

## Recommended Approach

Use one shared flow mapping and drive all three surfaces from it:

- row-level `Shared Metric Deltas` and `Sweep Layer Deltas` cells can open the most natural flow directly
- the focused workspace card gets a compact `Analysis Flow Summary` block describing the active flow and the resolved section pairing
- export metadata includes both the active flow id and a human-readable summary row

This is higher leverage than another micro-state addition because it makes the current compare stack easier to discover, easier to navigate from the overview table, and easier to preserve in copied/exported artifacts, all without adding new compare semantics.

## Verification Shape

This slice is complete when:

- generated catalog assets expose row-level analysis-flow links
- focused workspace drill-down renders an `Analysis Flow Summary`
- export metadata preserves the human-readable active flow summary
- focused catalog unit, workflow, and smoke verification remain green
