# Phase D Performance Foundation Handoff

## 2026-03-11 SPEC-08 Backing-Store Summary Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-perf-backing-store-reuse.md`
- `SPEC-13` now consumes one more structured `SPEC-08` field directly instead of collapsing all region pressure to one total.
- New closure evidence:
  - `PerfSummaryReport` now carries `vmem_region_peak_bytes_by_backing_store`
  - performance-estimation now reuses `memory_plan.region_summaries[*].peak_bytes_by_backing_store` directly
- This batch deliberately does not introduce:
  - a deeper cycle model
  - block-level lifetime replay
  - per-storage-binding traffic accounting

## 2026-03-09 Bandwidth / VMEM Breakdown Checkpoint

- New plan: `../plans/2026-03-09-spec-13-bandwidth-vmem-breakdown.md`
- `SPEC-13` now exposes first-order bandwidth and VMEM pressure summaries on top of the already-landed schedule timing and occupancy signals.
- New closure evidence:
  - `PerfSummaryReport` now carries `data_movement_read_bytes_by_address_space`
  - `PerfSummaryReport` now carries `data_movement_write_bytes_by_address_space`
  - `PerfSummaryReport` now carries `vmem_region_peak_bytes`
  - `PerfSummaryReport` now carries `vmem_region_capacity_bytes`
  - `PerfSummaryReport` now carries `vmem_region_peak_utilization`
  - performance-estimation workflow now consumes `MemoryPlanArtifact` when building the summary report instead of only validating its presence
- This batch deliberately does not introduce:
  - a deeper cycle model
  - layer-level memory attribution
  - transport replay or exact physical traffic accounting

## 2026-03-09 Schedule Makespan Summary Checkpoint

- New plan: `../plans/2026-03-09-spec-13-schedule-makespan-summary.md`
- `SPEC-13` still uses descriptor-driven estimation, but `PerfSummaryReport` now exposes first-order schedule timing summary instead of only descriptor-local totals.
- New closure evidence:
  - `PerfSummaryReport` now carries `schedule_makespan_slots`
  - `PerfSummaryReport` now carries `per_core_makespan_slots`
  - `PerfSummaryReport` now carries `schedule_transfer_slots`
  - performance-estimation workflow now consumes the resolved `ScheduleIR` when building the summary report
- This batch deliberately does not introduce:
  - overlap-aware global critical-path accounting in perf totals
  - phase-level timeline aggregation
  - deeper cycle fitting beyond current descriptor estimation

## 2026-03-09 Schedule Timing Propagation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-duration-policy.md`
- `SPEC-13` still uses descriptor-driven estimation, but descriptor inputs now carry scheduler timing hints.
- New closure evidence:
  - descriptor `ctrl_fields` now carry `issue_slot`
  - descriptor `ctrl_fields` now carry `duration_slots`
  - descriptor analysis now treats `duration_slots` as a lower bound on `estimated_cycles`
- This batch deliberately does not introduce:
  - a schedule-aware global critical-path model
  - issue-slot-aware overlap accounting in perf totals
  - phase-level timeline aggregation inside `PerfSummaryReport`

## 2026-03-09 Schedule Occupancy Breakdown Checkpoint

- New plan: `../plans/2026-03-09-spec-13-schedule-occupancy-breakdown.md`
- `SPEC-13` now exposes schedule occupancy summaries on top of the already-landed makespan signal.
- New closure evidence:
  - `PerfSummaryReport` now carries `per_core_busy_slots`
  - `PerfSummaryReport` now carries `per_core_idle_slots`
  - `PerfSummaryReport` now carries `schedule_stage_slot_totals`
  - busy-slot accounting now uses merged block intervals per core, so overlap is preserved instead of being double-counted
- This batch deliberately does not introduce:
  - a deeper cycle model
  - layer-level occupancy views
  - per-resource utilization curves

## 2026-03-07 Checkpoint

- `SPEC-13` now has a stable descriptor-driven performance estimation foundation.
- `run-performance-estimation` is the standalone run-root workflow and CLI command for perf analysis artifacts.
- Gemma3 `single-core/dual-core x prefill/decode` smoke now produces deterministic performance artifacts for both scheduling kinds.

## 1. What Is Stable Now

