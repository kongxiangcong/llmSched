# Phase C Single-Core Scheduler Handoff

## 2026-03-09 WDQ Prefix Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-wdq-prefix-specialization.md`
- `SPEC-10` now models `WDQ_GEMM` compute as a dequant-prefix-plus-matrix-body reservation shape instead of treating `MXU` as occupied from `issue_slot = 0`.
- New closure evidence:
  - `WDQ_GEMM` compute still reserves `WDQ` from offset `0`
  - `WDQ_GEMM` compute now reserves `MXU` only after the WDQ prefix completes
  - a later independent `GEMM` block may now fit before the `WDQ_GEMM` `MXU` body begins when dependencies allow it
  - public `ScheduleIR` stages remain unchanged; this batch is internal schedule-fidelity hardening only
- This batch still deliberately does not introduce:
  - new public schedule stages
  - cycle-calibrated `WDQ_GEMM` fitting
  - cost-based overlap search

## 2026-03-09 Interval Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-interval-resource-reservations.md`
- `SPEC-10` now keeps interval reservations as an internal scheduler primitive instead of collapsing every resource to a single `available_at` timestamp.
- New closure evidence:
  - single-core scheduling now permits a later `VPU` helper block to fit before a delayed `SDPA` `VPU` tail starts
  - resource-conflict checks now use sorted interval windows instead of whole-history linear scans
  - the ready queue now uses lazy earliest-issue heap scheduling instead of re-scanning the whole ready set on every step
  - the public `ScheduleIR` contract remains unchanged; this batch is internal overlap and runtime hardening only
- This batch still deliberately does not introduce:
  - new public schedule stages
  - global overlap search
  - cycle-calibrated engine timing

## 2026-03-09 Mixed-Engine Duration Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-mixed-engine-duration-specialization.md`
- `SPEC-10` no longer treats all GEMM-like compute macros as the same plain MXU duration surface.
- New closure evidence:
  - `WDQ_GEMM`, `RMSNORM_GEMM`, `SDPA`, and `SDPA_DECODE` now add explicit non-MXU overhead on top of the base GEMM compute cycles
  - schedule duration is now more consistent with the already-modeled mixed-engine reservations for these macros
  - focused scheduler/perf integration tests remain green with the stronger duration policy
- This batch still deliberately does not introduce:
  - cycle-calibrated compute fitting
  - new public schedule stages
  - layer-level timing attribution

## 2026-03-09 Vector Duration Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-vector-duration-specialization.md`
- `SPEC-10` now uses macro-specific vector-stage duration heuristics instead of one generic VPU formula for every helper macro.
- New closure evidence:
  - `RMSNORM`, `GEGLU`, `ROPE`, `ATTENTION_MASK_PREP`, and `LAYOUT_FALLBACK` now carry distinct stage-duration weights
  - `GEGLU` prepare/compute is now costlier than a generic helper prepare/compute of the same shape
  - focused scheduler/perf integration tests remain green with the stronger duration policy
- This batch still deliberately does not introduce:
  - cycle-calibrated duration fitting
  - dynamic schedule search
  - new public schedule stages

## 2026-03-09 GEGLU Resource Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-geglu-resource-specialization.md`
- `SPEC-10` now treats `GEGLU` compute as a mixed-engine scheduler surface instead of a pure `VPU` block.
- New closure evidence:
  - single-core `GEGLU` compute now emits `resource_set = ["MXU", "VPU"]`
  - `GEGLU` compute now reuses the phased reservation helper instead of reserving one engine class only
  - the public stage sequence stays stable as `dma_in -> prepare -> compute -> store`
- This batch still deliberately does not introduce:
  - a new public `GEGLU` sub-stage split
  - cycle-calibrated `GEGLU` duration fitting
  - a generic mixed-engine policy for every untiled helper macro

