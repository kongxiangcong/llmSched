# SPEC-10/11 Embedding DMA Tail Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-10/11` schedule-fidelity hardening by modeling `EMBEDDING_LOOKUP.dma_in` as shared `DMA` transport followed by a core-local `VPU` unpack/scale tail.

**Architecture:** Keep scheduler lowering unchanged and specialize only duration/reservation policy in `schedule_duration.py`. Add focused red-green tests in `test_schedule_duration.py`, `test_single_core_scheduler.py`, and `test_dual_core_scheduler.py` so both interval schedulers prove that later DMA work can start once the embedding DMA window closes, without waiting for the full block duration.

**Tech Stack:** Python 3.14, pytest, Pydantic IR/contracts, Markdown docs.

## Outcome

- Status: completed on 2026-03-10
- Implementation:
  - `EMBEDDING_LOOKUP.dma_in` now models shared `DMA` transport followed by a core-local `VPU` tail in `src/llm_sched/planning/schedule_duration.py`
  - no scheduler lowering changes were needed; single-core and dual-core schedulers consumed the refined reservations automatically
- Verification:
  - red: `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k embedding`
    - result before implementation: `3 failed`
  - green: same command
    - result after implementation: `3 passed, 42 deselected in 0.63s`
  - regression: `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
    - result: `45 passed in 0.83s`
  - workflow regression: `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
    - result: `11 passed in 19.03s`
- Notes:
  - this closes another concrete `prepare / store / DMA`-adjacent fidelity gap without adding a new foundation layer
  - the local workflow gate remains cheap enough to keep iterating on `SPEC-10/11`

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `tests/unit/planning/test_schedule_duration.py`
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Add a duration-policy regression test**

- Add a new `schedule_duration` test that expects `EMBEDDING_LOOKUP.dma_in` reservations to split into:
  - a leading `DMA` window
  - a trailing `VPU` window
- Assert the `DMA` window ends before the full block duration.

**Step 2: Add scheduler overlap regressions**

- Single-core:
  - schedule `EMBEDDING_LOOKUP` plus an independent `ROPE_TABLE`
  - assert the later `ROPE_TABLE.dma_in` starts at the end of the embedding DMA window, not at the end of the full block
- Dual-core:
  - same behavioral assertion under shared-DMA contention across cores

**Step 3: Run the tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py `
  tests/unit/planning/test_single_core_scheduler.py `
  tests/unit/planning/test_dual_core_scheduler.py -q -k embedding
```

Expected: FAIL because `EMBEDDING_LOOKUP.dma_in` is still modeled as a full-block `DMA` reservation.

### Task 2: Implement the phased tail specialization

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Add an embedding-tail slot helper**

- Compute a small but non-zero `VPU` tail for `EMBEDDING_LOOKUP.dma_in`.
- Base it on the resolved embedding output working-set, not on a fixed constant.

**Step 2: Feed that helper into duration and reservation policy**

- Extend `_dma_stage_slot_breakdown(...)` for `EMBEDDING_LOOKUP.dma_in`
- Extend `estimate_stage_resource_reservations(...)` so the block reserves:
  - `DMA` first
  - `VPU` second

**Step 3: Re-run the focused tests**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py `
  tests/unit/planning/test_single_core_scheduler.py `
  tests/unit/planning/test_dual_core_scheduler.py -q -k embedding
```

Expected: PASS.

### Task 3: Re-run the main planning regression slice

**Files:**
- No code changes

**Step 1: Re-run the scheduler-focused regression gate**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py `
  tests/unit/planning/test_single_core_scheduler.py `
  tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected: PASS.

### Task 4: Refresh progress evidence

**Files:**
- Modify: `docs/plans/2026-03-10-spec-10-11-embedding-dma-tail-specialization.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Record the implementation outcome**

- Add the actual red-green verification results to the plan doc.
- Add a roadmap checkpoint describing the new `EMBEDDING_LOOKUP` DMA-neighborhood specialization.

**Step 2: Refresh inventory and diff hygiene**

Run:

```powershell
python -m pytest --collect-only -q
git diff --check
```

Expected: updated collected-test count and only the existing CRLF warnings in diff hygiene.
