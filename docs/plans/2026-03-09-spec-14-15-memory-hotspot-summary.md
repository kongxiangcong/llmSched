# 2026-03-09 SPEC-14/15 Memory Hotspot Summary

## Goal

Push the existing prefill/decode top-level reports one step beyond pure throughput / latency aggregation by surfacing:
- dominant address-space pressure (`DDR` vs `VMEM`)
- hottest VMEM region and its peak utilization

This batch must stay top-level and summary-grade. It must not reopen raw descriptor semantics or create a new phase-local memory simulator.

## Scope

Production changes are limited to:
- `PrefillEvaluationReport`
- `DecodeEvaluationReport`
- `build_prefill_evaluation_report(...)`
- `build_decode_evaluation_report(...)`

The new surface is one `memory_hotspot` summary per top-level report.

## Summary Policy

### Address-space hotspot

Use the already-landed `PerfSummaryReport` fields:
- `data_movement_read_bytes_by_address_space`
- `data_movement_write_bytes_by_address_space`

Compute:
- a copied read map
- a copied write map
- one dominant address space chosen from combined read + write bytes

### VMEM hotspot

Use the already-landed `MemoryPlanArtifact.region_summaries` and expose:
- hottest region name
- hottest region peak bytes
- hottest region capacity bytes
- hottest region utilization

## Non-goals

This batch deliberately does not add:
- layer-level hotspot views
- token-phase hotspot views
- bus-accurate traffic replay
- cross-run compare logic

## Verification

Required gates:
- `tests/unit/contracts/test_prefill_report.py`
- `tests/unit/contracts/test_decode_report.py`
- `tests/unit/analysis/test_prefill_report_builder.py`
- `tests/unit/analysis/test_decode_report_builder.py`
- `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- `tests/smoke/test_phase_d_decode_foundation_matrix.py`

## Exit Condition

`SPEC-14` and `SPEC-15` can now answer:
- prefill/decode is more `DDR`-pressure-heavy or `VMEM`-pressure-heavy
- which VMEM region is the tightest

without forcing downstream UI / compare layers to reopen raw perf or memory-plan artifacts.
