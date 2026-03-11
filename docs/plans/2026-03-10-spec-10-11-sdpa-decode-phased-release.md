# SPEC-10/11 SDPA Decode Phased Release Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `SDPA_DECODE.compute` so `DMA` and `VPU` reservations use their true sub-window lengths instead of both occupying the full decode compute block.

**Architecture:** Keep the public `ScheduleIR` contract unchanged. Reuse the shared duration policy to compute the decode block makespan as `max(DMA, VPU)` while changing internal reservations so each engine is only held for its own modeled span, then prove the stronger overlap behavior with focused single-core and dual-core scheduler tests.

**Tech Stack:** Python 3.14, pytest, Typer CLI, Pydantic contracts, Markdown docs.

---

### Task 1: Add failing decode reservation tests

**Files:**
- Modify: `tests/unit/planning/test_schedule_duration.py`
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

- Tighten the decode reservation test so `VPU` is no longer allowed to reserve the full `SDPA_DECODE.compute` duration when the decode path is `DMA`-dominated.
- Add a single-core scheduler test proving a later same-core `VPU` helper may start during the decode compute `DMA` tail once `VPU` is released.
- Add a dual-core scheduler test proving the same core-local `VPU` reuse survives dual-core scheduling and cross-core dependency handling.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py -k sdpa_decode `
  tests/unit/planning/test_single_core_scheduler.py -k sdpa_decode `
  tests/unit/planning/test_dual_core_scheduler.py -k sdpa_decode -q
```

Expected: failures showing `SDPA_DECODE.compute` still reserves `DMA` and `VPU` for the full block.

### Task 2: Implement `SDPA_DECODE` phased release

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Add decode-specific reservation logic**

- Recompute the decode `DMA` and `VPU` slot counts inside `estimate_stage_resource_reservations(...)`.
- Keep block duration as `max(DMA, VPU)`, but emit per-engine reservations using the true slot count of each engine.

**Step 2: Re-run the focused tests**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py -k sdpa_decode `
  tests/unit/planning/test_single_core_scheduler.py -k sdpa_decode `
  tests/unit/planning/test_dual_core_scheduler.py -k sdpa_decode -q
```

Expected: PASS.

### Task 3: Record the checkpoint

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Add a short checkpoint entry**

- Summarize the new decode phased-release behavior.
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
