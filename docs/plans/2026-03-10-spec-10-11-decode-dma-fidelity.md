# SPEC-10/11 Decode DMA Fidelity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align `SDPA_DECODE` scheduling with the documented decode memory-bound model and document the recommended development-validation loop in the repository README.

**Architecture:** Keep the public `ScheduleIR` contract stable. Update the scheduler stage lowering and duration/reservation policy so decode attention uses `VPU + DMA` instead of the current `MXU + VPU` approximation, then lock the behavior with focused unit tests. Add a root `README.md` that points contributors to the fast local loop, workflow-focused checks, and smoke escalation path so full-suite runs stop being the default.

**Tech Stack:** Python 3.14, pytest, Typer CLI, Pydantic contracts, Markdown docs.

---

### Task 1: Add failing scheduler-fidelity tests

**Files:**
- Modify: `tests/unit/planning/test_schedule_duration.py`
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

- Add a duration/reservation test proving `SDPA_DECODE` compute reserves `DMA` and `VPU`, not `MXU`.
- Add a single-core scheduler test proving a same-core `WDQ_GEMM` compute block may overlap with `SDPA_DECODE` compute because decode no longer occupies `MXU`.
- Add a dual-core scheduler test proving the decode compute block on its assigned core exposes `["DMA", "VPU"]`.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py `
  tests/unit/planning/test_single_core_scheduler.py `
  tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected: failures showing `SDPA_DECODE` still uses `MXU` in duration/reservation or scheduler output.

### Task 2: Implement the decode scheduling model

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`
- Modify: `src/llm_sched/planning/single_core_scheduler.py`

**Step 1: Update stage lowering**

- Keep `SDPA` on `["MXU", "VPU"]`.
- Move `SDPA_DECODE` compute to `["DMA", "VPU"]`.

**Step 2: Refine duration and reservation policy**

- Give `SDPA_DECODE` a dedicated duration path derived from decode attention work plus streamed KV traffic.
- Emit reservation windows that hold `DMA` and `VPU` for the decode compute interval without reintroducing `MXU`.

**Step 3: Re-run the focused tests**

Run:

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py `
  tests/unit/planning/test_single_core_scheduler.py `
  tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected: PASS.

### Task 3: Document the development-validation ladder

**Files:**
- Create: `README.md`

**Step 1: Add concise contributor guidance**

- Explain the project purpose at a high level.
- Record the current phase focus (`M2`, `SPEC-10/11` hardening).
- Document the fast local loop, workflow-focused checks, and when to escalate to `local_smoke`, `milestone_matrix`, and full-suite runs.
- Explicitly state that `python -m pytest -q` is not the default loop.

**Step 2: Run a doc-safe verification command**

Run:

```powershell
python -m pytest tests/unit/contracts tests/unit/config tests/unit/arch tests/unit/ir tests/unit/frontend tests/unit/planning -q
```

Expected: PASS.

### Task 4: Run end-to-end verification and progress check

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
  tests/unit/pipeline/test_tile_planning_workflow.py -q
```

Expected: PASS.

**Step 2: Check project status evidence**

Run:

```powershell
python -m pytest --collect-only -q
git log --oneline -5
```

Expected: collected test count and recent checkpoint commits available for the closing summary.
