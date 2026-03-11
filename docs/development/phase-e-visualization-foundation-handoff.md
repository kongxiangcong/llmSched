# Phase E Visualization Foundation Handoff

## 2026-03-07 Checkpoint

- `SPEC-18` now has a stable visualization-facing static bundle foundation.
- `run-visualization-packaging` is the standalone workflow and CLI entrypoint for packaging one run-root into UI-consumable view data.
- Gemma3 `single-core/dual-core x prefill/decode` visualization packaging smoke now produces deterministic `visualization_bundle.json` artifacts.

## 1. What Is Stable Now

The current `SPEC-18` foundation consumes:
- one completed run-root
- `manifest.json`
- `dumps/canonical_graph_ir.json`
- schedule artifact
- `artifacts/memory_plan.json`
- `reports/isa_coverage_report.json`
- one top-level evaluation report
  - `reports/prefill_evaluation_report.json`
  - or `reports/decode_evaluation_report.json`
- optional `reports/sweep_delta_report.json` from a sweep workspace

It produces:
- `reports/visualization_bundle.json`
- `manifest.artifact_index["visualization_bundle"]`
- completed or failed `run-summary.json` updates through the visualization-packaging workflow

This foundation intentionally emits a static bundle, not a live query service.

## 2. Stable Contract

The current `VisualizationBundle` now carries:
- `bundle_id`
- `metadata`
- `view_index`
- `report_summary`
- `graph_view`
- `timeline_view`
- `kv_view`
- `vmem_view`
- `coverage_view`
- optional `sweep_view`
- `issues`

Current contract guarantees:
- UI does not need to understand internal GraphIR, ScheduleIR, MemoryPlan, or ISA coverage schemas
- one bundle is enough to render one run’s graph/timeline/KV/VMEM/coverage views
- sweep data is optional and only attached when a sweep workspace is explicitly provided

## 3. Current Aggregation Policy

The current bundle builder normalizes data as follows:
- graph view
  - built from canonical GraphIR nodes and producer-to-consumer edges
- timeline view
  - built from ordered ScheduleIR blocks with core/stage/macro metadata
- KV view
  - built from KV formulas and KV address diagnostics
- VMEM view
  - built from region summaries and VMEM fit diagnostics
- coverage view
  - built from ISA coverage counts and per-issue summaries
- sweep view
  - filtered to the current run’s `scenario_name`, `mode`, and target-profile context

The current `report_summary` policy is intentionally summary-grade:
- prefill exposes throughput-centric metrics
- decode exposes token-latency/KV-centric metrics
- hotspot macro ops preserve top-level report ordering

## 4. Workflow And CLI Entry

Workflow:
- `llm_sched.pipeline.run_visualization_packaging(run_root, sweep_root=None)`

CLI:
- `llm-sched run-visualization-packaging --run-root ...`
- `llm-sched run-visualization-packaging --run-root ... --sweep-root ...`

Current output location:
- `reports/visualization_bundle.json`

The current workflow is deliberately file-driven and deterministic. It does not start a server, maintain a cache, or expose remote query endpoints.

## 5. What SPEC-19 Can Assume

Workbench-facing work may now assume:
- one stable file already exists for graph/timeline/KV/VMEM/coverage data
- prefill and decode are normalized behind one bundle contract
- sweep comparison data can be attached without forcing the UI to reopen raw sweep reports

`SPEC-19` should not need to rediscover:
- how to find the right lower-level artifact for each view
- how to translate schedule blocks into timeline rows
- how to reconcile prefill and decode report shape differences

## 6. What Is Still Missing

The current `SPEC-18` foundation still lacks:
- a live query API or service layer
- multi-run catalogs and cross-run navigation indexes
- richer layer-level drill-down data
- direct descriptor/block/per-tensor deep links
- web asset serving or frontend application code

These are follow-on Phase E items, not reasons to reopen the current bundle contract.

## 7. Recommended Next Step

Next work should move into `SPEC-19`:
1. Build the first visualization workbench against `visualization_bundle.json`.
2. Keep the static bundle as the source of truth until UI needs prove a live service is necessary.
3. Only extend `SPEC-18` beyond the static bundle when the workbench reveals a concrete missing query pattern.
