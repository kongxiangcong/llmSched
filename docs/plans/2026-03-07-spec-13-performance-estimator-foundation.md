# SPEC-13 Performance Estimator Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable descriptor-driven performance estimation and bottleneck reporting foundation for single-core and dual-core scheduled runs.

**Architecture:** Reuse the current `DescriptorIR`, `ISACoverageReport`, `ScheduleIR`, and `MemoryPlanArtifact` as the only stable inputs. First freeze a lightweight performance summary contract and a deterministic descriptor-driven `AnalysisIR` estimator. Then add a run-root workflow and CLI that emit a stable perf analysis artifact plus a summary report without pretending to be RTL-accurate.

**Tech Stack:** Python 3.14, Pydantic models, existing run-root pipeline/CLI pattern, pytest unit/smoke tests.

---

### Task 1: Add Performance Summary Contract

**Files:**
- Create: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Create: `tests/unit/contracts/test_perf_report.py`

**Step 1: Write the failing test**

Add a contract test for:
- `totals`
- `per_macro_cycles`
- `per_macro_bytes`
- `bottleneck_counts`
- `isa_gap_counts`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`
Expected: FAIL because the contract file does not exist.

**Step 3: Write minimal implementation**

Create:
- `PerfSummaryReport`
- `PerfBottleneckIssue`

Keep this report summary-only. Do not embed the whole `AnalysisIR`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`
Expected: PASS

### Task 2: Add Descriptor-Driven Estimator

**Files:**
- Create: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `src/llm_sched/analysis/__init__.py`
- Create: `tests/unit/analysis/test_descriptor_estimator.py`

**Step 1: Write the failing tests**

Add estimator tests for:
- single-core compute descriptors emitting positive cycles/bytes with `compute-bound` tags
- DMA descriptors emitting memory-dominated metrics
- transfer descriptors emitting sync/cross-core costs
- ISA coverage gaps producing `isa-gap-bound` records

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q`
Expected: FAIL because the estimator does not exist.

**Step 3: Write minimal implementation**

Implement:
- `estimate_descriptor_analysis(descriptor_ir, coverage_report, hardware, scenario) -> AnalysisIR`
- abstract compute-cycle estimation from `shape_pack` and target capabilities
- DMA / transfer byte and cycle estimation from descriptor fields and target bandwidth/sync fields
- bottleneck tags: `compute-bound`, `memory-bound`, `sync-bound`, `isa-gap-bound`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_descriptor_estimator.py -q`
Expected: PASS

### Task 3: Add Perf Summary Builder

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Create: `tests/unit/analysis/test_perf_summary_builder.py`

**Step 1: Write the failing test**

Add a summary-builder test verifying:
- whole-run totals
- per-macro cycle aggregation
- per-macro byte aggregation
- bottleneck counts
- ISA gap counts

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`
Expected: FAIL because the summary builder does not exist.

**Step 3: Write minimal implementation**

Implement:
- `build_perf_summary_report(run_id, descriptor_ir, analysis_ir, coverage_report)`

Use only existing artifacts. Do not add layer breakdown in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`
Expected: PASS

### Task 4: Add Run-Root Workflow

**Files:**
- Create: `src/llm_sched/pipeline/performance_estimation.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Create: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing test**

Add a workflow test verifying:
- input artifacts are `descriptor_ir`, `isa_coverage_report`, and schedule/memory artifacts
- outputs are `artifacts/perf_analysis_ir.json` and `reports/perf_summary_report.json`
- manifest/run-summary updates are stable

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py -q`
Expected: FAIL because the workflow does not exist.

**Step 3: Write minimal implementation**

Implement:
- `run_performance_estimation(run_root)`
- load descriptor + coverage + target/scenario
- emit perf analysis IR and perf summary report
- update `manifest.artifact_index`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py -q`
Expected: PASS

### Task 5: Add CLI And Smoke Gates

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_run_performance_estimation.py`
- Create: `tests/smoke/test_phase_d_perf_foundation_matrix.py`

**Step 1: Write the failing tests**

Add smoke tests for:
- `llm-sched run-performance-estimation --run-root ...`
- Gemma3 `single/dual-core x prefill/decode` matrix
- `perf_analysis_ir.json` and `perf_summary_report.json` existence
- failure path without traceback when descriptor artifacts are missing

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_phase_d_perf_foundation_matrix.py -q`
Expected: FAIL because the CLI command does not exist.

**Step 3: Write minimal implementation**

Add CLI wiring and user-facing messages only. Do not add extra command-line switches in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_phase_d_perf_foundation_matrix.py -q`
Expected: PASS

### Task 6: Docs, Verification, Commit

**Files:**
- Create: `docs/development/phase-d-performance-foundation-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- stable descriptor-driven `AnalysisIR` assumptions
- `PerfSummaryReport` shape
- CLI/workflow entrypoint
- what `SPEC-14/15` may now assume

**Step 2: Run focused verification**

Run:
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_descriptor_estimator.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_phase_d_perf_foundation_matrix.py -q`

Expected: PASS

**Step 3: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 4: Commit**

```bash
git add src/llm_sched/contracts/perf_report.py src/llm_sched/analysis/descriptor_estimator.py src/llm_sched/pipeline/performance_estimation.py src/llm_sched/cli/main.py docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-d-performance-foundation-handoff.md tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_descriptor_estimator.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_phase_d_perf_foundation_matrix.py
git commit -m "feat: add spec 13 performance estimator foundation"
```
