# 2026-03-09 SPEC-10/11 Scheduler Fidelity And Coverage

## Goal

Close the first high-value scheduler fidelity gap after `SPEC-09` storage-aware ranking:

- schedulers must consume `TileCandidate.rank` instead of re-deriving their own preference
- untiled but stable NIG macro ops must still lower into `ScheduleIR`
- dual-core handoff semantics must continue to hold for untiled nodes

This batch intentionally does not add overlap search or global partition optimization.

## Scope

In scope:

- switch single-core and dual-core candidate selection to `rank`-first
- keep deterministic tie-break on `candidate_id`
- allow schedule emission when a node has stage policy but no tile candidate
- add stage policies for stable untiled macro ops:
  - `RMSNORM`
  - `ELEM_ADD`
  - `GEGLU`
  - `ROPE`
  - `ATTENTION_MASK_PREP`
  - `EMBEDDING_LOOKUP`
  - `SHAPE_HELPER`
  - `LAYOUT_FALLBACK`
  - `ROPE_TABLE`
  - `KVLOAD`
  - `KVSTORE`
- preserve dual-core `transfer` insertion across untiled nodes

Out of scope:

- overlap search
- resource pipelining
- smarter dual-core partition optimization
- descriptor packing changes

## TDD Entry

Red tests added first:

1. single-core prefers `rank=1` candidate even when it is not the largest `m_tile`
2. dual-core prefers `rank=1` candidate even when it is not the largest `m_tile`
3. single-core schedules untiled `RMSNORM` / `ELEM_ADD` / `KVLOAD` / `KVSTORE`
4. dual-core schedules untiled `RMSNORM` / `ELEM_ADD` and still inserts `transfer`

## Exit Criteria

- focused scheduler unit tests are green
- real Gemma3 single-core and dual-core smoke gates show untiled compute blocks in prefill schedules
- scheduler handoff docs no longer describe coverage as GEMM/attention-only
