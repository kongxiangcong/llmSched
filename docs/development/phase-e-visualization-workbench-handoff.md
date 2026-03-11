# Phase E Visualization Workbench Handoff

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
- a saved-view action that copies the current panel/filter state as a shareable link
- an export action that downloads the active panel plus current filtered state as JSON
- an exportable image action that downloads the active panel as an SVG snapshot
- a catalog compare tray that lets users select up to two runs and inspect shared summary-metric deltas without leaving the catalog
- a baseline-pinned compare workspace that compares visible runs in the same scenario as the first selected run
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

These are follow-on hardening items, not reasons to reopen the current static workbench contract.

## 7. Recommended Next Step

Next work should harden `SPEC-19`, not reopen `SPEC-18`:
1. Extend the catalog from current packaged-run discovery to richer workspace navigation and grouping.
2. Extend the current baseline-pinned compare workspace into richer compare navigation and deeper drill-down beyond the current shared summary-metric compare.
3. Keep `visualization_bundle.json` as the UI source of truth.
4. Delay live-service or framework decisions until static workbench and catalog gaps are concrete.
