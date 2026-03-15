# SPEC-14/15 Fitted Topline Adoption Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adopt `SPEC-13`'s new `fitted_work_cycles` surface into the summary-grade prefill and decode top-level reports without changing existing hotspot or layer-row semantics.

**Architecture:** Keep this slice narrow. Reuse the already-landed `PerfSummaryReport.phase_attribution` and `totals["fitted_work_cycles"]` surfaces, and add parallel top-level fitted-cycle fields only where `SPEC-14/15` already expose estimated-cycle summaries. Do not reinterpret existing `estimated_cycles`, `cycles_per_token`, macro hotspots, node hotspots, or layer breakdown rows in this batch.

**Tech Stack:** Python 3.11, Pydantic contracts, existing SPEC-14/15 report builders and workflows, pytest unit/workflow/smoke tests.

---

### Task 1: Adopt fitted-cycle toplines in the prefill report builder

**Files:**
- Modify: `src/llm_sched/contracts/prefill_report.py`
- Modify: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`

**Step 1: Write the failing test**

Extend the prefill builder test so the top-level throughput summary explicitly expects the fitted-cycle surface:

```python
assert report.throughput.fitted_work_cycles == pytest.approx(4608.0)
assert report.throughput.tokens_per_fitted_work_cycle == pytest.approx(128 / 4608.0)
assert report.throughput.fitted_cycles_per_token == pytest.approx(4608.0 / 128.0)
assert report.throughput.projection_fitted_work_cycles == pytest.approx(2048.0)
assert report.throughput.attention_fitted_work_cycles == pytest.approx(2048.0)
assert report.throughput.other_fitted_work_cycles == pytest.approx(512.0)
```

Keep the existing `estimated_cycles` assertions intact so the test locks the “parallel surface, not reinterpretation” policy.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_prefill_report_builder.py -q -x
```

Expected: FAIL because `PrefillThroughputSummary` does not yet expose fitted-cycle fields and the builder only computes estimated-cycle toplines.

**Step 3: Write minimal implementation**

Add only the new top-level fitted-cycle fields to `PrefillThroughputSummary`:

```python
fitted_work_cycles: float = Field(ge=0.0, default=0.0)
tokens_per_fitted_work_cycle: float = Field(ge=0.0, default=0.0)
fitted_cycles_per_token: float = Field(ge=0.0, default=0.0)
projection_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
kv_io_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
attention_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
sync_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
other_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
```

In the builder:
- read `perf_summary.totals["fitted_work_cycles"]` with fallback to `estimated_cycles`
- derive per-phase fitted work cycles from `phase_attribution[phase_name].fitted_work_cycles`
- keep all existing estimated-cycle and byte calculations unchanged

Do not touch macro/node/layer hotspot rows in this task.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Thread the prefill fitted-cycle surface through workflow and smoke outputs

**Files:**
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Modify: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- Modify: `tests/smoke/test_cli_run_prefill_evaluation.py`

**Step 1: Write the failing tests**

Add stable public-surface assertions only:

```python
assert report.throughput.fitted_work_cycles >= report.throughput.estimated_cycles
assert report.throughput.tokens_per_fitted_work_cycle > 0.0
assert report.throughput.projection_fitted_work_cycles >= 0.0
```

And in smoke / CLI JSON checks:

```python
assert report["throughput"]["fitted_work_cycles"] >= report["throughput"]["estimated_cycles"]
assert report["throughput"]["projection_fitted_work_cycles"] >= 0.0
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/smoke/test_phase_d_prefill_foundation_matrix.py `
  tests/smoke/test_cli_run_prefill_evaluation.py -q -x
