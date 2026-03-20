# SPEC-16 Analysis Flow Candidate Inspection Design

## Intent

The current `workspace_analysis_flow` surface is good at preserving analyst intent once a candidate has already been chosen, but it still leaves one high-friction step to the user: deciding which candidate should be inspected first. In the current catalog workspace, analysts still have to scan the full candidate table and infer which row best matches the selected flow.

This slice upgrades analysis flows from a focus-preservation layer into a candidate triage layer. The flow should not only say "look at summary plus estimated layer" or "look at pressure plus fitted layer"; it should also rank visible candidates according to the currently selected flow and explain why a given candidate is worth opening first.

## Approach

We keep the existing baseline-vs-candidate workspace model and avoid reopening any compare contracts. Instead, we enrich the existing row-state calculation with a small, flow-aware recommendation summary. For each candidate row, we derive:

- whether the row is recommended for the active flow
- a stable recommendation score
- a short human-readable reason string
- an optional recommendation tier such as `primary`, `watch`, or `background`

The scoring stays deliberately heuristic and only consumes already-available row data:

- `summary-hotspots` favors large top-line deltas and strong estimated-layer movement
- `grouped-hotspots` favors grouped-metric deltas plus estimated-layer movement
- `memory-regression` favors pressure regressions and fitted-layer movement

## Surface Changes

The catalog workspace gains three coordinated surfaces:

- workspace rows expose a recommendation tag/reason when an analysis flow is active
- the focused workspace card shows a new recommendation summary for the current candidate
- the workspace export payload preserves structured recommendation details for the focused candidate and all candidate rows

Optionally, we can also promote the top-ranked row into a small recommendation banner above the table, but the first implementation should prefer the row and focused-card surfaces as the stable minimum.

## Validation

We will treat this slice as done when:

- catalog builder tests prove recommendation helpers, labels, and export metadata exist
- workflow and smoke tests prove generated catalog assets preserve the recommendation surface
- the flow works entirely off existing compare payloads and does not change Phase D contracts
