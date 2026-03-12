# Phase E Visualization Workbench Handoff

## 2026-03-12 Catalog Phase C Blocked-Case Drill-Down Checkpoint

- New plan: `../plans/2026-03-12-catalog-phase-c-blocked-case-drilldown.md`
- static catalog now expands `Phase C Gate` into a blocked-case table when `workspace_root/reports/phase_c_acceptance_report.json` reports non-ready canonical cells
- `catalog_manifest.json` now carries optional `phase_c_blocked_cases`, including case id, blocker kind, planner/downstream closure states, and remaining gaps
- blocked-case rows with a concrete run now expose a direct packaged-workbench link, with planner-side blockers defaulting to `memory` and downstream blockers selecting `summary`/`memory`/`coverage` from structured required-consumer gaps instead of free-text parsing; `descriptor_generation` links now land on the packed-descriptor coverage section through `coverage_focus=packed-descriptor`
- those blocked-case links now also preserve `catalog_return`, so workbench drill-down can return to the same catalog context
- planner blocked-case links now also infer `memory_query` from known overflow-region gaps, so memory inspection can open with the relevant region already filtered
- focused catalog contract, builder, workflow, and CLI regressions remain green with the stronger workspace drill-down surface

## 2026-03-12 Catalog Phase C Gate Summary Checkpoint

- New plan: `../plans/2026-03-12-catalog-phase-c-gate-summary.md`
- static catalog now surfaces `Phase C Gate` readiness directly from `workspace_root/reports/phase_c_acceptance_report.json` when that workspace artifact is present
- `catalog_manifest.json` now carries an optional `phase_c_gate_summary`, including status plus ready/blocked/planner/downstream counts
- focused catalog contract, builder, workflow, and CLI regressions remain green with the stronger workspace-summary surface

## 2026-03-12 VMEM Memory-Class Visibility Checkpoint

- New plan: `../plans/2026-03-12-spec-08-visualization-memory-class-visibility.md`
- the memory panel now renders `Region Memory Class Mix` directly from `bundle.vmem_view.regions[*].peak_bytes_by_memory_class`
- memory-panel SVG snapshot lines now also expose top-region memory-class attribution, so the new visibility is not screen-only
- focused workbench builder and workflow regressions remain green with the stronger memory-panel contract

## 2026-03-11 Catalog Workbench Return Navigation Checkpoint

- New plan: `../plans/2026-03-11-spec-19-catalog-workbench-return-navigation.md`
- compare-driven workbench links now carry encoded catalog filter/selection state through `catalog_return`
- the workbench now surfaces `Back to Catalog Compare` when opened from catalog compare, and preserves that return target across internal panel deep links and copied current-view URLs
- focused catalog/workbench builder, workflow, and CLI smoke regressions remain green with the stronger round-trip navigation loop

## 2026-03-11 Compare Workspace Panel Navigation Checkpoint

- New plan: `../plans/2026-03-11-spec-19-compare-workspace-panel-navigation.md`
- the static catalog now exposes a `catalog-workbench-panel-filter` so compare tray and baseline-pinned workspace can deep-link into `summary`, `timeline`, `memory`, or `coverage`
- compare navigation no longer hardcodes `Open Summary`; it now renders `Open Selected Panel` plus summary fallback when needed
- focused catalog builder, workflow, and CLI smoke regressions remain green with the stronger workspace-navigation surface

## 2026-03-11 Catalog Multi-Metric Compare Checkpoint

- New plan: `../plans/2026-03-11-spec-19-catalog-multi-metric-compare.md`
- static catalog compare now carries `metric_values` copied from packaged bundle summary metrics instead of collapsing each run to one scalar primary metric
- the compare tray and baseline-pinned workspace now render `Shared Metric Deltas` directly from that structured metric map
- focused catalog contract, builder, and workflow regressions remain green with the stronger compare surface

## 2026-03-11 VMEM Backing-Store Visibility Checkpoint

- New plan: `../plans/2026-03-11-spec-19-workbench-vmem-backing-store-visibility.md`
- the memory panel now renders `Region Backing Store Mix` directly from `bundle.vmem_view.regions[*].peak_bytes_by_backing_store`
- memory-panel SVG snapshot lines now also expose top-region backing-store attribution, so the new visibility is not screen-only
- focused workbench builder and workflow regressions remain green with the stronger memory-panel contract

## 2026-03-07 Checkpoint

- `SPEC-19` now has a stable static workbench foundation.
- `run-visualization-workbench` is the standalone workflow and CLI entrypoint for packaging one run-root into a browsable `workbench/` directory.
- Gemma3 `single-core/dual-core x prefill/decode` workbench smoke now produces deterministic `index.html`, `app.js`, `styles.css`, and `workbench_manifest.json`.

## 1. What Is Stable Now

The current `SPEC-19` foundation consumes:
- one completed run-root
- `manifest.json`
- `reports/visualization_bundle.json`

It produces:
- `workbench/index.html`
- `workbench/assets/app.js`
- `workbench/assets/styles.css`
- `workbench/workbench_manifest.json`
- optional cross-run catalog outputs when catalog packaging is used:
  - `catalog/index.html`
  - `catalog/assets/app.js`
  - `catalog/assets/styles.css`
  - `catalog/catalog_manifest.json`
