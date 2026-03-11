# Phase C Tile Planner Handoff

## 2026-03-09 Storage-Aware Search and Ranking Checkpoint

- New plan: `../plans/2026-03-09-spec-09-storage-aware-search-ranking.md`
- `TilingPlanArtifact` remains `in_progress`, but tile candidates now explicitly consume the `SPEC-08` storage-binding surface.
- `TileCandidateResourceSummary` now carries:
  - `storage_binding_ids`
  - `storage_read_bytes_by_source_kind`
  - `storage_read_bytes_by_backing_store`
- `TileCandidate` now carries:
  - `rank`
  - `ranking_reason`
- The planner now:
  - expands GEMM-like prefill search beyond the old first descending `M_tile` set
  - keeps staged `WEIGHT` / `QUANT_PARAM` reads fixed instead of scaling them with `M_tile`
  - emits deterministic per-node ranking for scheduler-facing tie-breaks

## 2026-03-07 Checkpoint

- `SPEC-09` has started with a stable first-pass `TilingPlanArtifact`.
- `run-tile-planning` is now a standalone run-root workflow and CLI command.
- Gemma3 `single-core/dual-core x prefill/decode` smoke now produces stable tiling artifacts.

## 2026-03-07 Single-Core Scheduler Transition

- `SPEC-09` remains `in_progress`, but it no longer blocks `SPEC-10`.
- The active Phase C mainline is now `bound-NIG -> MemoryPlanArtifact -> TilingPlanArtifact -> ScheduleIR`.
- Single-core scheduling should consume tile-planner artifacts rather than re-deriving tile choices from raw NIG.

## 1. What Is Stable Now

The current `SPEC-09` foundation consumes:
- `bound_nig_ir.json`
- `artifacts/memory_plan.json`
- target profile
- scenario profile

It produces:
- `artifacts/tiling_plan.json`
- `manifest.artifact_index["tiling_plan"]`
- completed or failed `run-summary.json` updates through the tile-planning workflow

The planner is intentionally narrow. It is not a scheduler and it is not trying to choose a final hardware execution order.

## 2. Stable Contract

`TilingPlanArtifact` currently carries:
- `graph_id`
- `scenario_name`
- `core_mode`
- `candidates`

Each `TileCandidate` currently carries:
- `candidate_id`
- `node_id`
- `macro_op`
- `strategy`
- `m_tile`
- `n_tile`
- `k_tile`
- `read_bytes`
- `write_bytes`
- `total_vmem_bytes`
- `quant_alignment_ok`
- `quant_alignment_message`
- `source_memory_plan_region_pressure`
- optional `resource_summary`
- optional `issues`

This is enough for Phase C to compare candidates before scheduling without recomputing memory pressure from raw NIG tensors.

## 3. Current Macro Coverage

The first-pass planner currently emits candidates for:
- `GEMM`
- `WDQ_GEMM`
- `RMSNORM_GEMM`
- `SDPA`
- `SDPA_DECODE`

Current policy:
- prefill GEMM-like paths emit a descending `M_tile` set derived from memory-plan fit
- decode attention defaults to `M_tile=1`
- `N_tile` is capped by MXU column width
- `K_tile` stays aligned to the current architecture default and quant binding

## 4. What SPEC-10 and SPEC-11 Can Assume

The next-stage scheduler may assume:
- bound-NIG shape/layout/quant binding already exists
- memory-plan region pressure already exists
- tile candidates already explain quant-alignment status
- decode attention already converges to latency-first candidates

The scheduler should not need to rediscover:
- whether a node is decode or prefill
- whether `group_size` aligns with the chosen `k_tile`
- what the memory-plan baseline pressure looked like

## 5. What Is Still Missing

The current planner still lacks:
- broader macro coverage outside GEMM-like and attention main paths
- richer candidate search beyond the first descending `M_tile` set
- explicit dual-core-aware tiling tradeoff modeling
- scheduler-facing preference ranking beyond basic resource summaries

These are `SPEC-09` closure items, not reasons to reopen frontend or memory-plan contracts.

## 6. Recommended Next Step

`SPEC-10` has now started. The next tile-planner-facing work should be:
1. Expand tile-candidate coverage to the remaining scheduling-relevant macro surfaces.
2. Add stronger ranking and explanation fields where the scheduler needs deterministic tie-breaking.
3. Keep `TilingPlanArtifact` stable as the input contract for `SPEC-10`, not as a place to hide scheduling policy.
