# SPEC-16 Workspace Dual-Section Compare Design

## Scope

This slice stays inside the static catalog workspace compare drill-down. We do not change compare payloads, add new compare sections, or modify workbench routing. Instead, we let the focused workspace card optionally preserve and render a second compare section beside the primary focused section.

The current workflow now supports:

- a focused candidate
- a focused compare section
- row-level actions that jump into one section directly

That is already useful, but it still forces one-at-a-time inspection when the common need is to compare two sections against the same candidate pair, for example `grouped-metrics` versus `estimated-layer`, or `summary` versus `pressure`.

## Recommended Approach

Add one optional URL/state key, `workspace_secondary_detail_focus`, with the same section vocabulary as `workspace_detail_focus`. The focused workspace card should:

- render the primary focused section first
- optionally render a second explicitly labeled section immediately after it
- preserve both section ids in copied workspace links, JSON export, and SVG snapshot metadata

This keeps the change local and additive. We reuse the existing section rendering logic and ordering helpers instead of creating a new layout system or a separate compare mode.

## Interaction Model

The focused workspace card remains the destination. After this slice:

- the primary section still behaves exactly as it does today
- users can additionally pin one secondary section for comparison
- metadata can say both which section is focused and which section is being compared alongside it

If the secondary section is the same as the primary section, we collapse back to the current single-section behavior rather than duplicating content.

## Non-Goals

- No new compare contracts
- No new workspace columns
- No workbench-side secondary focus state
- No attempt to fully redesign the focused workspace card layout

## Verification Shape

This slice is complete when:

- generated catalog assets expose `workspace_secondary_detail_focus`
- focused workspace helpers preserve and render the secondary section
- export metadata records the secondary section when present
- focused catalog unit, workflow, and smoke verification remain green
