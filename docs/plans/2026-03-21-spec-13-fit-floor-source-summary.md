# SPEC-13 Fit Floor Source Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-13` with one narrow estimator-trust slice that explains which fitted-cycle floor actually dominates: raw estimated work, schedule floor, or external-read bandwidth floor.

**Architecture:** Reuse the existing fitted-cycle calculation in `descriptor_estimator.py`, but stop treating `fitted_work_cycles` as an opaque post-processed number. Thread minimal floor-source metrics through analysis records, then aggregate them into a compact top-level `fit_floor_source_summary` inside `PerfSummaryReport`. Keep this slice summary-grade and estimator-local so later compare consumers can reuse it instead of rebuilding their own attribution.

**Tech Stack:** Pydantic contracts, `llm_sched.analysis.descriptor_estimator`, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Add the fit-floor source contract surface

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Test: `tests/unit/contracts/test_perf_report.py`

**Step 1: Write the failing contract test**

Extend the existing `PerfSummaryReport` contract fixture so it requires a new top-level `fit_floor_source_summary` with fields:

```python
{
    "schedule_floor_gap_cycles": 96.0,
    "external_bandwidth_gap_cycles": 60.0,
    "estimated_dominant_subject_count": 0,
    "schedule_floor_dominant_subject_count": 1,
    "external_bandwidth_dominant_subject_count": 1,
    "dominant_floor_source": "schedule_floor",
    "dominant_floor_phase": "projection",
    "dominant_floor_macro": "WDQ_GEMM",
}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: FAIL because `PerfSummaryReport` does not yet accept `fit_floor_source_summary`.

**Step 3: Write minimal contract implementation**

Add a `PerfFitFloorSourceSummary` model and a `fit_floor_source_summary` field on `PerfSummaryReport`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: PASS.

### Task 2: Preserve floor-source metrics in descriptor estimation

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Test: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing estimator test**

Add focused assertions around descriptor-estimation output so at least one compute descriptor now preserves:

```python
assert record.metrics["schedule_floor_cycles"] >= 0.0
assert record.metrics["external_bandwidth_floor_cycles"] >= 0.0
assert record.metrics["fit_floor_gap_cycles"] == pytest.approx(
    record.metrics["fitted_work_cycles"] - record.metrics["estimated_cycles"]
)
assert record.metrics["fit_floor_source"] in {"estimated", "schedule_floor", "external_bandwidth"}
```

Use an existing fixture where schedule duration or external reads already lift fitted cycles.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q`

Expected: FAIL because the metrics are not yet emitted.

**Step 3: Write minimal implementation**

In `_fitted_work_cycles_for_descriptor(...)` or a helper right next to it:

- compute `estimated_cycles`
- compute `schedule_floor_cycles`
- compute `external_bandwidth_floor_cycles`
- compute `fitted_work_cycles`
- emit:
  - `schedule_floor_cycles`
  - `external_bandwidth_floor_cycles`
  - `fit_floor_gap_cycles`
  - `fit_floor_source`

Use the dominant source that actually equals the chosen fitted floor:
- `estimated`
- `schedule_floor`
- `external_bandwidth`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q`

Expected: PASS.

### Task 3: Aggregate floor-source trust into the canonical perf artifact

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Test: `tests/unit/analysis/test_perf_summary_builder.py`
- Test: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing builder/workflow tests**

Extend the current perf summary assertions with:

```python
assert report.fit_floor_source_summary.schedule_floor_gap_cycles >= 0.0
assert report.fit_floor_source_summary.external_bandwidth_gap_cycles >= 0.0
assert report.fit_floor_source_summary.dominant_floor_source in {
    "estimated", "schedule_floor", "external_bandwidth", ""
}
assert report.fit_floor_source_summary.dominant_floor_phase in {
    "projection", "kv_io", "attention", "sync", "other", ""
}
```

Also assert serialized workflow JSON includes `"fit_floor_source_summary"`.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: FAIL because the summary is not yet populated.

**Step 3: Write minimal implementation**

Aggregate from record metrics:

- `schedule_floor_gap_cycles = sum(max(0, schedule_floor_cycles - estimated_cycles))`
- `external_bandwidth_gap_cycles = sum(max(0, fitted_work_cycles - max(estimated_cycles, schedule_floor_cycles)))`
- count how many records are dominated by each `fit_floor_source`
- choose `dominant_floor_source` by largest total uplift, not count
- choose `dominant_floor_phase` and `dominant_floor_macro` from records whose `fit_floor_source` matches the dominant source and whose uplift is largest

Keep this top-level only; do not add per-phase tables yet.

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
- Modify: `docs/plans/2026-03-21-spec-13-critical-path-fit-gap-decomposition.md`

**Step 1: Update docs**

Record that:

- `SPEC-13` now explains not only fitted-versus-estimated and critical-path divergence, but also which floor is actually inflating fitted cycles
- this closes one deeper estimator-trust gap without reopening broader compare consumers
- the next remaining `SPEC-13` blocker is closer to stronger compare-grade estimator aggregation or genuinely richer fitted-cycle math

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - descriptor analysis now preserves:
    - `schedule_floor_cycles`
    - `external_bandwidth_floor_cycles`
    - `fit_floor_gap_cycles`
    - `fit-floor:*` dominant-source tags
  - `PerfSummaryReport` now exposes `fit_floor_source_summary`
  - top-level summary now carries:
    - `schedule_floor_gap_cycles`
    - `external_bandwidth_gap_cycles`
    - source-dominant subject counts
    - `dominant_floor_source`
    - `dominant_floor_phase`
    - `dominant_floor_macro`
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_perf_report.py -q` -> `1 passed`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q` -> `3 passed`
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q` -> `9 passed`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `19 passed`
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- updated interpretation:
  - this slice closes another estimator-trust gap by making the source of fitted-cycle inflation explicit in the canonical perf artifact
  - the next remaining `SPEC-13` blocker is now more likely compare-grade estimator aggregation or genuinely deeper fitted-cycle math, not missing floor-source interpretation
