# 2026-03-09 SPEC-13 Schedule Occupancy Breakdown

## Goal

Extend `PerfSummaryReport` so Phase D can consume the stronger `ScheduleIR` timing signal already produced by Phase C.

This batch is intentionally narrow:
- no new cycle model
- no new descriptor math
- no layer-level aggregation

## Scope

Add schedule-derived summary fields:
- `per_core_busy_slots`
- `per_core_idle_slots`
- `schedule_stage_slot_totals`

These fields should be derived directly from `issue_slot + duration_slots` and preserve overlap.

## Why This Batch

The scheduler now models:
- interval reservations
- mixed-engine reservation windows
- DMA-neighborhood windows

But `PerfSummaryReport` still only exposes:
- global makespan
- per-core makespan
- transfer slots

That is enough for a coarse top-line summary, but not enough to explain whether the stronger timing model is creating:
- more overlap
- more core slack
- stage-shape changes in DMA / prepare / compute / store balance

## Intended Semantics

- `per_core_busy_slots`
  - union length of all scheduled block intervals per core
- `per_core_idle_slots`
  - `schedule_makespan_slots - per_core_busy_slots[core]`
- `schedule_stage_slot_totals`
  - simple duration sum by stage across all blocks

## Non-Goals

- no overlap-aware critical-path cycle recomputation
- no VMEM-region-specific bandwidth breakdown yet
- no per-layer/token-phase occupancy views yet

## Validation

- contract coverage in `tests/unit/contracts/test_perf_report.py`
- builder coverage in `tests/unit/analysis/test_perf_summary_builder.py`
- workflow coverage in `tests/unit/pipeline/test_performance_estimation_workflow.py`
