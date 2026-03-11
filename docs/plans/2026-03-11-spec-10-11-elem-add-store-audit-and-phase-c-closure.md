# ELEM_ADD Store Audit and Phase C Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove or disprove an `ELEM_ADD.store` schedule-fidelity gap, implement the minimal fix if the gap is real, and then freeze the `SPEC-09` and `SPEC-12` closure decisions for `M2`.

**Architecture:** Reuse the existing schedule-fidelity audit pattern: add focused reservation-level red tests first, then make the smallest `schedule_duration.py` change that gives `ELEM_ADD.store` the same internal phased-reservation treatment already used by other vector-store surfaces. Keep the public `ScheduleIR` stage model unchanged and express the remaining `SPEC-09` and `SPEC-12` work as explicit closure decisions instead of open-ended backlog.

**Tech Stack:** Python, pytest, schedule duration heuristics, single-core and dual-core scheduler unit tests, Markdown docs

---

### Task 1: Add failing `ELEM_ADD.store` reservation tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Write the failing single-core reservation test**

Add a focused test that:
- builds `ELEM_ADD` store reservations
- reserves them at `issue_slot=0`
- asks when a later independent `DMA` request can start
- asserts the later `DMA` can issue at slot `0`

**Step 2: Write the failing dual-core reservation test**

Mirror the same assertion on the dual-core target profile so both `SPEC-10` and `SPEC-11` consume the same evidence.

**Step 3: Run the red slice**

```powershell
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k "elem_add_store_issue"
```

Expected: fail because `ELEM_ADD.store` still reserves only `DMA`.

### Task 2: Implement the minimal `ELEM_ADD.store` specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add an `ELEM_ADD` store-prefix heuristic**

Implement one helper that estimates a small VPU prefix before the later DMA writeback window for `ELEM_ADD.store`.

**Step 2: Wire it into duration and reservation breakdowns**

Update:
- `_dma_stage_slot_breakdown(...)`
- `estimate_stage_resource_reservations(...)`

Keep:
- public store stage resource set as `["DMA"]`
- public `ScheduleIR` block model unchanged

**Step 3: Re-run the red slice**

```powershell
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k "elem_add_store_issue"
```

Expected: pass

### Task 3: Run the focused scheduler regression

**Files:**
- Verify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Verify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Run the store-prefix slice**

```powershell
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k "store_issue_with_vpu_prefix or elem_add_store_issue"
```

**Step 2: Run a broader planner regression**

```powershell
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Record whether the new specialization stays local and whether any existing overlap assumptions break.

### Task 4: Freeze the Phase C closure decisions in docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-11-phase-c-m2-closure-audit.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Update the scheduler-closure evidence**

Record:
- whether `ELEM_ADD.store` needed specialization
- whether the remaining generic store surface list narrowed again

**Step 2: Make the `SPEC-09` closure decision explicit**

Document that `M2` accepts the current GEMM/attention tiling surface plus untiled-helper scheduling unless the audit exposed a concrete counterexample.

**Step 3: Freeze the `SPEC-12` stop-line**

Document that:
- packed summary consumer proof is enough for `M2`
- workbench summary visibility is enough for `M2`
- no per-record drilldown is required without a concrete consumer

## Outcome

- Root cause confirmed:
  - `ELEM_ADD.store` still behaved like one monolithic shared-`DMA` reservation surface in both single-core and dual-core scheduling
  - focused red tests failed first with `follower_issue == 4`, so the gap was real rather than speculative
- Implemented:
  - added focused single-core and dual-core `ELEM_ADD.store` reservation tests
  - added a minimal internal `VPU` prefix heuristic for `ELEM_ADD.store` in `schedule_duration.py`
  - kept the public `ScheduleIR` stage lowering unchanged as `store = ["DMA"]`
- Verification evidence:
  - `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k "elem_add_store_issue"` -> `2 passed`
  - `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k "store_issue_with_vpu_prefix or elem_add_store_issue"` -> `16 passed`
  - `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q` -> `60 passed`
- Closure decisions frozen:
  - `SPEC-09` now accepts the current GEMM-like plus attention tiling surface together with untiled-helper scheduling for `M2`
  - `SPEC-12` now stops at packed summary consumer proof plus workbench summary visibility for `M2`
