# SPEC-13 Residual External Stall Fitting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve `SPEC-13` fitted-cycle fidelity by replacing the current `max(schedule_floor, external_read_floor)` shortcut with a residual external-stall model that preserves schedule floor and only adds the non-overlappable portion of external-read pressure.

**Architecture:** Reuse the current descriptor-estimator pipeline and keep the change compute-local. Add one deeper-cycle rule inside `_fitted_work_cycle_metrics_for_descriptor(...)`: treat `estimated_cycles` as the overlap budget for external reads, compute a residual bandwidth stall above that overlap budget, and then add that stall on top of the schedule-aware fitted base instead of letting the external floor overwrite it.

**Tech Stack:** Pydantic-free estimator math change in `llm_sched.analysis.descriptor_estimator`, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Lock the new residual-stall behavior with failing estimator tests

**Files:**
- Modify: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing estimator tests**

Add two focused tests:

```python
def test_estimate_descriptor_analysis_adds_residual_external_stall_above_schedule_floor() -> None:
    ...
    descriptor_ir.descriptors[0].ctrl_fields["duration_slots"] = 64
    analysis = estimate_descriptor_analysis(..., schedule_ir=_schedule_ir_fixture(duration_slots=64), tiling_plan=_tiling_plan_fixture(ddr_backed_staged_bytes=122880))
    compute_record = ...
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 96.0
    assert compute_record.metrics["fitted_work_cycles"] == 112.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 64.0
    assert "fit-floor:external_bandwidth" in compute_record.tags

def test_estimate_descriptor_analysis_keeps_current_behavior_when_schedule_floor_does_not_exceed_estimated() -> None:
    ...
    assert compute_record.metrics["fitted_work_cycles"] == 96.0
```

The first test is the real new behavior: `64 + max(0, 96 - 48) = 112`.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: FAIL because the current estimator still returns `96.0` in the schedule-floor-plus-bandwidth case.

### Task 2: Implement residual external-stall fitting

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`

**Step 1: Write minimal implementation**

Inside `_fitted_work_cycle_metrics_for_descriptor(...)`:

- keep `estimated_cycles`
- keep `schedule_floor_cycles`
- keep `external_bandwidth_floor_cycles`
- compute `base_fitted_cycles = max(estimated_cycles, schedule_floor_cycles)`
- compute `residual_external_stall_cycles = max(0.0, external_bandwidth_floor_cycles - estimated_cycles)`
- when a compute descriptor has external reads, set:

```python
fitted_work_cycles = max(base_fitted_cycles, schedule_floor_cycles + residual_external_stall_cycles)
```

This keeps current behavior when `schedule_floor_cycles <= estimated_cycles`, but raises fitted cycles when schedule floor is already above estimated and there is still unhidden external-read pressure.

**Step 2: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: PASS.

### Task 3: Prove the deeper-cycle change survives perf summary/workflow serialization

**Files:**
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Add assertions that a residual-stall-heavy compute case preserves the stronger fitted topline through:

- `fit_gap_summary.total_fit_gap_cycles`
- `fit_floor_source_summary.external_bandwidth_gap_cycles`
- workflow JSON serialization of `fitted_work_cycles`

Prefer reusing or minimally extending existing fixtures rather than inventing a large new scenario.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: FAIL until the deeper-cycle math shows up in summaries.

**Step 3: Write minimal implementation**

Only update summary expectations if the underlying estimator outputs have changed. Avoid adding new summary fields in this slice.

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: PASS.

### Task 4: Reconfirm focused SPEC-13 and downstream keep-green

**Files:**
- Test: `tests/unit/analysis/test_descriptor_estimator.py`
- Test: `tests/unit/contracts/test_perf_report.py`
- Test: `tests/unit/analysis/test_perf_summary_builder.py`
- Test: `tests/unit/pipeline/test_performance_estimation_workflow.py`
- Test: `tests/smoke/test_phase_d_perf_foundation_matrix.py`
- Test: `tests/smoke/test_cli_run_performance_estimation.py`
- Test: `tests/unit/analysis/test_prefill_report_builder.py`
- Test: `tests/unit/analysis/test_decode_report_builder.py`
- Test: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Test: `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Test: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- Test: `tests/smoke/test_phase_d_decode_foundation_matrix.py`

**Step 1: Run focused SPEC-13 regression**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q
```

Expected: PASS.

**Step 2: Run downstream Phase D consumer regression**

Run:

```powershell
python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q
```

Expected: PASS.

### Task 5: Publish the closure update

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-21-spec-13-compare-grade-estimator-summary.md`

**Step 1: Update docs**

Record that:

- compute fitted-cycle math now preserves schedule floor and adds only residual external-read stall
- this is the first post-summary estimator slice that materially changes fitted-cycle values again
- the next remaining `SPEC-13` blocker, if any, is richer overlap/stall math beyond this residual model

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - `_fitted_work_cycle_metrics_for_descriptor(...)` now preserves `schedule_floor` and adds only residual external-read stall above `estimated_cycles`
  - `fit-floor:external_bandwidth` attribution now also covers the residual-stall case where external bandwidth raises fitted work cycles above both `estimated_cycles` and `schedule_floor`
  - regression coverage now proves the stronger fitted topline survives:
    - descriptor-estimator unit tests
    - perf summary aggregation
    - workflow JSON serialization
- fresh verification:
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q` -> `11 passed`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `22 passed`
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- interpretation:
  - this is the first post-summary `SPEC-13` slice that materially changes fitted-cycle values again
  - the next remaining estimator blocker is richer overlap/stall fidelity beyond the current residual model
- downstream follow-on landed after this slice:
  - `../plans/2026-03-21-spec-13-shared-dma-bidirectional-stall.md`
  - estimator math now covers shared-DMA read/write pressure as well, so the next remaining blocker has moved toward finer-grained overlap budgeting rather than missing bidirectional external bandwidth awareness
