# SPEC-16 Sweep Delta Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable sweep-and-delta foundation that can rerun prefill/decode evaluations across target-profile variants and emit a comparable delta report.

**Architecture:** Introduce a small sweep spec contract plus a sweep delta report contract. The workflow will materialize child run-roots under a sweep workspace, rerun the existing `SPEC-02 -> SPEC-15` pipelines, then aggregate whole-run and macro-hotspot deltas relative to a designated baseline target profile.

**Tech Stack:** Python 3.14, Pydantic models, existing run-root pipeline/CLI pattern, pytest unit/smoke tests.

---

### Task 1: Add Sweep Spec And Delta Report Contracts

**Files:**
- Create: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Create: `tests/unit/contracts/test_sweep_report.py`

**Step 1: Write the failing test**

Add a contract test covering:
- `SweepSpec`
- `SweepRunRecord`
- `SweepComparison`
- `SweepDeltaReport`
- metric deltas and macro deltas

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_sweep_report.py -q`
Expected: FAIL because the contract file does not exist.

**Step 3: Write minimal implementation**

Create:
- `SweepSpec`
- `SweepMacroPoint`
- `SweepRunRecord`
- `SweepMetricDelta`
- `SweepMacroDelta`
- `SweepComparison`
- `SweepIssue`
- `SweepDeltaReport`

Keep it summary-grade. Do not embed full per-run artifacts.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_sweep_report.py -q`
Expected: PASS

### Task 2: Add Sweep Delta Builder

**Files:**
- Create: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/analysis/__init__.py`
- Create: `tests/unit/analysis/test_sweep_report_builder.py`

**Step 1: Write the failing tests**

Add builder tests for:
- per-scenario baseline-vs-candidate metric deltas
- macro hotspot deltas
- failed runs surfacing as issues
- missing baseline surfacing as an issue instead of a crash

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_sweep_report_builder.py -q`
Expected: FAIL because the builder does not exist.

**Step 3: Write minimal implementation**

Implement:
- `build_sweep_delta_report(sweep_name, baseline_target_profile_name, run_records, profile_diff_lookup)`

Use only whole-run metrics plus macro hotspots in this batch. Do not add layer-level diffing.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_sweep_report_builder.py -q`
Expected: PASS

### Task 3: Add Sweep Workflow

**Files:**
- Create: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Create: `tests/unit/pipeline/test_sweep_analysis_workflow.py`

**Step 1: Write the failing tests**

Add workflow tests verifying:
- child run-roots are created under a sweep workspace
- baseline and candidate targets are rerun for declared scenarios
- output is `reports/sweep_delta_report.json`
- invalid sweep specs fail cleanly

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_sweep_analysis_workflow.py -q`
Expected: FAIL because the workflow does not exist.

**Step 3: Write minimal implementation**

Implement:
- `run_sweep_analysis(sweep_spec_path, sweep_root)`
- load and validate sweep spec
- initialize child run-roots
- run existing frontend/memory/tile/schedule/descriptor/perf/top-level eval pipelines
- emit `sweep_delta_report.json`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_sweep_analysis_workflow.py -q`
Expected: PASS

### Task 4: Add CLI And Smoke Gates

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_run_sweep_analysis.py`
- Create: `tests/smoke/test_phase_d_sweep_foundation_matrix.py`

**Step 1: Write the failing tests**

Add smoke tests for:
- `llm-sched run-sweep-analysis --sweep-spec ... --sweep-root ...`
- Gemma3 `single-core/dual-core x prefill/decode` sweep matrix
- `reports/sweep_delta_report.json` existence
- failure path without traceback for invalid baseline target config

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_sweep_analysis.py tests/smoke/test_phase_d_sweep_foundation_matrix.py -q`
Expected: FAIL because the CLI command does not exist.

**Step 3: Write minimal implementation**

Add CLI wiring and user-facing messages only. Do not add parallel execution or layer-level delta logic in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_sweep_analysis.py tests/smoke/test_phase_d_sweep_foundation_matrix.py -q`
Expected: PASS

### Task 5: Docs, Verification, Commit

**Files:**
- Create: `docs/development/phase-d-sweep-foundation-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- stable sweep spec assumptions
- `SweepDeltaReport` shape
- CLI/workflow entrypoint
- what `SPEC-18` may now assume

**Step 2: Run focused verification**

Run:
- `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/smoke/test_cli_run_sweep_analysis.py tests/smoke/test_phase_d_sweep_foundation_matrix.py -q`

Expected: PASS

**Step 3: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 4: Commit**

```bash
git add src/llm_sched/contracts/sweep_report.py src/llm_sched/analysis/sweep_report_builder.py src/llm_sched/pipeline/sweep_analysis.py src/llm_sched/cli/main.py docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-d-sweep-foundation-handoff.md docs/plans/2026-03-07-spec-16-sweep-delta-engine.md tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/smoke/test_cli_run_sweep_analysis.py tests/smoke/test_phase_d_sweep_foundation_matrix.py
git commit -m "feat: add spec 16 sweep delta foundation"
```
