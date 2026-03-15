# SPEC-13 Deeper Cycle Model Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a tile- and memory-aware `fitted_work_cycles` surface to `SPEC-13`, so performance artifacts preserve the current summary-grade `estimated_cycles` contract while also exposing a deeper fitted work-cycle model for totals, phases, macro/node/layer rollups, and future downstream compare work.

**Architecture:** Keep the new work inside the existing `DescriptorIR -> AnalysisIR -> PerfSummaryReport` chain. Compute a per-record `fitted_work_cycles` metric in `estimate_descriptor_analysis(...)` using current descriptor work estimates plus schedule duration floors and optional tiling-plan-backed external-memory pressure, then aggregate that new metric in `build_perf_summary_report(...)` without rewriting existing `estimated_cycles`, `critical_path_cycles`, prefill/decode top-line metrics, or visualization compare semantics.

**Tech Stack:** Python 3.11, Pydantic contracts, existing SPEC-13 analysis/pipeline modules, optional `TilingPlanArtifact` reuse, pytest unit/workflow/smoke tests.

---

### Task 1: Add estimator-level fitted work-cycle coverage

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing tests**

Add direct estimator coverage that proves the new per-record metric exists and that optional tiling-plan memory pressure can raise the fitted value above the current summary-grade estimate:

```python
analysis = estimate_descriptor_analysis(
    _descriptor_ir_fixture(),
    _coverage_report_fixture(),
    _test_target_profile(),
    _test_prefill_scenario(),
    schedule_ir=_schedule_ir_fixture(),
    tiling_plan=_tiling_plan_fixture(ddr_backed_staged_bytes=122880),
)

compute_record = next(
    record for record in analysis.records if record.subject_id == "sched.block.linear.compute"
)

assert compute_record.metrics["estimated_cycles"] == 48.0
assert compute_record.metrics["fitted_work_cycles"] == 96.0
```

Add a second test that locks the backward-compatible fallback:

```python
analysis = estimate_descriptor_analysis(
    _descriptor_ir_fixture(),
    _coverage_report_fixture(),
    _test_target_profile(),
    _test_prefill_scenario(),
)

compute_record = next(
    record for record in analysis.records if record.subject_id == "sched.block.linear.compute"
)

assert compute_record.metrics["fitted_work_cycles"] == compute_record.metrics["estimated_cycles"]
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q -x
```

Expected: FAIL because `estimate_descriptor_analysis(...)` does not yet accept the extra context and emitted metrics do not include `fitted_work_cycles`.

**Step 3: Write minimal implementation**

Implement the smallest estimator-only slice:

```python
def estimate_descriptor_analysis(
    descriptor_ir,
    coverage_report,
    hardware,
    scenario,
    *,
    schedule_ir: ScheduleIR | None = None,
    memory_plan: MemoryPlanArtifact | None = None,
    tiling_plan: TilingPlanArtifact | None = None,
) -> AnalysisIR:
    ...
    metrics["fitted_work_cycles"] = _fitted_work_cycles_for_descriptor(
        descriptor=descriptor,
        metrics=metrics,
        schedule_block=schedule_block_by_id.get(descriptor.schedule_block_id),
        tiling_candidate=tiling_candidate_by_id.get(schedule_block.tiling_candidate_id)
        if schedule_block is not None and schedule_block.tiling_candidate_id is not None
        else None,
        capabilities=capabilities,
    )
```

Keep the new helper conservative:
- start from the current `estimated_cycles`
- keep `duration_slots` as a lower bound
- when a tiling candidate exposes `resource_summary.storage_read_bytes_by_backing_store`, convert DDR-backed staged / persistent reads into a memory-cycle floor using existing bandwidth helpers
- when tiling-plan evidence is missing, fall back to the current descriptor-only result instead of failing

Do not change current tags or existing metric keys in this batch.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Aggregate fitted work cycles into canonical perf summaries

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`

**Step 1: Write the failing tests**

Extend the perf contract and builder coverage so the new metric survives aggregation:

```python
report = build_perf_summary_report(
    run_id="run-spec13-summary",
    descriptor_ir=descriptor_ir,
    analysis_ir=analysis_ir_with_fitted_cycles(),
    coverage_report=coverage,
    scenario=_prefill_scenario_fixture(),
    schedule_ir=schedule_ir,
    memory_plan=_memory_plan_fixture(),
)