## 2026-03-09 Phased Engine Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-phased-engine-reservations.md`
- `SPEC-10` no longer reserves every compute resource for the whole block duration on selected mixed-engine macros.
- New closure evidence:
  - single-core scheduling now uses internal per-resource reservation windows instead of only whole-block occupancy
  - `SDPA` / `SDPA_DECODE` compute now releases `MXU` before the trailing `VPU` tail completes
  - a later `WDQ_GEMM` may now start on `MXU` during the `SDPA` VPU tail when dependencies allow it
  - the public `ScheduleIR` contract remains unchanged; this is an internal timing-fidelity upgrade only
- This batch still deliberately does not introduce:
  - new public schedule stages
  - alternative overlap search
  - cycle-calibrated micro-engine timing

## 2026-03-09 Duration Policy Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-duration-policy.md`
- `SPEC-10` now uses a shared stage-duration policy instead of hard-coding `duration_slots = 1`.
- New closure evidence:
  - tiled compute stages now emit non-unit duration based on tile shape and MXU/VPU throughput
  - `dma_in` / `store` stages now emit non-unit duration based on byte count and DMA bandwidth
  - `issue_slot` now advances against full producer occupancy, not only block count
- This batch still deliberately does not introduce:
  - cycle-accurate calibration
  - runtime overlap search
  - schedule-cost feedback into tile search

## 2026-03-09 Single-Core Overlap Checkpoint

- `SPEC-10` now distinguishes deterministic block order from actual issue timing.
- `ScheduleIR` blocks now carry:
  - `depends_on`
  - `issue_slot`
  - `duration_slots`
- single-core scheduling now uses a conservative earliest-issue policy:
  - intra-node stages remain ordered
  - producer-to-consumer dependencies gate `prepare` / `compute` and store-only consumers
  - resource-disjoint stages may overlap
- current scope is still intentionally narrow:
  - only single-core overlap is modeled in this batch
  - dual-core transfer/barrier overlap is still deferred

## 2026-03-09 Scheduler Fidelity Checkpoint

- `SPEC-10` now consumes `TileCandidate.rank` directly instead of re-deriving tile preference from `m_tile`.
- untiled but stable macro ops now still lower into `ScheduleIR`; they no longer disappear just because `SPEC-09` emitted no tile candidate.
- current untiled coverage now includes `RMSNORM`, `ELEM_ADD`, `GEGLU`, `ROPE`, `ATTENTION_MASK_PREP`, `EMBEDDING_LOOKUP`, `SHAPE_HELPER`, `LAYOUT_FALLBACK`, `ROPE_TABLE`, `KVLOAD`, and `KVSTORE`.
- Gemma3 single-core prefill smoke now asserts the schedule contains an untiled helper compute block with `tiling_candidate_id = null`; in the current audited fixture that visible helper surface is `SHAPE_HELPER`, while focused scheduler unit tests continue to cover `RMSNORM` / `ELEM_ADD`.

## 2026-03-07 Checkpoint

- `SPEC-10` has started with a stable first-pass single-core `ScheduleIR`.
- `run-single-core-scheduling` is now a standalone run-root workflow and CLI command.
- Gemma3 `single-core x prefill/decode` smoke now produces deterministic schedule artifacts.

## 1. What Is Stable Now

The current `SPEC-10` foundation consumes:
- `bound_nig_ir.json`
- `artifacts/memory_plan.json`
- `artifacts/tiling_plan.json`
- target profile
- scenario profile

It produces:
- `artifacts/schedule_ir.json`
- `manifest.artifact_index["schedule_ir"]`
- completed or failed `run-summary.json` updates through the single-core scheduling workflow

The scheduler is intentionally narrow. It does not yet search for overlap or do descriptor encoding.

## 2. Stable Contract

The extended `ScheduleIR` now carries scheduler-facing block metadata:
- `block_id`
- `core_id`
- `node_id`
- `macro_op`
- `stage`
- `tiling_candidate_id`
- `resource_set`
- `buffer_binding`
- `barrier_in`
- `barrier_out`
- `depends_on`
- `issue_slot`
- `duration_slots`
- `order_key`
- `audit_ref`

Single-core invariants now enforce:
- all blocks bind to exactly one core
- no `Core Link`
- no cross-core barrier usage

## 3. Current Scheduler Coverage

