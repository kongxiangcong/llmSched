# Phase D Prefill Foundation Handoff

## 2026-03-15 Fitted-Cycle Topline Adoption Checkpoint

- New plan: `../plans/2026-03-15-spec-14-15-fitted-topline-adoption.md`
- `PrefillEvaluationReport.throughput` now carries summary-grade `fitted_work_cycles`, fitted per-token ratios, and per-phase fitted toplines sourced from `SPEC-13`.
- `SPEC-14` now reuses `PerfSummaryReport.totals["fitted_work_cycles"]` plus `phase_attribution[*].fitted_work_cycles` without reinterpreting existing `estimated_cycles`, `macro_hotspots`, `node_hotspots`, or `layer_breakdown`.
- focused prefill/decode builder, workflow, and smoke regressions remain green (`20 passed`) with the stronger summary-grade fitted-cycle surface.
- This batch deliberately does not introduce:
  - fitted-cycle hotspot rows
  - fitted-cycle layer breakdown rows
  - compare-grade fitted-cycle aggregation
  - deeper cycle-model changes outside `SPEC-13`

## 2026-03-12 Hottest-Region Memory-Class Reuse Checkpoint

- New plan: `../plans/2026-03-12-spec-08-prefill-decode-memory-class-hotspot-reuse.md`
- `PrefillEvaluationReport.memory_hotspot` now carries `hottest_region_peak_bytes_by_memory_class`.
- `SPEC-14` now reuses `memory_plan.region_summaries[hottest_region].peak_bytes_by_memory_class` directly instead of leaving the hottest-region source-class mix trapped inside planner-only JSON.
- focused prefill contract, builder, and workflow regressions remain green with the stronger report contract.

## 2026-03-11 Hottest-Region Backing-Store Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-prefill-decode-backing-store-hotspot-reuse.md`
- `PrefillEvaluationReport.memory_hotspot` now carries `hottest_region_peak_bytes_by_backing_store`.
- `SPEC-14` now reuses `memory_plan.region_summaries[hottest_region].peak_bytes_by_backing_store` directly instead of reducing the hottest region to one scalar peak.
- focused prefill contract, builder, and workflow regressions remain green with the stronger report contract.

## 2026-03-09 Memory Hotspot Summary Checkpoint

- New plan: `../plans/2026-03-09-spec-14-15-memory-hotspot-summary.md`
- `SPEC-14` now exposes a first-order memory-hotspot view on top of the already-landed throughput and memory-summary fields.
- New closure evidence:
  - `PrefillEvaluationReport` now carries `memory_hotspot`
  - `memory_hotspot` now exposes `dominant_address_space`
- `memory_hotspot` now exposes copied read/write bytes by address space
- `memory_hotspot` now exposes the hottest VMEM region and its peak utilization
- `memory_hotspot` now also exposes hottest-region backing-store attribution
- `memory_hotspot` now also exposes hottest-region memory-class attribution
- prefill workflow and Phase D prefill smoke remain green with the stronger report contract
- This batch deliberately does not introduce:
  - layer-level memory views
  - token-phase hotspot replay
  - cross-run compare logic

## 2026-03-07 Checkpoint

- `SPEC-14` now has a stable prefill-only top-level evaluation foundation.
- `run-prefill-evaluation` is the standalone run-root workflow and CLI command for prefill-facing reports.
- Gemma3 `single-core/dual-core x prefill` smoke now produces deterministic prefill evaluation artifacts.

## 1. What Is Stable Now

The current `SPEC-14` foundation consumes:
- `reports/perf_summary_report.json`
- `reports/isa_coverage_report.json`
- `artifacts/memory_plan.json`
- scenario profile

It produces:
- `reports/prefill_evaluation_report.json`
- `manifest.artifact_index["prefill_evaluation_report"]`
- completed or failed `run-summary.json` updates through the prefill-evaluation workflow

This foundation is intentionally summary-grade. It aggregates stable Phase C and `SPEC-13` artifacts and does not rerun the compile chain.

## 2. Stable Contract

The current `PrefillEvaluationReport` now carries:
- `run_id`
- `graph_id`
- `scenario_name`
- `schedule_kind`
- `batch`
- `seq_len`
- `mxu_dominant`
- `throughput`
- `memory_summary`
- `memory_hotspot`
- `isa_summary`
- `macro_hotspots`

Current top-level guarantees:
- only `scenario.mode = prefill` is accepted
- throughput is derived from run-level cycles and token count
- memory summary is derived from existing VMEM/KV diagnostics instead of recomputing planning logic
- ISA gaps stay explicit at the top-level report

## 3. Current Aggregation Policy

The prefill evaluator currently models:
- throughput as `total_tokens`, `estimated_cycles`, `tokens_per_cycle`, `cycles_per_token`, and `bytes_per_cycle`
- memory pressure using `max_region_utilization`, overflow region count, unresolved address count, and KV formula count
- memory hotspots using address-space movement totals from `PerfSummaryReport` plus hottest-region data from `MemoryPlanArtifact`
- ISA summary using unmapped block count plus `gap_counts`
- hotspots using sorted per-macro cycle totals from `PerfSummaryReport`

Current `mxu_dominant` policy is intentionally simple:
- treat `GEMM`, `WDQ_GEMM`, and `RMSNORM_GEMM` as MXU-heavy macros
- mark the run as MXU-dominant when those macros contribute at least half of whole-run cycles

## 4. What SPEC-15 And SPEC-16 Can Assume

Decode and sweep work may now assume:
- a top-level eval report format exists alongside the lower-level perf artifacts
- Phase D can expose summary-grade reports without reopening descriptor semantics
- single-core and dual-core prefill runs are already normalized to one report contract

`SPEC-15/16` should not need to rediscover:
- how to aggregate whole-run cycles into a user-facing top-level report
- how VMEM and ISA summaries surface into evaluation outputs
- how hotspots are derived from stable per-macro totals

## 5. What Is Still Missing

The current `SPEC-14` foundation still lacks:
- layer-level prefill report views
- cross-run comparison between single-core and dual-core in one report
- layer-level or token-phase memory hotspot attribution
- integration with decode reporting and sweep delta reports

These are follow-on Phase D items, not reasons to reopen the current perf or scheduler contracts.

## 6. Recommended Next Step

Next work should keep moving forward inside Phase D:
1. Start `SPEC-15` with a decode-only top-level report that matches the current prefill aggregation style.
2. After both top-level reports exist, add sweep/delta comparison in `SPEC-16`.
3. Only then widen visualization-facing data contracts.
