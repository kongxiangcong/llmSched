# SPEC-10/11 KVLOAD DMA Tail Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-10/11` schedule-fidelity modeling into the `KVLOAD.dma_in` neighborhood so shared `DMA` occupancy ends before local KV layout/unpack work finishes.

**Architecture:** Keep the public `ScheduleIR` artifact stable. Specialize the shared duration/reservation policy so `KVLOAD.dma_in` becomes a staged window with a shared-`DMA` transport body followed by a core-local `VPU` tail, then lock the overlap behavior with focused single-core and dual-core scheduler tests.

**Tech Stack:** Python 3.14, pytest, Typer CLI, Pydantic contracts, Markdown docs.

---

### Task 1: Add failing KVLOAD scheduler-fidelity tests

**Files:**
- Modify: `tests/unit/planning/test_schedule_duration.py`
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

- Add a duration/reservation test proving `KVLOAD.dma_in` emits a shared `DMA` window followed by a local `VPU` tail.
- Add a single-core scheduler test proving later independent `DMA` work may issue during the `KVLOAD` VPU tail.
- Add a dual-core scheduler test proving the same overlap survives shared-`DMA` contention across cores.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py -k kvload `
  tests/unit/planning/test_single_core_scheduler.py -k kvload `
  tests/unit/planning/test_dual_core_scheduler.py -k kvload -q
```

Expected: failures showing `KVLOAD.dma_in` still reserves shared `DMA` for the full block.

### Task 2: Implement `KVLOAD` DMA tail specialization

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Extend DMA stage timing**

- Add a `KVLOAD`-specific `dma_in` tail-slot helper derived from bound attention metadata or resolved shape.
- Include that tail in the shared `_dma_stage_slot_breakdown(...)`.

**Step 2: Extend reservation policy**

- Keep the transport prefix/body on shared `DMA`.
- Emit a later `VPU` tail reservation for the non-DMA layout/unpack window.

**Step 3: Re-run the focused tests**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py -k kvload `
  tests/unit/planning/test_single_core_scheduler.py -k kvload `
  tests/unit/planning/test_dual_core_scheduler.py -k kvload -q
```

Expected: PASS.

### Task 3: Record the checkpoint

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Add a short checkpoint entry**

- Summarize the new `KVLOAD.dma_in` specialization.
- State what `M2` gap it closes and what still remains.

### Task 4: Run focused verification and refresh progress evidence

**Files:**
- No code changes

**Step 1: Run focused regression**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py `
  tests/unit/planning/test_single_core_scheduler.py `
  tests/unit/planning/test_dual_core_scheduler.py `
  tests/unit/pipeline/test_frontend_analysis_workflow.py `
  tests/unit/pipeline/test_memory_planning_workflow.py `
  tests/unit/pipeline/test_tile_planning_workflow.py `
  tests/unit/pipeline/test_single_core_scheduling_workflow.py `
  tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q
```

Expected: PASS.

**Step 2: Refresh status evidence**

Run:

```powershell
python -m pytest --collect-only -q
git diff --check
```

Expected: updated collected test count and clean diff check.
