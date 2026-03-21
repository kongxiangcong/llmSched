# SPEC-13 Shared-DMA Bidirectional Stall Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-13` compute fitted-cycle math so external writes and shared-DMA read/write contention contribute to fitted work cycles instead of only external reads.

**Architecture:** Keep the change estimator-local. First extend `TileCandidateResourceSummary` with structured backing-store write bytes so compute descriptors can see both external reads and external writes. Then replace the current read-only external-bandwidth floor with a shared-DMA bidirectional stall model that sums the non-overlappable portions of external read and write pressure above the existing compute overlap budget.

**Tech Stack:** Pydantic contracts, `llm_sched.analysis.descriptor_estimator`, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Add structured external-write backing-store accounting to the tiling contract

**Files:**
- Modify: `src/llm_sched/contracts/tiling_plan.py`
- Modify: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing test**

Extend `_tiling_plan_fixture(...)` so it can emit:

```python
resource_summary=TileCandidateResourceSummary(
    ...,
    storage_write_bytes_by_backing_store={"ddr-backed-staged": 40960},
)
```

and add one focused assertion-driven test that validates the fixture round-trips through pydantic without dropping the new field.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: FAIL because `TileCandidateResourceSummary` does not yet accept structured backing-store write bytes.

**Step 3: Write minimal implementation**

Add the new contract field:

```python
storage_write_bytes_by_backing_store: dict[BackingStoreKind, int] = Field(default_factory=dict)
```

and update the local fixture helper to pass it.

**Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: PASS.

### Task 2: Lock the new shared-DMA bidirectional stall behavior with failing estimator tests

**Files:**
- Modify: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing tests**

Add two focused tests:

```python
def test_estimate_descriptor_analysis_adds_residual_external_write_stall() -> None:
    analysis = estimate_descriptor_analysis(
        ...,
        schedule_ir=_schedule_ir_fixture(),
        tiling_plan=_tiling_plan_fixture(
            ddr_backed_staged_bytes=0,
            ddr_backed_staged_write_bytes=40960,
        ),
    )
    compute_record = ...
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 32.0
    assert compute_record.metrics["fitted_work_cycles"] == 48.0

def test_estimate_descriptor_analysis_adds_bidirectional_shared_dma_stall_above_schedule_floor() -> None:
    analysis = estimate_descriptor_analysis(
        ...,
        schedule_ir=_schedule_ir_fixture(duration_slots=64),
        tiling_plan=_tiling_plan_fixture(
            ddr_backed_staged_bytes=122880,
            ddr_backed_staged_write_bytes=40960,
        ),
    )
    compute_record = ...
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 128.0
    assert compute_record.metrics["fitted_work_cycles"] == 144.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 96.0
    assert "fit-floor:external_bandwidth" in compute_record.tags
```

The second test is the new behavior: shared-DMA demand is `96 + 32 = 128`, overlap budget remains `48`, so fitted cycles become `64 + (128 - 48) = 144`.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: FAIL because the current estimator still ignores external writes.

### Task 3: Implement shared-DMA bidirectional stall fitting

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`

**Step 1: Write minimal implementation**

Inside `_fitted_work_cycle_metrics_for_descriptor(...)`:

- compute `external_read_bytes` from backing-store reads
- compute `external_write_bytes` from backing-store writes
- convert both to cycles with `_bandwidth_cycles(...)`
- define:

```python
external_bandwidth_floor_cycles = external_read_cycles + external_write_cycles
residual_external_stall_cycles = max(0.0, external_bandwidth_floor_cycles - estimated_cycles)
fitted_work_cycles = max(base_fitted_cycles, schedule_floor_cycles + residual_external_stall_cycles)
```

Keep the scope narrow:

- no per-direction public metrics in this slice
- no change to non-compute descriptors
- no compare/report contract additions yet

**Step 2: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q
```

Expected: PASS.

### Task 4: Prove the stronger shared-DMA fit survives perf summary/workflow serialization

**Files:**
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Add assertions that a bidirectional-stall-heavy compute case preserves the stronger fitted topline through:

- `fit_gap_summary.total_fit_gap_cycles`
- `fit_floor_source_summary.external_bandwidth_gap_cycles`
- workflow JSON serialization of `fitted_work_cycles`

Use the same `144.0` fitted topline scenario from Task 2.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: FAIL until the stronger fitted-cycle values are reflected in summaries and serialized artifacts.

**Step 3: Write minimal implementation**

Only update fixture inputs and summary expectations if the underlying estimator outputs have changed. Do not add new report fields in this slice.

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: PASS.

### Task 5: Reconfirm focused SPEC-13 and downstream keep-green

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

### Task 6: Publish the closure update

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-21-spec-13-residual-external-stall-fitting.md`

**Step 1: Update docs**

Record that:

- `SPEC-13` compute fitted-cycle math now includes shared-DMA bidirectional external pressure, not just external reads
- this extends the residual-stall model without reopening compare/report contracts
- the next remaining blocker, if any, is finer-grained overlap budgeting rather than missing external-write awareness

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 5 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - `TileCandidateResourceSummary` now preserves structured `storage_write_bytes_by_backing_store`
  - `_fitted_work_cycle_metrics_for_descriptor(...)` now folds external writes into shared-DMA bandwidth pressure instead of only external reads
  - shared-DMA bidirectional demand now raises `external_bandwidth_floor_cycles`, `fitted_work_cycles`, and `fit_floor_gap_cycles` through the existing residual-stall model
  - regression coverage now proves the stronger fitted topline survives:
    - descriptor-estimator unit tests
    - perf summary aggregation
    - workflow JSON serialization
- fresh verification:
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q` -> `13 passed`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `27 passed`
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- interpretation:
  - this slice closes the remaining read-only blind spot in current `SPEC-13` deeper-cycle fitting
  - the next remaining estimator blocker is finer-grained overlap budgeting or direction-aware stall decomposition beyond the current bidirectional shared-DMA model
- downstream follow-on landed after this slice:
  - `../plans/2026-03-21-spec-13-fit-floor-direction-summary.md`
  - direction-aware read/write floor observability now lives in the canonical perf artifact, so the next remaining blocker has tightened further toward overlap-budget fidelity rather than external-bandwidth attribution
