# 2026-03-20 SPEC-16 Compare Focus Modes Design

## Context

`SPEC-16` already emits three strong compare surfaces:

- grouped scalar compare summaries
- estimated `layer_deltas`
- fitted `fitted_layer_deltas`

`SPEC-18/19` can now render and export those surfaces, but the compare UX still behaves like a fixed dashboard. Users can inspect all groups, switch layer sorting, and deep-link into a focused sweep row, yet they cannot choose an explicit compare lens such as "show me memory pressure first" or "show me schedule imbalance first" and carry that focus consistently across catalog workspace, workbench sweep panel, and snapshot/export metadata.

The roadmap's current next slice calls for "stronger compare modes beyond the current estimated/fitted layer and grouped-scalar summaries". The narrowest useful interpretation is to add compare-focus modes on top of the existing payload, without reopening estimator math or inventing a new report contract.

## Recommended Approach

Add a shared compare-focus abstraction that selects and labels the most relevant compare content for a chosen lens. The first slice should stay visualization-facing but reuse shared selection helpers so catalog and workbench do not diverge.

Recommended focus modes:

- `summary`
- `memory-pressure`
- `schedule-shape`
- `estimated-layer`
- `fitted-layer`

For scalar-driven modes, the implementation should reuse existing grouped compare rows and highlighted scalar deltas rather than recomputing new deltas. For layer-driven modes, the implementation should reuse the existing estimated/fitted layer delta payloads and existing sorting semantics. The output should remain explainable: each mode should produce a short label, a compact summary, and the top N rows that justify the summary.

## Boundaries

In scope:

- shared compare-focus selection helpers
- visualization-facing compare-focus metadata
- catalog controls and workspace drilldown for compare focus
- workbench sweep-panel compare focus and export/snapshot persistence

Out of scope:

- new estimator math
- new `SPEC-13/14/15` report fields
- new standalone `PhaseDCompareReport` math
- block-level diffing
- live services

## Success Criteria

- A user can select a compare-focus mode in catalog workspace and in workbench sweep view.
- The selected mode changes which summary rows and layer rows are emphasized, but not the underlying delta math.
- Deep links, JSON export, and SVG snapshot metadata preserve the selected compare focus.
- Raw `SweepComparison` and `PhaseDCompareReport` consumers still work when the new focus metadata is absent.
