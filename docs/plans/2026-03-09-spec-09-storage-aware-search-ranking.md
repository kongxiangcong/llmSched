# SPEC-09 Storage-Aware Search and Ranking

## Goal

Push `SPEC-09` from the current deterministic foundation to a richer tile-candidate search/ranking pass that explicitly consumes the `SPEC-08` storage-binding surface instead of treating all input bytes as one undifferentiated pool.

## Scope

In scope:
- expand prefill candidate search beyond the current first descending `M_tile` set
- make candidate resource summaries storage-aware
- stop scaling staged `WEIGHT` / `QUANT_PARAM` reads as if they were activation traffic
- add deterministic per-node ranking fields that later schedulers can consume

Out of scope:
- final scheduler policy
- dual-core execution-order heuristics
- descriptor/ISA-level packing changes
- traffic/cycle-accurate modeling

## Contract Changes

Extend `TileCandidateResourceSummary` with:
- `storage_binding_ids`
- `storage_read_bytes_by_source_kind`
- `storage_read_bytes_by_backing_store`

Extend `TileCandidate` with:
- `rank`
- `ranking_reason`

The contract should remain scheduler-friendly:
- ranking is deterministic
- rank `1` means the preferred candidate for the current node/scenario
- storage-aware summaries stay explanatory, not target-specific encodings

## Planner Changes

1. Build a `storage_bindings_by_id` lookup from `MemoryPlanArtifact`.
2. Expand GEMM-like prefill search space to include a richer descending set such as:
   - base fit candidate
   - next lower MXU-friendly candidates
   - additional intermediate candidate(s) like `24` / `12` when fit allows
3. Keep decode attention latency-first with `M_tile=1`.
4. Compute resource summaries with storage-aware accounting:
   - activation bytes scale with `M_tile`
   - staged weight/quant bytes do not scale with `M_tile`
   - persistent/storage-tagged reads are broken out by source kind and backing-store kind
5. Rank candidates deterministically per node and attach `rank` plus `ranking_reason`.

## Validation

- unit contract tests for new rank/storage summary fields
- planner tests showing:
  - richer prefill candidate set
  - staged weight/quant bytes remain constant across `M_tile`
  - rank ordering is deterministic
- workflow/smoke tests showing new fields persist in `tiling_plan.json`

## Expected Outcome

After this batch:
- `SPEC-09` no longer treats staged weight/quant bytes like scaled activation traffic
- `TilingPlanArtifact` becomes a better input contract for `SPEC-10/11`
- the next `M2` closure work can focus on schedule fidelity rather than reopening tile-candidate semantics