```

Expected: FAIL because serialized prefill report artifacts do not yet expose the new fitted-cycle top-level fields.

**Step 3: Verify the slice after Task 1 implementation**

No additional production files should need changes if Task 1 is implemented correctly; workflow serialization should pick up the stronger contract automatically.

**Step 4: Run tests to verify they pass**

Run the same command again and expect PASS.

### Task 3: Adopt fitted-cycle toplines in the decode report builder

**Files:**
- Modify: `src/llm_sched/contracts/decode_report.py`
- Modify: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `tests/unit/analysis/test_decode_report_builder.py`

**Step 1: Write the failing test**

Extend the decode builder test so token-latency and KV summary surfaces explicitly consume the fitted-cycle data:

```python
assert report.token_latency.fitted_work_cycles == pytest.approx(3360.0)
assert report.token_latency.fitted_work_cycles_per_token == pytest.approx(3360.0)
assert report.token_latency.kv_io_fitted_work_cycles == pytest.approx(960.0)
assert report.kv_summary.kv_related_fitted_work_cycle_share == pytest.approx(960.0 / 3360.0)
```

Keep the existing estimated-cycle assertions intact.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_decode_report_builder.py -q -x
```

Expected: FAIL because `DecodeLatencySummary` / `DecodeKVSummary` do not yet expose fitted-cycle fields and the builder only computes estimated-cycle toplines.

**Step 3: Write minimal implementation**

Add only the parallel fitted-cycle fields needed for decode toplines:

```python
class DecodeLatencySummary(BaseModel):
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    fitted_work_cycles_per_token: float = Field(ge=0.0, default=0.0)
    projection_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    kv_io_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    attention_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    sync_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    other_fitted_work_cycles: float = Field(ge=0.0, default=0.0)


class DecodeKVSummary(BaseModel):
    kv_related_fitted_work_cycle_share: float = Field(ge=0.0, default=0.0)
```

In the builder:
- read whole-run fitted work cycles from `perf_summary.totals`
- derive per-phase fitted work cycles from `phase_attribution`
- derive `kv_related_fitted_work_cycle_share` from decode `kv_io` fitted work cycles over whole-run fitted work cycles
- keep existing estimated-cycle, bytes, hotspots, and layer-row semantics unchanged

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 4: Thread the decode surface through workflow, smoke, and checkpoints

**Files:**
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Modify: `tests/smoke/test_phase_d_decode_foundation_matrix.py`
- Modify: `tests/smoke/test_cli_run_decode_evaluation.py`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-d-prefill-foundation-handoff.md`
- Modify: `docs/development/phase-d-decode-foundation-handoff.md`

**Step 1: Write the failing tests**

Add decode workflow and smoke assertions:

```python
assert report.token_latency.fitted_work_cycles >= report.token_latency.estimated_cycles
assert report.token_latency.kv_io_fitted_work_cycles >= 0.0
assert report.kv_summary.kv_related_fitted_work_cycle_share >= 0.0
```

And in JSON checks:

```python
assert report["token_latency"]["fitted_work_cycles"] >= report["token_latency"]["estimated_cycles"]
assert report["kv_summary"]["kv_related_fitted_work_cycle_share"] >= 0.0
```

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/smoke/test_phase_d_decode_foundation_matrix.py `
  tests/smoke/test_cli_run_decode_evaluation.py -q -x
```

Expected: FAIL because serialized decode report artifacts do not yet expose the new fitted-cycle top-level fields.

**Step 3: Run the full focused regression surface**

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/smoke/test_phase_d_prefill_foundation_matrix.py `
  tests/smoke/test_phase_d_decode_foundation_matrix.py `
  tests/smoke/test_cli_run_prefill_evaluation.py `
  tests/smoke/test_cli_run_decode_evaluation.py -q
```

Expected: PASS.

**Step 4: Update narrow Phase D checkpoints**

Add one narrow roadmap / handoff note that:
- `SPEC-14/15` now consume `SPEC-13` fitted-cycle toplines in prefill/decode top-level reports
- the adoption is intentionally summary-grade
- macro/node/layer hotspot and compare-grade fitted-cycle work remains later `SPEC-16` or follow-on `SPEC-14/15` work