The current `SPEC-13` foundation consumes:
- `artifacts/descriptor_ir.json`
- `reports/isa_coverage_report.json`
- `artifacts/memory_plan.json`
- `artifacts/schedule_ir.json` or `artifacts/dual_core_schedule_ir.json`
- target profile
- scenario profile

It produces:
- `artifacts/perf_analysis_ir.json`
- `reports/perf_summary_report.json`
- `manifest.artifact_index["perf_analysis_ir"]`
- `manifest.artifact_index["perf_summary_report"]`
- completed or failed `run-summary.json` updates through the performance-estimation workflow

This foundation is intentionally abstract and deterministic. It is designed for architecture evaluation, not RTL-faithful cycle simulation.

## 2. Stable Contract

The current `PerfSummaryReport` now carries:
- `run_id`
- `graph_id`
- `schedule_kind`
- `schedule_makespan_slots`
- `per_core_makespan_slots`
- `per_core_busy_slots`
- `per_core_idle_slots`
- `schedule_transfer_slots`
- `schedule_stage_slot_totals`
- `data_movement_read_bytes_by_address_space`
- `data_movement_write_bytes_by_address_space`
- `vmem_region_peak_bytes`
- `vmem_region_peak_bytes_by_backing_store`
- `vmem_region_capacity_bytes`
- `vmem_region_peak_utilization`
- `totals`
- `per_macro_cycles`
- `per_macro_bytes`
- `bottleneck_counts`
- `isa_gap_counts`
- `issues`

The current `perf_analysis_ir.json` uses `AnalysisIR` and now guarantees:
- one record per mapped descriptor
- explicit zero-metric records for ISA coverage gaps
- stable `subject_id = schedule_block_id`
- `descriptor-analysis` traceability tags and descriptor-linked `audit_ref`

## 3. Current Estimation Policy

The descriptor-driven estimator currently models:
- compute descriptors as abstract MXU/VPU work with positive cycle and byte estimates
- `dma_in` and `store` blocks as bandwidth-dominated transfers
- dual-core transfer blocks as sync-aware communication work
- ISA coverage gaps as explicit `isa-gap-bound` analysis records rather than silent drops

Current bottleneck tags:
- `compute-bound`
- `memory-bound`
- `sync-bound`
- `isa-gap-bound`

Current totals are summary-grade and comparable across runs, but not hardware-timed measurements.
Current timing summary is also intentionally conservative:
- schedule makespan is derived from `issue_slot + duration_slots`
- per-core makespan is derived independently per core id
- transfer slots count only explicit `transfer` stage occupancy
Current bandwidth / VMEM summary is also intentionally summary-grade:
- data movement is grouped by address space (`DDR` / `VMEM`) instead of by exact bus transaction
- VMEM pressure is grouped by planned region summary instead of replaying block-level lifetime overlap
- backing-store attribution is grouped by region-level peak summary instead of by exact block or storage-binding replay
- staged weight-family compute may contribute conservative external read pressure even when descriptor address fields stay abstract

## 4. What SPEC-14 And SPEC-15 Can Assume

Prefill and decode evaluation flows may now assume:
- scheduled runs can produce stable performance artifacts without re-deriving descriptor semantics
- single-core and dual-core runs share one summary contract
- ISA gaps are already surfaced inside performance outputs
- per-macro cycle and byte totals are available for report aggregation
- first-order bandwidth pressure can be read without reopening descriptor payloads
- first-order VMEM region pressure can be read without reopening raw memory-plan diagnostics

`SPEC-14/15` should not need to rediscover:
- which schedule kind produced the run
- whether a bottleneck came from compute, memory, sync, or ISA gaps
- whether dual-core handoff costs were represented

## 5. What Is Still Missing

The current `SPEC-13` foundation still lacks:
- tile- and memory-plan-aware deeper cycle models
- layer-level or token-phase attribution of bandwidth and VMEM pressure
- layer-level or token-phase aggregation views
- prefill/decode top-level evaluation reports
- sweep and delta-comparison integration

These are Phase D closure items, not reasons to reopen the current descriptor or scheduler contracts.

## 6. Recommended Next Step

Next work should keep moving forward inside Phase D:
1. Harden `SPEC-13` with richer perf/bandwidth breakdowns on top of current descriptor artifacts.
2. Start `SPEC-14` and `SPEC-15` using `PerfSummaryReport` as the stable aggregation input.
3. Delay sweep/UI work until perf outputs are stable enough for cross-run comparison.
