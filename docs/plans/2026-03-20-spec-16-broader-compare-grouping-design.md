# SPEC-16 Broader Compare Grouping Design

## Scope

This slice stays entirely downstream of existing `SPEC-16` compare math. We do not add new estimator rows, new sweep artifacts, or new Phase D compare contracts. Instead, we promote two already-stable grouped scalar sections, `throughput_latency` and `phase_shape`, into first-class compare focus modes alongside the existing `summary`, `memory-pressure`, `schedule-shape`, `estimated-layer`, and `fitted-layer` focus set.

The user-facing goal is to make compare focus mean something operational in catalog and workbench, not just metadata. Today, both surfaces can preserve `compare_focus`, but grouped compare rendering still tends to show all grouped scalar sections together. After this slice, choosing a grouped compare focus should narrow emphasis to the corresponding compare section while preserving existing pressure and layer-focused flows.

## Recommended Approach

Use a shared focus-to-group mapping in `compare_grouping.py` and keep the taxonomy additive:

- `summary` maps to `headline`
- `throughput-latency` maps to `throughput_latency`
- `phase-shape` maps to `phase_shape`
- `memory-pressure` keeps its current pressure-oriented behavior
- `schedule-shape` keeps its current grouped schedule behavior
- `estimated-layer` / `fitted-layer` stay layer-oriented

This is the lowest-risk option because the grouped scalar data already exists in bundle and catalog payloads. We only need to expose the new focus ids, update the available focus rows emitted by packaging, and make catalog/workbench render helpers pick the relevant grouped sections for the active focus. That gives us broader compare grouping without reopening any Phase D computation or inventing another parallel compare abstraction.

## Non-Goals

- No new upstream compare math
- No new live query/service layer
- No deeper workspace drill-down beyond the current compare surface
- No UI-heavy redesign of catalog or workbench controls

## Verification Shape

The slice is complete when:

- bundle/catalog compare summaries expose the broader focus taxonomy
- generated catalog/workbench assets contain the new focus labels and focus-aware grouped rendering helpers
- focused unit, pipeline, and smoke visualization verification stays green
