# SPEC-13 External Write Drain Overlap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `SPEC-13` overlap budgeting by treating external writes as post-compute drain cycles instead of letting `estimated_cycles` absorb them by default.

**Architecture:** Keep the change estimator-local. Preserve the current residual external-read overlap model, but split the overlap budget by direction: inbound external reads may consume the compute overlap budget, while outbound external writes are modeled as non-overlapped drain appended after compute. Reuse the current direction-aware floor metrics and summaries rather than adding new contracts.

**Tech Stack:** `llm_sched.analysis.descriptor_estimator`, existing perf-report contracts, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Lock the new external-write-drain behavior with failing estimator tests

**Files:**
- Modify: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing tests**

Update the existing write-aware tests so they require:

```python
def test_estimate_descriptor_analysis_adds_residual_external_write_stall() -> None:
    ...
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["external_write_floor_cycles"] == 32.0
    assert compute_record.metrics["fitted_work_cycles"] == 80.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 32.0

def test_estimate_descriptor_analysis_adds_bidirectional_shared_dma_stall_above_schedule_floor() -> None:
    ...
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_read_floor_cycles"] == 96.0
    assert compute_record.metrics["external_write_floor_cycles"] == 32.0
    assert compute_record.metrics["fitted_work_cycles"] == 144.0
```

The write-only case is the real math change: external writes now add a full 32-cycle drain on top of the 48-cycle compute estimate.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: FAIL because the current estimator still lets the overlap budget absorb write-only pressure.

### Task 2: Implement external-write drain overlap budgeting

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`

**Step 1: Write minimal implementation**

Inside `_fitted_work_cycle_metrics_for_descriptor(...)`, keep the current read residual logic but split by direction:

```python
residual_external_read_stall_cycles = max(0.0, external_read_cycles - estimated_cycles)
residual_external_write_stall_cycles = external_write_cycles
fitted_work_cycles = max(
    base_fitted_cycles,
    schedule_floor_cycles
    + residual_external_read_stall_cycles
    + residual_external_write_stall_cycles,
)
```

Keep the scope narrow:

- no new metrics beyond the already-landed direction-aware floor fields
- no change to non-compute descriptors
- no new top-level summary contract in this slice

**Step 2: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: PASS.

### Task 3: Prove the stronger write-drain fit survives perf summary/workflow serialization

**Files:**
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Update the write-aware summary/workflow assertions so a write-only external floor case now preserves:

```python
assert report.totals["fitted_work_cycles"] == pytest.approx(80.0)
assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(32.0)
assert report.fit_floor_direction_summary.external_write_gap_cycles == pytest.approx(32.0)
```

and serialized workflow JSON carries the same stronger topline.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: FAIL until the updated overlap budgeting reaches summary/workflow artifacts.

**Step 3: Write minimal implementation**

Only update fixture metrics and expected toplines where the estimator output actually changed. Avoid adding any new report field in this slice.

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
- Modify: `docs/plans/2026-03-21-spec-13-fit-floor-direction-summary.md`

**Step 1: Update docs**

Record that:

- `SPEC-13` overlap budgeting now treats external writes as write-drain cycles instead of assuming they overlap compute
- this is the first direction-aware overlap-budget math slice, not just another observability field
- the next remaining blocker, if any, is finer-grained schedule slack / overlap allocation beyond the current read-overlap plus write-drain rule

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - overlap budgeting now lets `estimated_cycles` absorb external reads but not external writes
  - write-only external pressure now raises `fitted_work_cycles` and `fit_floor_gap_cycles` through a dedicated write-drain rule
  - existing fit-gap and fit-floor summaries now observe stronger write-aware fitted-cycle toplines without any new report field
- fresh verification:
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q` -> `15 passed`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `29 passed`
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- interpretation:
  - this is the first explicit direction-aware overlap-budget math slice inside current `SPEC-13`
  - the next remaining estimator blocker is finer-grained schedule slack / overlap allocation beyond the current read-overlap plus write-drain rule
