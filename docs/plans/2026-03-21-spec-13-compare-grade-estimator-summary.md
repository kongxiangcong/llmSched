# SPEC-13 Compare-Grade Estimator Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `PhaseDCompareReport` with one compare-grade estimator summary so analysts can judge fitted-versus-estimated trust movement across prefill/decode compares without reopening raw perf artifacts.

**Architecture:** Reuse the compare rows already emitted by `SweepDeltaReport` and `PhaseDCompareReport`; do not expand every row with more estimator-local fields. Instead, aggregate two top-level `PhaseDEstimatorCompareSummary` sections, one for prefill and one for decode, built from existing `estimated_cycles`, `fitted_work_cycles`, `critical_path_cycles`, and per-phase fitted/estimated compare deltas.

**Tech Stack:** Pydantic contracts, `llm_sched.analysis.phase_d_compare_report_builder`, pytest contract/builder/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Add the compare-grade estimator summary contract

**Files:**
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Test: `tests/unit/contracts/test_phase_d_compare_report.py`

**Step 1: Write the failing contract test**

Extend the existing `PhaseDCompareReport` fixture so it requires:

```python
"prefill_estimator_summary": {
    "compare_count": 1,
    "candidate_tighter_fit_count": 1,
    "baseline_tighter_fit_count": 0,
    "neutral_fit_count": 0,
    "avg_fit_gap_delta": 0.0,
    "avg_critical_path_gap_delta": -256.0,
    "dominant_fit_gap_phase": "projection",
    "dominant_critical_path_delta_phase": "attention",
},
"decode_estimator_summary": {
    "compare_count": 1,
    "candidate_tighter_fit_count": 1,
    "baseline_tighter_fit_count": 0,
    "neutral_fit_count": 0,
    "avg_fit_gap_delta": 0.0,
    "avg_critical_path_gap_delta": -240.0,
    "dominant_fit_gap_phase": "kv_io",
    "dominant_critical_path_delta_phase": "projection",
},
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py -q`

Expected: FAIL because `PhaseDCompareReport` does not yet accept estimator summaries.

**Step 3: Write minimal contract implementation**

Add `PhaseDEstimatorCompareSummary` plus top-level `prefill_estimator_summary` / `decode_estimator_summary` fields on `PhaseDCompareReport`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py -q`

Expected: PASS.

### Task 2: Build estimator summaries from existing compare rows

**Files:**
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Test: `tests/unit/analysis/test_phase_d_compare_report_builder.py`

**Step 1: Write the failing builder test**

Add focused assertions that:

```python
assert report.prefill_estimator_summary.compare_count == 1
assert report.prefill_estimator_summary.candidate_tighter_fit_count == 1
assert report.prefill_estimator_summary.avg_fit_gap_delta == pytest.approx(0.0)
assert report.prefill_estimator_summary.avg_critical_path_gap_delta == pytest.approx(-256.0)
assert report.prefill_estimator_summary.dominant_fit_gap_phase == "projection"
assert report.prefill_estimator_summary.dominant_critical_path_delta_phase == "attention"

assert report.decode_estimator_summary.compare_count == 1
assert report.decode_estimator_summary.candidate_tighter_fit_count == 1
assert report.decode_estimator_summary.avg_fit_gap_delta == pytest.approx(0.0)
assert report.decode_estimator_summary.avg_critical_path_gap_delta == pytest.approx(-240.0)
assert report.decode_estimator_summary.dominant_fit_gap_phase == "kv_io"
assert report.decode_estimator_summary.dominant_critical_path_delta_phase == "projection"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_phase_d_compare_report_builder.py -q`

Expected: FAIL because builder does not yet populate the summaries.

**Step 3: Write minimal implementation**

Aggregate separately for prefill/decode rows:

- per row `fit_gap_delta = fitted_work_cycles.delta_value - estimated_cycles.delta_value`
- per row `critical_path_gap_delta = critical_path_cycles.delta_value - estimated_cycles.delta_value`
- `candidate_tighter_fit_count` when `fit_gap_delta < 0`
- `baseline_tighter_fit_count` when `fit_gap_delta > 0`
- `neutral_fit_count` otherwise
- `dominant_fit_gap_phase` from the largest average absolute `(phase_fitted_work_cycles.delta_value - phase_cycles.delta_value)`
- `dominant_critical_path_delta_phase` from the largest average absolute `phase_cycles.delta_value`

Keep the slice top-level only; do not add row-level estimator fields.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_phase_d_compare_report_builder.py -q`

Expected: PASS.

### Task 3: Prove workflow/CLI serialization carries estimator summaries

**Files:**
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/smoke/test_cli_run_phase_d_compare.py`

**Step 1: Write the failing workflow/smoke assertions**

Add assertions that serialized report payload contains:

```python
assert "prefill_estimator_summary" in report_payload
assert "decode_estimator_summary" in report_payload
assert report.prefill_estimator_summary.compare_count >= 0
assert report.decode_estimator_summary.compare_count >= 0
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q
```

Expected: FAIL because the serialized report does not yet expose the fields.

**Step 3: Write minimal implementation**

Ensure normal `PhaseDCompareReport.model_dump(mode="json")` carries the two summaries unchanged.

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q
```

Expected: PASS.

### Task 4: Reconfirm focused compare and downstream keep-green

**Files:**
- Test: `tests/unit/contracts/test_phase_d_compare_report.py`
- Test: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Test: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Test: `tests/smoke/test_cli_run_phase_d_compare.py`
- Test: `tests/unit/visualization/test_catalog_builder.py`
- Test: `tests/unit/visualization/test_workbench_builder.py`
- Test: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Test: `tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Test: `tests/smoke/test_cli_run_visualization_catalog.py`
- Test: `tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Run focused Phase D compare regression**

Run:

```powershell
python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q
```

Expected: PASS.

**Step 2: Run visualization consumer reconfirmation**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS.

### Task 5: Publish the closure update

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-21-spec-13-fit-floor-source-summary.md`

**Step 1: Update docs**

Record that:

- `PhaseDCompareReport` now carries compare-grade estimator summaries
- current estimator trust surfaces are no longer trapped inside `PerfSummaryReport`
- the next remaining `SPEC-13` blocker is closer to deeper cycle-fitting math than missing compare-grade aggregation

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - `PhaseDCompareReport` now exposes:
    - `prefill_estimator_summary`
    - `decode_estimator_summary`
  - compare-grade summaries now carry:
    - compare counts
    - tighter-fit counts
    - average fit-gap deltas
    - average critical-path-gap deltas
    - dominant fitted-gap phase
    - dominant critical-path-gap phase
- downstream follow-on landed after this slice:
  - `../plans/2026-03-21-spec-13-residual-external-stall-fitting.md`
  - estimator math now preserves `schedule_floor` and adds only residual external-read stall, so the next remaining blocker has moved from compare-grade aggregation to richer overlap/stall fidelity
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py -q` -> `4 passed`
  - `python -m pytest tests/unit/analysis/test_phase_d_compare_report_builder.py -q` -> `7 passed`
  - `python -m pytest tests/unit/pipeline/test_phase_d_compare_workflow.py -q` -> `4 passed`
  - `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q` -> `2 passed`
  - `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `17 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- updated interpretation:
  - this slice closes the compare-grade estimator aggregation gap that still sat between `PerfSummaryReport` trust signals and `PhaseDCompareReport`
  - the next remaining `SPEC-13` blocker is now more clearly deeper cycle-fitting math, not missing estimator compare aggregation