The single-core scheduler currently lowers:
- `GEMM`
- `WDQ_GEMM`
- `RMSNORM_GEMM`
- `RMSNORM`
- `ELEM_ADD`
- `GEGLU`
- `ROPE`
- `SDPA`
- `SDPA_DECODE`
- `ATTENTION_MASK_PREP`
- `EMBEDDING_LOOKUP`
- `SHAPE_HELPER`
- `LAYOUT_FALLBACK`
- `ROPE_TABLE`
- `KVLOAD`
- `KVSTORE`

Current stage policy:
- GEMM-like nodes: `dma_in -> compute -> store`
- attention nodes: `dma_in -> prepare -> compute -> store`
- untiled VPU/data-movement helpers use deterministic fixed stage templates and may carry `tiling_candidate_id = null`

Current resource policy:
- `WDQ_GEMM` compute uses `WDQ + MXU`
- `RMSNORM_GEMM` compute uses `VPU + MXU`
- `SDPA/SDPA_DECODE` compute uses `MXU + VPU`

## 4. What SPEC-12 Can Assume

Descriptor generation may now assume:
- tile choice is already frozen at `tiling_candidate_id`
- schedule blocks are already ordered deterministically
- single-core schedules never carry cross-core resources
- block-level `audit_ref` still points back to the originating NIG node

Descriptor generation should not need to rediscover:
- which tile candidate was selected
- which core a block belongs to
- whether a block is `dma_in`, `prepare`, `compute`, or `store`

## 5. What Is Still Missing

The remaining gap is now an acceptance boundary, not a broad missing-foundation list:
- global cost-based overlap search and calibrated pipelining remain out of the current `M2` scope
- descriptor-facing field packing belongs to `SPEC-12`, not to the scheduler
- current `M2` closure hinges on keeping the conservative phased-reservation / occupancy contract stable for downstream consumers

What is now present is intentionally not global overlap search. It is a conservative overlap foundation with explicit occupancy metadata and a completed helper-store audit batch.

These are `SPEC-10` acceptance items or `SPEC-12` work, not reasons to reopen the tile or memory contracts.

## 6. Recommended Next Step

Next work should keep the single-core scheduler in closure mode:
1. Freeze the current single-core `ScheduleIR` contract as the accepted Phase C scheduler surface.
2. Let descriptor / perf layers consume the current occupancy and reservation signal without reopening scheduler policy by default.
3. Reopen scheduler specialization only if a concrete downstream consumer exposes a real mismatch.

## 2026-03-09 Overhead-Aligned Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-overhead-aligned-reservations.md`
- `SPEC-10` now aligns selected mixed-engine reservation windows with the already-landed duration-overhead model instead of using one quarter-split fallback everywhere.
- New closure evidence:
  - `RMSNORM_GEMM` compute now reserves `VPU` for the true norm-prefix window and delays `MXU` occupancy until that prefix completes
  - `SDPA` / `SDPA_DECODE` compute now reserve `MXU` for the true GEMM body and reserve `VPU` only for the true attention-tail window
  - single-core scheduling now precomputes per-block reservation windows and consumes them directly during interval scheduling instead of recomputing coarse reservations at issue time
  - helper work around `SDPA` now respects the earlier explicit `VPU` tail boundary, while helper `prepare` may still fit before that tail if dependencies allow it
- This batch still deliberately does not introduce:
  - new public schedule stages
  - cycle-calibrated micro-engine timing
  - cost-based overlap search

## 2026-03-09 DMA Window Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-dma-window-specialization.md`
- `SPEC-10` now hardens DMA-neighborhood timing instead of only compute-neighborhood timing.
- New closure evidence:
  - `WDQ_GEMM.dma_in` now models `DMA` transport separately from a short quant-staging `WDQ` tail
  - `KVSTORE.store` now models a `VPU` pack/layout prefix before `DMA` writeback begins
  - interval scheduling can now place later independent DMA work inside those non-DMA windows when dependencies allow it
- This batch still deliberately does not introduce:
  - new public schedule stages
  - cycle-calibrated DMA timing
  - cost-based overlap search
