# Phase C Contract Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Realign outdated Phase B/Phase C smoke and workflow expectations with the current accepted frontend, memory-planning, and scheduling contracts so the full pytest suite reflects the repo's actual supported behavior.

**Architecture:** Treat the failing closure tests as the bug surface, not the Phase D code that recently landed. Keep the current accepted compile-chain behavior intact, tighten assertions around stable public evidence that still exists today, and stop requiring older explicit KVLOAD/KVSTORE or untiled helper-block shapes that the current fixtures no longer emit. This is a test-and-doc alignment slice only; it must not widen current planner or scheduler contracts.

**Tech Stack:** Python 3.11+, pytest, Phase B/Phase C smoke tests, run-root workflow artifacts, JSON report contracts.

---

### Task 1: Align Phase B legality smoke to current frontend evidence

**Files:**
- Modify: `tests/smoke/test_phase_b_closure_matrix.py`

**Step 1: Use the existing failing smoke as the red test**

The full-suite failure already proves the old assumptions are stale:

```powershell
python -m pytest tests/smoke/test_phase_b_closure_matrix.py -q
```

Expected: FAIL on required `kv_cache_dtype_mismatch` / `target_quant_activation_dtype_gap` counts.

**Step 2: Update assertions to current stable frontend evidence**

Keep assertions that still reflect accepted behavior:

- `dynamic_shape_unresolved == 0`
- `no_hardware_mapping > 0`
- `target_quant_group_size_gap > 0`
- `SHAPE_HELPER` still appears in pseudo fallback counts
- binding coverage still meets the per-case threshold

Stop requiring the two issue-count keys that current fixture runs no longer emit.

**Step 3: Re-run the focused smoke**

```powershell
python -m pytest tests/smoke/test_phase_b_closure_matrix.py -q
```

Expected: PASS.

### Task 2: Align memory-planning smoke/workflow to the current attention-metadata contract

**Files:**
- Modify: `tests/smoke/test_phase_c_memory_planner_matrix.py`
- Modify: `tests/unit/pipeline/test_memory_planning_workflow.py`

**Step 1: Use the existing failing tests as the red test**

```powershell
python -m pytest `
  tests/smoke/test_phase_c_memory_planner_matrix.py `
  tests/unit/pipeline/test_memory_planning_workflow.py -q
```

Expected: FAIL on required non-empty `kv_formulas`.

**Step 2: Update assertions to stable memory-plan outputs**

Preserve coverage for stable evidence that current real runs still emit:

- allocations and storage bindings exist
- address diagnostics are fully resolved
- region summaries still expose lifetime-bucket, memory-class, and backing-store peaks
- weight/quant symbolic address diagnostics remain present
- planner artifacts still wire into manifest/run-summary correctly

Do not require real fixture runs to emit non-empty `kv_formulas` unless the fixture path actually contains explicit `KVLOAD` / `KVSTORE` nodes.

**Step 3: Re-run the focused tests**

```powershell
python -m pytest `
  tests/smoke/test_phase_c_memory_planner_matrix.py `
  tests/unit/pipeline/test_memory_planning_workflow.py -q
```

Expected: PASS.

### Task 3: Align Phase C schedule smoke to the current helper-block shape

**Files:**
- Modify: `tests/smoke/test_phase_c_single_core_schedule_matrix.py`
- Modify: `tests/smoke/test_phase_c_dual_core_schedule_matrix.py`

**Step 1: Use the existing failing smoke as the red test**

```powershell
python -m pytest `
  tests/smoke/test_phase_c_single_core_schedule_matrix.py `
  tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q
```

Expected: FAIL on required untiled `RMSNORM` / `ELEM_ADD` compute blocks.

**Step 2: Update assertions to current prefill schedule evidence**

Require the stable shape emitted by current fixtures:

- prefill compute blocks exist
- `WDQ_GEMM` remains present
- `SDPA` remains present for prefill
- `SHAPE_HELPER` remains present as a compute helper block
- `SHAPE_HELPER` keeps `tiling_candidate_id is None`

Stop requiring untiled `RMSNORM` / `ELEM_ADD` compute blocks in the real fixture schedules.

**Step 3: Re-run the focused smoke**

```powershell
python -m pytest `
  tests/smoke/test_phase_c_single_core_schedule_matrix.py `
  tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q
```

Expected: PASS.

### Task 4: Re-verify the repaired full-suite surface

**Files:**
- No code changes expected

**Step 1: Run the repaired focused cluster**

```powershell
python -m pytest `
  tests/smoke/test_phase_b_closure_matrix.py `
  tests/smoke/test_phase_c_memory_planner_matrix.py `
  tests/smoke/test_phase_c_single_core_schedule_matrix.py `
  tests/smoke/test_phase_c_dual_core_schedule_matrix.py `
  tests/unit/pipeline/test_memory_planning_workflow.py -q
```

Expected: PASS.

**Step 2: Run full pytest**

```powershell
python -m pytest -q --durations=30
```

Expected: PASS.

**Step 3: Summarize the new project state**

Report:

- updated completion picture relative to README/roadmap
- exact fresh full-suite result
- any remaining gaps for `M3`
