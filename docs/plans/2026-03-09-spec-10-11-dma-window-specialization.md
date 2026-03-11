# 2026-03-09 SPEC-10/11 DMA Window Specialization

## Goal

Harden scheduler timing fidelity in the `prepare / store / DMA` neighborhood without changing the public `ScheduleIR` surface.

This batch focuses on two narrow cases:
- `WDQ_GEMM.dma_in`
  - model DMA transport separately from quant staging tail
- `KVSTORE.store`
  - model pack/format prefix separately from DMA writeback

## Why This Batch

The current interval scheduler already handles phased reservations for mixed-engine `compute`, but `dma_in` and `store` still behave like coarse whole-block `DMA` occupancy.

That leaves two visible fidelity gaps:
- later DMA work cannot overlap with post-transport local staging on `WDQ_GEMM`
- later DMA work cannot start before `KVSTORE` reaches its actual DMA write window

## Intended Behavior

- `WDQ_GEMM.dma_in`
  - total stage duration remains one block
  - `DMA` is reserved first
  - `WDQ` remains reserved for a short tail after `DMA` transport completes
- `KVSTORE.store`
  - total stage duration remains one block
  - `VPU` is reserved first for pack/layout work
  - `DMA` starts only after that prefix

## Non-Goals

- no new public schedule stages
- no cost-based overlap search
- no cycle-calibrated DMA micro-model
- no reopening of frontend, tiling, or descriptor contracts

## Validation

- new unit coverage in `tests/unit/planning/test_schedule_duration.py`
- single-core scheduler overlap regression coverage in `tests/unit/planning/test_single_core_scheduler.py`
- dual-core scheduler overlap regression coverage in `tests/unit/planning/test_dual_core_scheduler.py`
