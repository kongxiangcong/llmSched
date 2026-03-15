# SPEC-14/15 Fitted Layer Hotspots Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-14` and `SPEC-15` so prefill/decode reports expose fitted-cycle data not only in top-level summaries, but also in `node_hotspots` and `layer_breakdown`.

**Architecture:** Keep this slice inside the existing `PerfSummaryReport -> prefill/decode report builders -> workflow/CLI artifacts` chain. Reuse the already-stable `per_node_fitted_work_cycles` and `per_layer_fitted_work_cycles` surfaces from `SPEC-13`, then thread them into `PrefillEvaluationReport` and `DecodeEvaluationReport` without changing existing estimated-cycle fields or compare contracts in this batch.

**Tech Stack:** Python 3.11, Pydantic contracts, existing Phase D analysis builders, pytest unit/workflow/smoke tests.

---

### Task 1: Add fitted-cycle fields to prefill/decode hotspot and layer contracts

**Files:**
- Modify: `src/llm_sched/contracts/prefill_report.py`
- Modify: `src/llm_sched/contracts/decode_report.py`
- Modify: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`
- Modify: `tests/unit/analysis/test_decode_report_builder.py`

**Step 1: Write the failing tests**

Extend builder coverage to lock the new fitted surfaces on both node hotspots and layer rows:

```python
assert report.node_hotspots[0].fitted_work_cycles == pytest.approx(3328.0)
assert report.node_hotspots[0].fitted_cycle_share == pytest.approx(3328.0 / 4608.0)
assert report.layer_breakdown[0].fitted_work_cycles == pytest.approx(3328.0)
assert report.layer_breakdown[0].fitted_cycle_share == pytest.approx(3328.0 / 4608.0)
```

Mirror the same assertions in decode coverage using decode fixture numbers.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py -q -x
```

Expected: FAIL because hotspot/layer contracts do not yet expose fitted fields.

**Step 3: Write minimal implementation**

Add only the new parallel fields needed for this slice:

```python
class PrefillNodeHotspot(BaseModel):
    ...
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    fitted_cycle_share: float = Field(ge=0.0, default=0.0)
```

Apply the same pattern to:
- `PrefillLayerBreakdownRow`
- `DecodeNodeHotspot`
- `DecodeLayerBreakdownRow`

Then update the prefill/decode report builders so they:
- read fitted totals from `perf_summary.per_node_fitted_work_cycles` / `perf_summary.per_layer_fitted_work_cycles`
- fall back to `estimated_cycles` when fitted values are absent
- compute `fitted_cycle_share` against report-level fitted totals, with `0.0` when the denominator is zero

Do not change `macro_hotspots`, top-level throughput/latency summaries, or any compare/report-builder surfaces outside node/layer rows in this task.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Preserve the new surface through workflow and smoke artifacts

**Files:**
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Modify: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- Modify: `tests/smoke/test_phase_d_decode_foundation_matrix.py`

**Step 1: Write the failing tests**

Add workflow and smoke assertions that only lock the stable serialized public surface:

```python
assert report.node_hotspots[0].fitted_work_cycles >= report.node_hotspots[0].estimated_cycles
assert report.node_hotspots[0].fitted_cycle_share >= 0.0
assert report.layer_breakdown[0].fitted_work_cycles >= report.layer_breakdown[0].estimated_cycles
assert report.layer_breakdown[0].fitted_cycle_share >= 0.0
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/smoke/test_phase_d_prefill_foundation_matrix.py `
  tests/smoke/test_phase_d_decode_foundation_matrix.py -q -x
```

Expected: FAIL because serialized reports do not yet include the new fitted node/layer fields.

**Step 3: Write minimal implementation**

No pipeline contract changes should be needed beyond Task 1. Let the existing builders and report serialization carry the new fields into workflow/CLI artifacts.

If a workflow test reveals missing propagation, make the smallest builder or contract fix necessary; do not widen scope into compare builders or visualization consumers in this batch.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 3: Verify the SPEC-14/15 regression surface and record the checkpoint

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-15-spec-14-15-fitted-layer-hotspots.md`
- Test: `tests/unit/analysis/test_prefill_report_builder.py`
- Test: `tests/unit/analysis/test_decode_report_builder.py`
- Test: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Test: `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Test: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- Test: `tests/smoke/test_phase_d_decode_foundation_matrix.py`

**Step 1: Run focused regression verification**

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/smoke/test_phase_d_prefill_foundation_matrix.py `
  tests/smoke/test_phase_d_decode_foundation_matrix.py -q
```

Expected: PASS.

**Step 2: Update the roadmap checkpoint**

Add one narrow roadmap note that:
- `SPEC-14/15` node hotspots and layer rows now expose fitted-cycle fields beside estimated-cycle fields
- this slice stays report-local and does not yet add fitted compare rows to `SPEC-16`
- any later compare/view adoption should consume these richer report surfaces instead of rebuilding fitted node/layer rollups ad hoc

## 2026-03-15 Task 3 Execution Record

- focused `SPEC-14/15` regression verification:
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q`
  - result: `16 passed in 34.11s`
- closure evidence:
  - `PrefillEvaluationReport.node_hotspots` and `PrefillEvaluationReport.layer_breakdown` now expose `fitted_work_cycles` and `fitted_cycle_share`
  - `DecodeEvaluationReport.node_hotspots` and `DecodeEvaluationReport.layer_breakdown` now expose `fitted_work_cycles` and `fitted_cycle_share`
  - workflow and smoke serialization required no extra production-code changes beyond the builder/contract slice because the new fields already propagated through the existing report pipeline
- scope intentionally held:
  - no changes to `macro_hotspots`
  - no new `SPEC-16` compare rows or visualization payload changes in this slice
