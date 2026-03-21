# SPEC-13 Schedule Slack Write Absorption Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve `SPEC-13` overlap budgeting by letting schedule slack absorb part of external write drain before it inflates fitted work cycles.

**Architecture:** Keep the change estimator-local and narrowly scoped to compute descriptors. Reuse the current direction-aware overlap model, but introduce one extra budget term: `schedule_slack_cycles = max(0.0, schedule_floor_cycles - estimated_cycles)`. Apply that slack only to external write drain, so current read-overlap semantics stay unchanged while write-only or mixed read/write cases become less pessimistic when the schedule already contains idle headroom.

**Tech Stack:** `llm_sched.analysis.descriptor_estimator`, existing perf-report contracts, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Lock the schedule-slack write-absorption behavior with failing estimator tests

**Files:**
- Modify: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing tests**

Add two focused scenarios:

```python
def test_estimate_descriptor_analysis_uses_schedule_slack_to_absorb_external_write_drain() -> None:
    ...
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_write_floor_cycles"] == 32.0
    assert compute_record.metrics["fitted_work_cycles"] == 80.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 32.0

def test_estimate_descriptor_analysis_keeps_bidirectional_stall_when_write_drain_exceeds_schedule_slack() -> None:
    ...
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_read_floor_cycles"] == 96.0
    assert compute_record.metrics["external_write_floor_cycles"] == 32.0
    assert compute_record.metrics["fitted_work_cycles"] == 128.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 80.0
```

Math for the second case:

- schedule slack = `64 - 48 = 16`
- residual external read stall = `96 - 48 = 48`
- absorbed write drain = `max(0, 32 - 16) = 16`
- fitted cycles = `64 + 48 + 16 = 128`

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: FAIL because the current estimator still charges the full write drain even when schedule slack exists.

### Task 2: Implement schedule-slack write absorption

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`

**Step 1: Write minimal implementation**

Inside `_fitted_work_cycle_metrics_for_descriptor(...)`, after computing `schedule_floor`, `estimated_cycles`, `external_read_cycles`, and `external_write_cycles`, add:

```python
schedule_slack_cycles = max(0.0, schedule_floor_cycles - estimated_cycles)
residual_external_read_stall_cycles = max(0.0, external_read_cycles - estimated_cycles)
residual_external_write_stall_cycles = max(0.0, external_write_cycles - schedule_slack_cycles)
```

and keep:

```python
fitted_work_cycles = max(
    base_fitted_cycles,
    schedule_floor_cycles
    + residual_external_read_stall_cycles
    + residual_external_write_stall_cycles,
)
```

Keep the scope narrow:

- no new metrics or report fields
- no change to non-compute descriptors
- no change to current read-overlap logic

**Step 2: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: PASS.

### Task 3: Prove the updated overlap budgeting survives perf summary/workflow serialization

**Files:**
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Update the write-aware summary/workflow fixtures so schedule-slack-aware cases now preserve:

```python
assert report.totals["fitted_work_cycles"] == pytest.approx(80.0)
assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(32.0)
```

for the slack-absorbed write-only case, and:

```python
assert report.totals["fitted_work_cycles"] == pytest.approx(128.0)
assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(80.0)
```

for the mixed read/write case.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: FAIL until the refined overlap budgeting reaches summary/workflow artifacts.

**Step 3: Write minimal implementation**

Only update fixture metrics and expected toplines where the estimator output actually changed. Do not add any new contract in this slice.

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
- Modify: `docs/plans/2026-03-21-spec-13-external-write-drain-overlap.md`

**Step 1: Update docs**

Record that:

- schedule slack now absorbs part of external write drain
- this is the first schedule-slack-aware overlap allocation slice in current `SPEC-13`
- the next remaining blocker, if any, is richer slack allocation policy beyond the current write-absorption rule

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - overlap budgeting now derives `schedule_slack_cycles = max(0.0, schedule_floor - estimated_cycles)`
  - that slack is applied to absorb part of external write drain before it inflates `fitted_work_cycles`
  - current read-overlap semantics remain unchanged
- fresh verification:
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q` -> `17 passed`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `32 passed`
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- interpretation:
  - this is the first schedule-slack-aware overlap allocation slice in current `SPEC-13`
  - the next remaining estimator blocker is richer slack-allocation policy beyond the current single-rule write absorption
