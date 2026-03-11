# 2026-03-09 SPEC-13 Bandwidth / VMEM Breakdown

## Goal

Push `SPEC-13` one step past schedule occupancy summary by adding summary-grade:
- data-movement bytes grouped by address space
- VMEM region peak/capacity/utilization grouped by region

This batch must stay report-level. It must not introduce a deeper cycle model, layer-level attribution, or a new low-level memory simulator.

## Scope

Production changes are limited to:
- `PerfSummaryReport`
- `build_perf_summary_report(...)`
- `run-performance-estimation`

The new fields are:
- `data_movement_read_bytes_by_address_space`
- `data_movement_write_bytes_by_address_space`
- `vmem_region_peak_bytes`
- `vmem_region_capacity_bytes`
- `vmem_region_peak_utilization`

## Aggregation Policy

### Address-space movement

Use summary-grade aggregation only:
- explicit `dma_in` / `store` / `transfer` address fields are the first source of truth
- bytes are attributed to unique address spaces per read-side or write-side role
- if a compute descriptor is a staged-weight macro family, add a conservative DDR read estimate for the weight-side fetch

This is intended to answer:
- is movement pressure mainly `DDR` or `VMEM`
- is the current bottleneck signal compute-like or transport-like

It is not intended to prove exact physical traffic.

### VMEM breakdown

Consume `MemoryPlanArtifact.region_summaries` and expose:
- peak bytes
- capacity bytes
- peak utilization

This is intended to answer:
- which VMEM region is tight
- whether pressure is concentrated in ping/pong/weight-like regions

## Non-goals

This batch deliberately does not include:
- layer-level memory attribution
- block-level traffic replay
- cycle-calibrated DDR timing
- backing-store-specific critical-path fitting

## Verification

Required gates:
- `tests/unit/contracts/test_perf_report.py`
- `tests/unit/analysis/test_perf_summary_builder.py`
- `tests/unit/pipeline/test_performance_estimation_workflow.py`
- `tests/smoke/test_phase_d_perf_foundation_matrix.py`
- downstream `prefill` / `decode` workflow readers stay green

## Exit Condition

`PerfSummaryReport` becomes a stable downstream input for:
- `SPEC-14`
- `SPEC-15`
- later `SPEC-16` compare surfaces

without requiring those layers to reopen raw `MemoryPlanArtifact` or raw `DescriptorIR` just to answer first-order bandwidth / VMEM questions.
