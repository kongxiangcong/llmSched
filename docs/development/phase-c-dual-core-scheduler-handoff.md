# Phase C Dual-Core Scheduler Handoff

## 2026-03-09 WDQ Prefix Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-wdq-prefix-specialization.md`
- `SPEC-11` now consumes the same `WDQ_GEMM` prefix-aware reservation shape as `SPEC-10`.
- New closure evidence:
  - dual-core scheduling now reserves `WDQ` from offset `0` but delays `MXU` occupancy until the WDQ prefix completes
  - a later independent core-local `GEMM` block may now fit before the `WDQ_GEMM` `MXU` body begins on the same core
  - transfer/barrier semantics remain unchanged while the stronger local compute reservation model stays internal
  - public `ScheduleIR` contract remains unchanged; this batch is timing-fidelity hardening only
- This batch still deliberately does not introduce:
  - repartition search
  - cycle-calibrated `WDQ_GEMM` fitting
  - new public schedule stages

## 2026-03-09 Interval Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-interval-resource-reservations.md`
- `SPEC-11` now uses the same interval-reservation scheduler core as `SPEC-10` instead of collapsing every resource to one scalar availability boundary.
- New closure evidence:
  - dual-core scheduling now permits later core-local `VPU` helper work to fit before a delayed `SDPA` `VPU` tail starts on the same core
  - transfer/sync reservations continue to coexist with the new interval model without changing the public `transfer` block contract
  - resource-conflict checks now use sorted interval windows plus lazy ready-heap recomputation instead of whole-ready-set rescans
  - the public `ScheduleIR` contract remains unchanged; this batch is internal overlap and runtime hardening only
- This batch still deliberately does not introduce:
  - repartition search
  - new public schedule stages
  - cycle-calibrated engine timing

## 2026-03-09 Mixed-Engine Duration Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-mixed-engine-duration-specialization.md`
- `SPEC-11` now consumes the same mixed-engine compute duration policy as `SPEC-10`.
- New closure evidence:
  - dual-core schedules now inherit explicit compute overhead for `WDQ_GEMM`, `RMSNORM_GEMM`, `SDPA`, and `SDPA_DECODE`
  - dual-core scheduler and perf-facing tests remain green with the stronger duration policy
  - no public dual-core schedule contract changes were required
- This batch still deliberately does not introduce:
  - cycle-calibrated compute fitting
  - repartition search
  - layer-level timing attribution

## 2026-03-09 Vector Duration Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-vector-duration-specialization.md`
- `SPEC-11` now consumes the same macro-specific vector-stage duration heuristics as `SPEC-10`.
- New closure evidence:
  - dual-core schedules now inherit specialized duration weights for `RMSNORM`, `GEGLU`, `ROPE`, `ATTENTION_MASK_PREP`, and `LAYOUT_FALLBACK`
  - dual-core scheduler and downstream perf-facing tests remain green with the stronger duration policy
  - no public dual-core schedule contract changes were required
- This batch still deliberately does not introduce:
  - cycle-calibrated duration fitting
  - repartition search
  - new public schedule stages

## 2026-03-09 GEGLU Resource Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-geglu-resource-specialization.md`
- `SPEC-11` now mirrors the single-core `GEGLU` mixed-engine compute policy in dual-core scheduling.
- New closure evidence:
  - dual-core `GEGLU` compute now emits `resource_set = ["MXU", "VPU"]`
  - `GEGLU` compute now participates in the same phased reservation helper used for other mixed-engine compute blocks
  - deterministic core assignment and transfer insertion stay unchanged
- This batch still deliberately does not introduce:
  - a new public `GEGLU` sub-stage split
  - repartition search
  - cycle-calibrated `GEGLU` duration fitting

## 2026-03-09 Phased Engine Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-phased-engine-reservations.md`
- `SPEC-11` now applies the same phased engine reservation policy used by `SPEC-10` for selected mixed-engine compute macros.
- New closure evidence:
  - dual-core scheduling now uses internal per-resource reservation windows for compute blocks instead of reserving every engine for the full block lifetime
  - `SDPA` / `SDPA_DECODE` compute now releases the core-local `MXU` before the trailing `VPU` tail completes
  - later core-local `WDQ_GEMM` work may now start during the `SDPA` VPU tail when dependencies allow it
  - shared transfer/sync timing remains compatible with the new compute-side reservation model