- `manifest.artifact_index["visualization_workbench_entry"]`
- `manifest.artifact_index["visualization_workbench_manifest"]`
- completed or failed `run-summary.json` updates through the visualization-workbench workflow

This foundation intentionally emits a static workbench, not a dev server or live application backend.

## 2. Stable Contract

The current `VisualizationWorkbenchArtifact` now carries:
- `workbench_id`
- `metadata`
- `entry_html_path`
- `bundle_path`
- `default_panel`
- `available_panels`
- `asset_files`

Current contract guarantees:
- one workbench points at exactly one `VisualizationBundle`
- the entry page and all static assets are declared explicitly
- the default panel and available panels are validated up front
- sweep navigation is only exposed when `bundle.sweep_view` exists

## 3. Current Rendering Policy

The current workbench builder renders:
- `summary`
- `graph`
- `timeline`
- `core-occupancy`
- `memory`
- `coverage`
- optional `sweep`

Current policy is intentionally simple:
- one static `index.html`
- one static `app.js`
- one static `styles.css`
- browser-side fetch only to the declared bundle path
- no extra report fetches and no raw IR fetches

Current hardening already includes:
- graph search against node id / label / op / dtype
- timeline search against block id / node id / macro / stage
- timeline filters for stage and core
- click-to-inspect timeline block detail rendering in a dedicated detail card
- explicit-list cross-run catalog generation with mode/schedule filtering
- optional catalog discovery from explicit run lists, `sweep_root`, or a workspace scan
- catalog search against run id / scenario / target / schedule
- scenario-group navigation chips and grouped run sections inside the catalog page
- workbench URL-state routing for `panel`, `graph_query`, `timeline_query`, `timeline_stage`, `timeline_core`, and `detail_block`
- catalog panel-deep-link shortcuts from grouped run cards into `summary`, `timeline`, `memory`, and `coverage`
- graph node quick links into timeline filtering
- timeline block detail quick links into graph search and coverage filtering
- coverage issue quick links into timeline block detail
- KV formula quick links into timeline filtering
- memory-panel visibility for per-region backing-store attribution
- memory-panel visibility for per-region memory-class attribution
- a saved-view action that copies the current panel/filter state as a shareable link
- an export action that downloads the active panel plus current filtered state as JSON
- an exportable image action that downloads the active panel as an SVG snapshot
- a catalog compare tray that lets users select up to two runs and inspect shared summary-metric deltas without leaving the catalog
- a baseline-pinned compare workspace that compares visible runs in the same scenario as the first selected run
- a selected-panel navigation control that retargets compare links into `summary`, `timeline`, `memory`, or `coverage`
- a round-trip catalog/workbench navigation loop so compare-driven drill-down can return to the same catalog context
- compare workspace controls for baseline/candidate role swap and same-scenario versus all-visible compare scope switching

This keeps the UI side decoupled from lower-level artifact churn.

## 4. Workflow And CLI Entry

Workflow:
- `llm_sched.pipeline.run_visualization_workbench(run_root)`

Builder:
- `llm_sched.visualization.build_visualization_workbench(bundle, bundle_relative_path, workbench_root)`

CLI:
- `llm-sched run-visualization-workbench --run-root ...`
- `llm-sched run-visualization-catalog --catalog-root ... [--run-root ...] [--sweep-root ...] [--workspace-root ...]`

Current output location:
- `workbench/index.html`
- `workbench/assets/app.js`
- `workbench/assets/styles.css`
- `workbench/workbench_manifest.json`
- `catalog/index.html`
- `catalog/assets/app.js`
- `catalog/assets/styles.css`
- `catalog/catalog_manifest.json`

## 5. What This Enables

Downstream users can now:
- open one run-root and inspect graph/timeline/memory/coverage data without reading raw JSON by hand
- keep prefill and decode on one normalized UI surface
- attach sweep comparison data without introducing a second UI contract
- build one static index page that jumps across multiple packaged run roots
- reuse the same catalog flow for explicit lists or sweep/workspace discovery

This is the first point where `SPEC-18` becomes directly usable by a human-facing workbench.

## 6. What Is Still Missing

The current `SPEC-19` foundation still lacks:
- a served application shell
- richer workspace discovery policies beyond the current packaged-run scan boundary
- richer rendered screenshot workflows beyond the current SVG snapshot export
- richer compare drill-down beyond the current shared summary-metric compare
- deeper workspace drill-down beyond the current selected-panel deep links
- richer round-trip navigation beyond the current catalog-return loop

These are follow-on hardening items, not reasons to reopen the current static workbench contract.

## 7. Recommended Next Step

Next work should harden `SPEC-19`, not reopen `SPEC-18`:
1. Extend the catalog from current packaged-run discovery, selected-panel deep links, and catalog-return loop to deeper workspace drill-down and grouping.
2. Extend the current baseline-pinned compare workspace into richer compare navigation and deeper drill-down beyond the current shared summary-metric compare.
3. Keep `visualization_bundle.json` as the UI source of truth.
4. Delay live-service or framework decisions until static workbench and catalog gaps are concrete.
