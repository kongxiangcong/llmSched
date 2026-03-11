# SPEC-10/11 SDPA Store Prefix Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `SDPA` and `SDPA_DECODE` store-stage reservation modeling so output writeback no longer appears as one monolithic shared-`DMA` slab when frontend semantics already preserve output transpose/reshape work.

**Architecture:** Keep stage lowering and public `ScheduleIR` unchanged. Add a narrow `store`-side phased reservation for attention output writeback, with TDD proof at the reservation layer and scheduler-window layer. Reuse existing interval reservation machinery so downstream descriptor/perf consumers only see stronger overlap fidelity, not a new artifact contract.

**Tech Stack:** Python, pytest, schedule duration policy, interval reservation helpers, single-core and dual-core scheduler tests

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add a duration-layer failing test**

Add one focused test that proves `estimate_stage_resource_reservations(...)` keeps `SDPA.store` and `SDPA_DECODE.store` on pure `DMA` today, but should instead emit a short `VPU` prefix followed by the later `DMA` writeback window.

**Step 2: Add a single-core scheduler-window failing test**

Add one focused test that uses `find_earliest_issue_slot(...)` plus a real `SDPA.store` reservation request and proves a pure-`DMA` follower should be able to co-issue at the store block start once the `DMA` window is delayed behind a `VPU` prefix.

**Step 3: Add a dual-core scheduler-window failing test**

Mirror the same intent for dual-core by reusing the real `SDPA.store` reservation request against a shared-`DMA` timeline.

**Step 4: Run the red slice**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k sdpa_store
```

Expected: fail because `SDPA.store` and `SDPA_DECODE.store` still reserve the entire block as `DMA`.

### Task 2: Implement the minimal reservation specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add one shared helper for attention-output store prefix slots**

Use the existing output element count and VPU lanes to model a short output-layout prefix for `SDPA` and `SDPA_DECODE` store stages.

**Step 2: Wire the helper into store-stage slot breakdown and reservations**

Keep total duration shape stable, but split the reservation into:

```text
("VPU", 0, prefix_slots)
("DMA", prefix_slots, transport_slots)
```

for `SDPA.store` and `SDPA_DECODE.store`.

### Task 3: Re-run the main planning regression slice

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k sdpa_store
```

**Step 2: Re-run broader planning regression**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

**Step 3: Re-run workflow-focused local gate**

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-sdpa-store-prefix-specialization.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- broader planning result
- workflow-focused result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what `SDPA` / `SDPA_DECODE` store specialization now models
- what overlap-fidelity gap it closes for `SPEC-10/11`
- what should be audited next inside `M2`

## Outcome

- `SDPA` / `SDPA_DECODE` store-stage hardening landed as a reservation-only refinement: public stage lowering and `ScheduleIR` block shape stayed unchanged while output writeback now exposes a short `VPU` prefix before the later shared-`DMA` window.
- focused red/green slice:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k sdpa_store`
  - `3 failed` -> `3 passed, 55 deselected in 0.78s`
- explicit confirmation of all newly added cases:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py::test_estimate_stage_resource_reservations_specializes_sdpa_store_prefix tests/unit/planning/test_schedule_duration.py::test_estimate_stage_resource_reservations_specializes_sdpa_decode_store_prefix tests/unit/planning/test_single_core_scheduler.py::test_plan_single_core_schedule_allows_dma_at_sdpa_store_issue_with_vpu_prefix tests/unit/planning/test_dual_core_scheduler.py::test_plan_dual_core_schedule_allows_dma_at_sdpa_store_issue_with_vpu_prefix -q`
  - `4 passed in 0.79s`
- broader planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `58 passed in 1.01s`
- workflow-focused regression:
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `11 passed in 20.80s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `335 tests collected in 1.03s`