- This batch still deliberately does not introduce:
  - new public schedule stages
  - repartition search
  - cycle-calibrated micro-engine timing

## 2026-03-09 Shared Sync Overlap Checkpoint

- New plan: `../plans/2026-03-09-spec-11-shared-sync-overlap.md`
- `SPEC-11` still keeps one `transfer` block per cross-core handoff, but transfer occupancy is no longer modeled as one monolithic reservation.
- New closure evidence:
  - dual-core scheduling now treats transfer transport occupancy and sync-tail occupancy as separate internal reservations
  - `Core Link` or `DMA` transport resources may be released before the transfer block fully ends when only sync tail remains
  - shared sync timing is now modeled explicitly through an internal shared sync resource instead of being folded into transport contention alone
  - workflow and Phase C dual-core smoke remain green with the stronger timing policy
- This batch still deliberately does not introduce:
  - new `ScheduleIR` block kinds
  - transport choice search
  - cost-based repartitioning

## 2026-03-09 Duration Policy Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-duration-policy.md`
- `SPEC-11` now uses the same shared stage-duration policy as `SPEC-10` instead of hard-coding `duration_slots = 1`.
- New closure evidence:
  - transfer blocks now carry non-unit occupancy from transport bandwidth plus sync cost
  - dual-core compute and DMA stages now carry non-unit occupancy derived from tile shape or byte count
  - shared `DMA` / `Core Link` contention now interacts with real occupancy instead of 1-slot placeholders
- This batch still deliberately does not introduce:
  - transport choice search
  - cycle-calibrated duration fitting
  - repartition search

## 2026-03-09 Dual-Core Overlap Checkpoint

- New plan: `../plans/2026-03-09-spec-11-dual-core-overlap-foundation.md`
- `SPEC-11` now has a conservative overlap/occupancy foundation instead of a pure append-only block sequence.
- New closure evidence:
  - dual-core `ScheduleIR` blocks now carry meaningful `depends_on`
  - dual-core schedules now emit non-trivial `issue_slot` timing
  - transfer blocks now depend on the producer terminal stage instead of floating free
  - consumer `prepare/compute` stages now wait on a cross-core transfer block when the producer lives on the other core
  - shared `DMA` and `Core Link` contention is now reflected through scheduler resource keys
- This batch deliberately still does not introduce:
  - repartition search
  - cost-based `DMA` versus `Core Link` choice
  - cycle-calibrated duration modeling

## 2026-03-09 Scheduler Fidelity Checkpoint

- `SPEC-11` now consumes `TileCandidate.rank` directly instead of re-sorting by tile shape.
- untiled but stable macro ops now still lower into dual-core `ScheduleIR`; they no longer vanish when no tile candidate exists.
- transfer insertion remains explicit for untiled cross-core producer-consumer handoff.
- Gemma3 dual-core prefill smoke now asserts the schedule contains untiled compute blocks such as `RMSNORM` or `ELEM_ADD`.

## 2026-03-07 Checkpoint

- `SPEC-11` has started with a stable first-pass dual-core `ScheduleIR`.
- `run-dual-core-scheduling` is now a standalone run-root workflow and CLI command.
- Gemma3 `dual-core x prefill/decode` smoke now produces deterministic dual-core schedule artifacts.

## 1. What Is Stable Now

The current `SPEC-11` foundation consumes:
- `bound_nig_ir.json`
- `artifacts/memory_plan.json`
- `artifacts/tiling_plan.json`
- target profile
- scenario profile

It produces:
- `artifacts/dual_core_schedule_ir.json`
- `manifest.artifact_index["dual_core_schedule_ir"]`
- completed or failed `run-summary.json` updates through the dual-core scheduling workflow

The scheduler is intentionally narrow. It does not yet do overlap search or global partition optimization.

## 2. Stable Contract

The extended dual-core `ScheduleIR` now carries:
- `block_id`
- `core_id`
- `peer_core_id`
- `node_id`
- `macro_op`
- `stage`
- `tiling_candidate_id`
- `resource_set`
- `buffer_binding`
- `barrier_in`
- `barrier_out`
- `transfer_kind`
- `transfer_bytes`
- `sync_cost_cycles`
- `order_key`
- `audit_ref`

