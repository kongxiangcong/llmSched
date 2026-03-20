# SPEC-16 Analysis Flow Workbench Bridge Design

## Intent

The current `workspace_analysis_flow` state is useful inside catalog workspace compare, but it still stops short of the downstream surface where analysts spend time validating deltas: the workbench sweep panel. We already preserve `compare_focus` and `layer_delta_focus` across catalog-to-workbench links, but the higher-level analyst intent that chose those focuses is still lost when users leave the workspace card.

This slice closes that gap by promoting analysis flows into a shared cross-surface navigation concept. The goal is not to invent new compare math or new sweep payloads. Instead, we carry an existing intent layer through the current deep-link stack so catalog, workbench, copied URLs, and export artifacts all describe the same workflow.

## Approach

We keep the existing catalog-side `workspace_analysis_flow -> preset -> section pair` mapping as the source of truth for analyst intent. On top of that, we add a workbench-facing mapping that resolves each supported analysis flow into:

- a default `compare_focus`
- a default `layer_delta_focus`
- a user-facing flow label

Catalog links into workbench will attach the active analysis flow when users are in focused workspace compare paths. Workbench then hydrates that state from URL parameters, uses it to keep compare/layer defaults aligned, renders a compact `Analysis Workflow` summary near the sweep compare surface, and preserves the flow in copied links and JSON/SVG export metadata.

## Scope

Included:

- catalog-to-workbench links preserve active analysis flow for focused workspace compare paths
- workbench URL state gains explicit analysis-flow support
- workbench sweep surface renders an analyst-facing summary/action block for the active flow
- workbench export metadata preserves both raw flow id and a human-readable resolved summary

Not included:

- new compare contracts or new sweep payload math
- new catalog compare focuses beyond the existing stable taxonomy
- any reopening of Phase D estimator/eval contracts

## Validation

We will treat this as done when:

- catalog builder tests prove workbench links can carry analysis-flow state
- workbench builder tests prove URL hydration, summary rendering, and export metadata all include analysis-flow information
- workflow/smoke tests stay green for catalog and workbench generation
