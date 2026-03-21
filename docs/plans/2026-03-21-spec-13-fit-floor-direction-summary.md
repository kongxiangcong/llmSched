# SPEC-13 Fit-Floor Direction Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `SPEC-13` shared-DMA fit-floor pressure direction-aware by preserving external read/write floor cycles and aggregating them into a canonical top-level summary.

**Architecture:** Keep the slice estimator-local and summary-grade. Extend descriptor-analysis metrics with `external_read_floor_cycles` and `external_write_floor_cycles`, then aggregate one new `PerfFitFloorDirectionSummary` on `PerfSummaryReport` so downstream consumers can tell whether fitted-cycle inflation is dominated by inbound or outbound off-chip pressure without reopening raw records.

**Tech Stack:** Pydantic contracts, `llm_sched.analysis.descriptor_estimator`, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Add direction-aware floor metrics to descriptor analysis

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing test**

Extend the existing tiled-compute assertions so they require:

```python
assert compute_record.metrics["external_read_floor_cycles"] == 96.0
assert compute_record.metrics["external_write_floor_cycles"] == 32.0
assert compute_record.metrics["external_bandwidth_floor_cycles"] == 128.0
```

Also keep one write-only case that expects:

```python
assert compute_record.metrics["external_read_floor_cycles"] == 0.0
assert compute_record.metrics["external_write_floor_cycles"] == 32.0
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: FAIL because the estimator does not yet expose direction-aware floor metrics.

**Step 3: Write minimal implementation**

Update `_fitted_work_cycle_metrics_for_descriptor(...)`, `_build_fit_floor_metrics(...)`, and `_zero_metrics()` so descriptor-analysis records preserve:

```python
"external_read_floor_cycles": ...
"external_write_floor_cycles": ...
```

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: PASS.

### Task 2: Add the top-level fit-floor direction summary contract

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `tests/unit/contracts/test_perf_report.py`

**Step 1: Write the failing contract test**

Extend the `PerfSummaryReport` fixture so it requires:

```python
"fit_floor_direction_summary": {
    "external_read_gap_cycles": 96.0,
    "external_write_gap_cycles": 32.0,
    "dominant_external_direction": "read",
    "dominant_external_phase": "projection",
    "dominant_external_macro": "WDQ_GEMM",
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/contracts/test_perf_report.py -q
```

Expected: FAIL because `PerfSummaryReport` does not yet accept the new summary.

**Step 3: Write minimal contract implementation**

Add:

```python
class PerfFitFloorDirectionSummary(BaseModel):
    ...
```

and wire it onto `PerfSummaryReport` as `fit_floor_direction_summary`.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/contracts/test_perf_report.py -q
```

Expected: PASS.

### Task 3: Build fit-floor direction summary from existing estimator records

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Add focused assertions that a bidirectional shared-DMA case produces:

```python
assert report.fit_floor_direction_summary.external_read_gap_cycles == pytest.approx(96.0)
assert report.fit_floor_direction_summary.external_write_gap_cycles == pytest.approx(32.0)
assert report.fit_floor_direction_summary.dominant_external_direction == "read"
assert report.fit_floor_direction_summary.dominant_external_phase == "projection"
assert report.fit_floor_direction_summary.dominant_external_macro == "WDQ_GEMM"
```

and that workflow JSON serialization preserves `fit_floor_direction_summary`.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: FAIL because no fit-floor direction summary is produced yet.

**Step 3: Write minimal implementation**

Aggregate read/write gap cycles from descriptor-analysis records that already carry `fit-floor:external_bandwidth`, and choose dominant direction/phase/macro by largest aggregated external gap contribution.

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
- Modify: `docs/plans/2026-03-21-spec-13-shared-dma-bidirectional-stall.md`

**Step 1: Update docs**

Record that:

- `SPEC-13` now preserves shared-DMA read/write floor decomposition beside the existing external-bandwidth topline
- this is a direction-aware trust slice, not a new deeper-cycle math rewrite
- the next remaining blocker, if any, is finer-grained overlap budgeting rather than missing direction-level observability

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - descriptor-analysis records now preserve `external_read_floor_cycles` and `external_write_floor_cycles`
  - `PerfSummaryReport` now exposes `fit_floor_direction_summary`
  - top-level perf artifacts can now explain whether current external-bandwidth uplift is dominated by inbound or outbound off-chip pressure
- fresh verification:
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q` -> `13 passed`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `27 passed`
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- interpretation:
  - this slice closes the current direction-level observability gap without reopening deeper-cycle math
  - the next remaining estimator blocker is finer-grained overlap budgeting beyond the current read/write floor decomposition
- downstream follow-on landed after this slice:
  - `../plans/2026-03-21-spec-13-external-write-drain-overlap.md`
  - overlap budgeting now distinguishes read-overlap from write-drain behavior, so the next remaining blocker has shifted from direction-level observability to finer schedule slack / overlap allocation fidelity