assert report.totals["fitted_work_cycles"] == 90.0
assert report.phase_attribution["projection"].fitted_work_cycles == 64.0
assert report.per_macro_fitted_work_cycles == {"WDQ_GEMM": 90.0}
assert report.per_node_fitted_work_cycles["nig.node.linear.0"] == 64.0
assert report.per_layer_fitted_work_cycles["0"] == 64.0
```

In `tests/unit/contracts/test_perf_report.py`, validate the new stable fields explicitly:

```python
assert report.phase_attribution["projection"].fitted_work_cycles == 880.0
assert report.per_node_fitted_work_cycles["nig.node.linear.0"] == 880.0
assert report.per_layer_fitted_work_cycles["0"] == 880.0
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` and `PerfSummaryReport` do not yet expose fitted-cycle fields and the perf builder does not aggregate them.

**Step 3: Write minimal implementation**

Add only the new parallel surfaces needed for `SPEC-13`:

```python
class PerfPhaseSummary(BaseModel):
    ...
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)


class PerfSummaryReport(BaseModel):
    ...
    per_macro_fitted_work_cycles: dict[str, float] = Field(default_factory=dict)
    per_node_fitted_work_cycles: dict[str, float] = Field(default_factory=dict)
    per_layer_fitted_work_cycles: dict[str, float] = Field(default_factory=dict)
```

Update `build_perf_summary_report(...)` so it:
- sums `record.metrics["fitted_work_cycles"]` into `totals["fitted_work_cycles"]`
- rolls the new metric into per-macro, per-node, and per-layer dictionaries
- carries phase-local `fitted_work_cycles` beside the existing `estimated_cycles`, cycle components, occupied slots, and pressure breakdowns

Do not rename or reinterpret the existing `estimated_cycles` surfaces in this batch.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 3: Thread the new surface through the performance-estimation workflow

**Files:**
- Modify: `src/llm_sched/pipeline/performance_estimation.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`
- Modify: `tests/smoke/test_phase_d_perf_foundation_matrix.py`
- Modify: `tests/smoke/test_cli_run_performance_estimation.py`

**Step 1: Write the failing tests**

Add workflow and smoke assertions that only lock the stable public surface:

```python
assert summary_report.totals["fitted_work_cycles"] >= summary_report.totals["estimated_cycles"]
assert summary_report.phase_attribution["other"].fitted_work_cycles >= 0.0
assert summary_report.per_node_fitted_work_cycles
assert summary_report.per_layer_fitted_work_cycles
```

And in smoke:

```python
assert perf_report["totals"]["fitted_work_cycles"] >= perf_report["totals"]["estimated_cycles"]
assert perf_report["phase_attribution"]["projection"]["fitted_work_cycles"] >= 0.0
assert perf_report["per_node_fitted_work_cycles"]
assert perf_report["per_layer_fitted_work_cycles"]
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/smoke/test_phase_d_perf_foundation_matrix.py `
  tests/smoke/test_cli_run_performance_estimation.py -q -x
```

Expected: FAIL because the serialized workflow artifacts do not yet include the new fitted-cycle surfaces.

**Step 3: Write minimal implementation**

Teach the workflow to consume optional tiling-plan context without creating a new hard dependency:

```python
tiling_plan = _load_optional_ir(
    layout.run_root / Path(artifact_index.get("tiling_plan", "artifacts/tiling_plan.json")),
    TilingPlanArtifact,
)

analysis_ir = estimate_descriptor_analysis(
    descriptor_ir,
    coverage_report,
    target_profile,
    scenario_profile,
    schedule_ir=schedule_ir,
    memory_plan=memory_plan,
    tiling_plan=tiling_plan,
)
```

Requirements for this slice:
- missing `tiling_plan.json` must stay non-fatal for older or minimal fixtures
- real smoke runs should opportunistically use tiling-plan data when present
- report serialization should expose the new fields automatically once the perf builder returns them

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 4: Verify the regression surface and record the checkpoint

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-15-spec-13-deeper-cycle-model.md`
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

**Step 1: Run focused SPEC-13 verification**

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_descriptor_estimator.py `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/smoke/test_phase_d_perf_foundation_matrix.py `
  tests/smoke/test_cli_run_performance_estimation.py -q
```

Expected: PASS.

**Step 2: Run downstream Phase D regression checks**

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

Expected: PASS, proving the richer `PerfPhaseSummary` contract does not regress existing `SPEC-14/15` consumers.

**Step 3: Update the roadmap checkpoint**

Add one narrow roadmap note that:
- `SPEC-13` now exposes tile-/memory-aware `fitted_work_cycles` beside the older `estimated_cycles`
- the new surface is available at totals, phase, macro, node, and layer granularity
- prefill/decode top-level adoption and richer compare surfaces remain later `SPEC-14/15/16` work, not part of this batch

## 2026-03-15 Task 4 Execution Record

- focused `SPEC-13` verification:
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q`
  - result: `19 passed in 27.55s`
- downstream Phase D regression verification:
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q`
  - result: `16 passed in 33.79s`
- roadmap checkpoint updated in `docs/development/evaluation-compiler-roadmap.md`
- scope intentionally held:
  - no `SPEC-14/15/16` compare-surface changes in this task
  - no reinterpretation of existing `estimated_cycles` semantics in this task
