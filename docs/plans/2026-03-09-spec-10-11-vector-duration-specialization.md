# SPEC-10/11 Vector Duration Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve schedule makespan fidelity by adding macro-specific duration heuristics for vector-style stages without changing the public `ScheduleIR` contract.

**Architecture:** Keep stage lowering and block structure stable, but refine `estimate_stage_duration_slots(...)` so vector-family macros no longer all share the same duration formula. The first scope covers stable macro surfaces where one generic VPU formula is clearly too coarse: `RMSNORM`, `GEGLU`, `ROPE`, `ATTENTION_MASK_PREP`, and `LAYOUT_FALLBACK`.

**Tech Stack:** Python dataclasses, pytest, existing scheduler/memory/descriptor/perf contracts.

---

### Task 1: Write failing duration specialization tests

**Files:**
- Create: `tests/unit/planning/test_schedule_duration.py`

**Step 1: Write the failing tests**

- Add direct unit tests for `estimate_stage_duration_slots(...)` that assert:
  - `GEGLU` compute is costlier than `RMSNORM` compute for the same resolved shape
  - `ROPE` compute is costlier than `SHAPE_HELPER` compute for the same resolved shape
  - `ATTENTION_MASK_PREP` compute is costlier than `SHAPE_HELPER` compute for the same resolved shape
  - `GEGLU` prepare is costlier than a generic helper prepare for the same resolved shape

**Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/planning/test_schedule_duration.py -q
```

Expected:
- the new tests fail because all current vector-family stages still share the same generic duration formula

### Task 2: Implement the minimal duration specialization

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Add macro-stage-specific factors**

- Keep the current generic vector formula as the base.
- Add a small explicit factor table keyed by `(macro_op, stage)` for the first specialized vector-family set.

**Step 2: Re-run the targeted tests**

Run:

```bash
python -m pytest tests/unit/planning/test_schedule_duration.py -q
```

Expected:
- the new duration specialization tests pass

### Task 3: Verify scheduler/perf integration and document the checkpoint

**Files:**
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Modify: `docs/development/phase-c-dual-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Run focused integration verification**

Run:

```bash
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/analysis/test_descriptor_estimator.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected:
- scheduler and perf-facing tests remain green with the stronger duration policy

**Step 2: Update docs**

- Record the vector-duration specialization checkpoint and narrow the next `SPEC-10/11` gap.

**Step 3: Run full verification**

Run:

```bash
python -m pytest -q
git diff --check
```

Expected:
- full test suite passes
- no diff errors, only CRLF warnings are acceptable

**Step 4: Commit**

```bash
git add docs/plans/2026-03-09-spec-10-11-vector-duration-specialization.md docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md src/llm_sched/planning/schedule_duration.py tests/unit/planning/test_schedule_duration.py
git commit -m "feat: specialize vector stage durations"
```