Dual-core invariants now enforce:
- `transfer` blocks must declare both `barrier_in` and `barrier_out`
- `transfer` blocks must declare `peer_core_id`
- `peer_core_id` must differ from the source `core_id`
- `transfer` blocks must declare `transfer_kind` and positive `transfer_bytes`
- `Core Link` usage is valid only in dual-core schedules

## 3. Current Scheduler Coverage

The dual-core scheduler currently lowers:
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

Current policy:
- supported nodes are assigned deterministically across core 0 and core 1
- a `transfer` block is inserted for explicit cross-core producer-consumer handoff
- transfer resource selection prefers `Core Link` when enabled and falls back to `DMA`
- stage lowering mirrors the single-core foundation once a node is assigned to a core
- ready blocks are issued with a conservative earliest-issue scheduler instead of raw append order
- shared `DMA` and shared `Core Link` are modeled as globally contended resources
- transfer scheduling now models transport occupancy and sync-tail occupancy separately while keeping one stable `transfer` block in the public artifact
- untiled helper nodes may carry `tiling_candidate_id = null` while still participating in core assignment and transfer insertion

## 4. What SPEC-12 Can Assume

Descriptor generation may now assume:
- tile choice is already frozen at `tiling_candidate_id`
- each scheduled block already belongs to a concrete core
- cross-core handoff points are explicit `transfer` blocks
- dual-core barrier boundaries are already materialized in the schedule artifact
- block-level `audit_ref` still points back to the originating NIG node set

Descriptor generation should not need to rediscover:
- which node moved across cores
- whether the transfer uses `Core Link` or `DMA`
- where barrier boundaries must be inserted

## 5. What Is Still Missing

The remaining gap is now an acceptance boundary, not a broad missing-foundation list:
- smarter repartition search and cost-aware `DMA` versus `Core Link` choice remain outside the current `M2` scope
- descriptor-facing field packing belongs to `SPEC-12`, not to the scheduler
- current `M2` closure hinges on keeping the present transfer/sync-aware overlap contract stable for downstream consumers

What is now present is intentionally not global repartition search. It is a deterministic dual-core scheduler with explicit overlap, transfer, sync, and helper-store audit coverage.

These are `SPEC-11` acceptance items or `SPEC-12` work, not reasons to reopen the memory or tiling contracts.

## 6. Recommended Next Step

Next work should keep the dual-core scheduler in closure mode:
1. Freeze the current dual-core `ScheduleIR` contract as the accepted Phase C dual-core surface.
2. Let descriptor / perf layers consume the current overlap, transfer, and sync signal without reopening partition/search policy by default.
3. Reopen dual-core scheduler specialization only if a concrete downstream consumer exposes a real mismatch.

## 2026-03-09 Overhead-Aligned Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-overhead-aligned-reservations.md`
- `SPEC-11` now consumes the same overhead-aligned mixed-engine reservation windows as `SPEC-10` instead of relying on one quarter-split fallback for all mixed-engine compute.
- New closure evidence:
  - `RMSNORM_GEMM` compute now keeps `VPU` occupied only for the true norm-prefix window before `MXU` body execution on the assigned core
  - `SDPA` / `SDPA_DECODE` compute now expose the true `MXU` body plus `VPU` tail split on the assigned core
  - dual-core scheduling now precomputes per-block reservation windows and feeds them directly into the shared interval scheduler, including transfer blocks
  - helper work on the same core now respects the explicit earlier `VPU` tail boundary while still allowing pre-tail `prepare` work when dependencies permit
- This batch still deliberately does not introduce:
  - repartition search
  - new public schedule stages
  - cycle-calibrated micro-engine timing

## 2026-03-09 DMA Window Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-dma-window-specialization.md`
- `SPEC-11` now hardens the same DMA-neighborhood windows as `SPEC-10`, not only mixed-engine compute windows.
- New closure evidence:
  - `WDQ_GEMM.dma_in` now exposes a `DMA` transport phase followed by a short `WDQ` tail on the assigned core
  - `KVSTORE.store` now exposes a `VPU` pack/layout prefix before shared `DMA` writeback begins
  - dual-core interval scheduling can now place later shared-DMA work inside those non-DMA windows when dependencies allow it
- This batch still deliberately does not introduce:
  - repartition search
  - new public schedule stages
  - cycle-calibrated DMA timing
