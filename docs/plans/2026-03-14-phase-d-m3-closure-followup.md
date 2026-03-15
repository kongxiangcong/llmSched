# Phase D M3 Closure Follow-up Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Record the current audited state, restore full-regression closure, and continue Phase D work strictly in roadmap To Do order.

**Architecture:** Keep `docs/development/evaluation-compiler-roadmap.md` as the only project-status source and use this plan as the execution queue. First repair the currently failing full-regression checks so the repository reality matches the documented closure story, then continue `SPEC-13/14/15/16` in `M3` order, and only after that resume `SPEC-19` hardening.

**Tech Stack:** Markdown documentation, Python, pytest, static visualization generation

---

### Task 1: Reconfirm and preserve the audited entry state

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\README.md`
- Test: `D:\workspace\llmSched\tests\smoke`

**Step 1: Re-run the audit commands**

Run:

```powershell
python -m pytest -q
python -m pytest tests/smoke -m local_smoke -q
python -m pytest tests/smoke -m milestone_matrix -q
```

Expected:
- full pytest still reports the known failing set until repair work starts
- both smoke commands stay green

**Step 2: Keep the roadmap checkpoint current**

If counts or failing files change during later work, update only the `2026-03-14 Progress Review Checkpoint` block in `docs/development/evaluation-compiler-roadmap.md`.

### Task 2: Restore the Phase B legality regression surface

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\frontend\legality.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\frontend_analysis.py`
- Modify if needed: `D:\workspace\llmSched\src\llm_sched\contracts\frontend_analysis_report.py`
- Test: `D:\workspace\llmSched\tests\smoke\test_phase_b_closure_matrix.py`
- Test: `D:\workspace\llmSched\tests\unit\pipeline\test_frontend_analysis_workflow.py`

**Step 1: Lock the expected report shape**

Run:

```powershell
python -m pytest tests/smoke/test_phase_b_closure_matrix.py -q
```

Expected: FAIL on missing `kv_cache_dtype_mismatch` in `frontend_legality.issue_counts`.

**Step 2: Restore or intentionally replace the missing legality signal**

Make the smallest change that re-establishes a stable, explicit legality count for the closure matrix. If the signal was intentionally renamed, update the producing code and the consuming tests in one slice, and record the contract change in the roadmap checkpoint.

**Step 3: Verify the repaired slice**

Run:

```powershell
python -m pytest tests/smoke/test_phase_b_closure_matrix.py tests/unit/pipeline/test_frontend_analysis_workflow.py -q
```

Expected: PASS.

### Task 3: Restore the Phase C memory-planner `kv_formulas` surface

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\memory_planner.py`
- Modify if needed: `D:\workspace\llmSched\src\llm_sched\contracts\memory_plan.py`
- Modify if needed: `D:\workspace\llmSched\src\llm_sched\pipeline\memory_planning.py`
- Test: `D:\workspace\llmSched\tests\smoke\test_phase_c_memory_planner_matrix.py`
- Test: `D:\workspace\llmSched\tests\unit\pipeline\test_memory_planning_workflow.py`
- Test: `D:\workspace\llmSched\tests\unit\contracts\test_memory_plan_contract.py`

**Step 1: Reproduce the current failure**

Run:

```powershell
python -m pytest tests/smoke/test_phase_c_memory_planner_matrix.py tests/unit/pipeline/test_memory_planning_workflow.py -q
```

Expected: FAIL because `kv_formulas` is empty.

**Step 2: Restore a stable `kv_formulas` contract**

Repair the planner so decode and matrix scenarios emit the expected `kv_formulas` payload again, or narrow the contract deliberately and update all consumers in the same slice if the change is intentional.

**Step 3: Verify the repaired slice**

Run:

```powershell
python -m pytest tests/smoke/test_phase_c_memory_planner_matrix.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/contracts/test_memory_plan_contract.py -q
```

Expected: PASS.

### Task 4: Restore visible untiled helper compute blocks in scheduler outputs

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\dual_core_scheduler.py`
- Modify if needed: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`
- Test: `D:\workspace\llmSched\tests\smoke\test_phase_c_single_core_schedule_matrix.py`
- Test: `D:\workspace\llmSched\tests\smoke\test_phase_c_dual_core_schedule_matrix.py`
- Test: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Test: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Reproduce the current schedule regressions**

Run:

```powershell
python -m pytest tests/smoke/test_phase_c_single_core_schedule_matrix.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q
```

Expected: FAIL because prefill schedules do not expose untiled `RMSNORM` / `ELEM_ADD` compute blocks.

**Step 2: Repair scheduler visibility with minimal scope**

Restore the expected helper-block surface without reopening unrelated scheduler fidelity work. Preserve the current public `ScheduleIR` contract unless a deliberate contract change is documented.

**Step 3: Verify the repaired slice**

Run:

```powershell
python -m pytest tests/smoke/test_phase_c_single_core_schedule_matrix.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected: PASS.

### Task 5: Reclose the repository regression gate

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Run the full verification ladder**

Run:

```powershell
python -m pytest tests/smoke -m local_smoke -q
python -m pytest tests/smoke -m milestone_matrix -q
python -m pytest -q
```

Expected:
- smoke remains green
- full pytest returns to zero failures

**Step 2: Update the roadmap checkpoint**

Refresh the recorded counts and remove no-longer-applicable blockers from the `2026-03-14 Progress Review Checkpoint`.

### Task 6: Continue `P0: close M3` in roadmap order

**Files:**
- Read: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Read: `D:\workspace\llmSched\docs\development\phase-d-performance-foundation-handoff.md`
- Read: `D:\workspace\llmSched\docs\development\phase-d-prefill-foundation-handoff.md`
- Read: `D:\workspace\llmSched\docs\development\phase-d-decode-foundation-handoff.md`
- Read/Modify: `D:\workspace\llmSched\docs\plans\2026-03-14-phase-d-m3-closure-followup.md`

**Step 1: Pick the next roadmap-owned slice**

After full-regression closure, execute only in this order:
- `SPEC-13`: deeper cycle model, clearer bandwidth / VMEM breakdown
- `SPEC-14/15`: layer-level breakdown, stronger single-core / dual-core compare view
- `SPEC-16`: richer diff mode, deeper multi-metric compare

**Step 2: Create a dedicated slice plan for each follow-on change**

Each new code slice should get its own dated plan doc under `docs/plans/` and should cite this file plus the roadmap as its entry context.

### Task 7: Keep `SPEC-19` hardening downstream of `M3`

**Files:**
- Read: `D:\workspace\llmSched\docs\development\phase-e-visualization-workbench-handoff.md`

**Step 1: Guard the priority order**

Do not resume `SPEC-19` compare/workspace/screenshot hardening until:
- the full-regression gate is green again
- the next active slice is not blocked by `M3`

**Step 2: Limit Phase E work to roadmap `P1`**

When `SPEC-19` work resumes, keep it to:
- richer compare drill-down
- deeper workspace drill-down
- richer screenshot/export workflow

Do not open new service or lower-level contract work from that branch of the plan.
