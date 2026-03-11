# SPEC-14 Prefill Evaluation Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable prefill-only top-level evaluation pipeline on top of the existing descriptor-driven performance artifacts.

**Architecture:** Reuse the current run-root chain through `run-performance-estimation` and add a thin aggregation layer for prefill scenarios only. The new foundation should consume stable perf, coverage, and memory artifacts, emit a single prefill-facing report, and reject decode scenarios explicitly instead of silently misusing the prefill report shape.

**Tech Stack:** Python 3.14, Pydantic models, existing run-root pipeline/CLI pattern, pytest unit/smoke tests.

---

### Task 1: Add Prefill Evaluation Report Contract

**Files:**
- Create: `src/llm_sched/contracts/prefill_report.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Create: `tests/unit/contracts/test_prefill_report.py`

**Step 1: Write the failing test**

Add a contract test covering:
- `run_id`
- `graph_id`
- `scenario_name`
- `schedule_kind`
- `throughput`
- `memory_summary`
- `isa_summary`
- `macro_hotspots`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_prefill_report.py -q`
Expected: FAIL because the contract file does not exist.

**Step 3: Write minimal implementation**

Create:
- `PrefillThroughputSummary`
- `PrefillMemorySummary`
- `PrefillISASummary`
- `PrefillMacroHotspot`
- `PrefillEvaluationReport`

Keep it summary-only. Do not embed full IR artifacts.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_prefill_report.py -q`
Expected: PASS

### Task 2: Add Prefill Report Builder

**Files:**
- Create: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `src/llm_sched/analysis/__init__.py`
- Create: `tests/unit/analysis/test_prefill_report_builder.py`

**Step 1: Write the failing tests**

Add builder tests for:
- prefill scenarios producing positive throughput fields
- GEMM-heavy perf summaries being recognized as MXU-dominant
- memory-plan diagnostics being aggregated into memory summary
- ISA gap counts being surfaced in the top-level report
- decode scenarios being rejected explicitly

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_prefill_report_builder.py -q`
Expected: FAIL because the builder does not exist.

**Step 3: Write minimal implementation**

Implement:
- `build_prefill_evaluation_report(run_id, scenario, perf_summary, coverage_report, memory_plan)`

Use only existing artifact contracts. Do not add per-layer breakdown in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_prefill_report_builder.py -q`
Expected: PASS

### Task 3: Add Run-Root Workflow

**Files:**
- Create: `src/llm_sched/pipeline/prefill_evaluation.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Create: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`

**Step 1: Write the failing test**

Add a workflow test verifying:
- input artifacts are `perf_summary_report`, `isa_coverage_report`, and `memory_plan`
- output is `reports/prefill_evaluation_report.json`
- manifest/run-summary updates are stable
- decode scenarios fail cleanly

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_prefill_evaluation_workflow.py -q`
Expected: FAIL because the workflow does not exist.

**Step 3: Write minimal implementation**

Implement:
- `run_prefill_evaluation(run_root)`
- load perf summary + coverage + memory plan + scenario
- reject non-prefill scenarios with a clear diagnostic
- emit `prefill_evaluation_report.json`
- update `manifest.artifact_index`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_prefill_evaluation_workflow.py -q`
Expected: PASS

### Task 4: Add CLI And Smoke Gates

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_run_prefill_evaluation.py`
- Create: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`

**Step 1: Write the failing tests**

Add smoke tests for:
- `llm-sched run-prefill-evaluation --run-root ...`
- Gemma3 `single-core/dual-core x prefill` matrix
- `prefill_evaluation_report.json` existence
- failure path without traceback for decode scenarios

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_phase_d_prefill_foundation_matrix.py -q`
Expected: FAIL because the CLI command does not exist.

**Step 3: Write minimal implementation**

Add CLI wiring and user-facing messages only. Do not add auto-rerun of the full compile pipeline in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_phase_d_prefill_foundation_matrix.py -q`
Expected: PASS

### Task 5: Docs, Verification, Commit

**Files:**
- Create: `docs/development/phase-d-prefill-foundation-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- stable prefill evaluation assumptions
- `PrefillEvaluationReport` shape
- CLI/workflow entrypoint
- what `SPEC-15/16/18` may now assume

**Step 2: Run focused verification**

Run:
- `python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_phase_d_prefill_foundation_matrix.py -q`

Expected: PASS

**Step 3: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 4: Commit**

```bash
git add src/llm_sched/contracts/prefill_report.py src/llm_sched/analysis/prefill_report_builder.py src/llm_sched/pipeline/prefill_evaluation.py src/llm_sched/cli/main.py docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-d-prefill-foundation-handoff.md docs/plans/2026-03-07-spec-14-prefill-eval-pipeline.md tests/unit/contracts/test_prefill_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_phase_d_prefill_foundation_matrix.py
git commit -m "feat: add spec 14 prefill evaluation foundation"
```
