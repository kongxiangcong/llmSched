# Phase D Compare Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a standalone Phase D compare artifact and CLI that lifts structured prefill/decode compare summaries out of `sweep_delta_report.json` into a dedicated machine-readable report.

**Architecture:** Reuse the existing `SPEC-16` sweep output as the narrowest upstream dependency instead of opening a second rerun workflow. Add one dedicated compare report contract plus one builder/workflow/CLI that reads `reports/sweep_delta_report.json`, groups mode-aware compare rows into explicit prefill/decode sections, and writes `reports/phase_d_compare_report.json` under the sweep root.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep analysis workflow/CLI, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q`
  - `5 passed in 0.27s`
- `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q`
  - `2 passed in 212.46s`

---

### Task 1: Add Failing Tests For The Standalone Compare Artifact

**Files:**
- Create: `tests/unit/contracts/test_phase_d_compare_report.py`
- Create: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Create: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Create: `tests/smoke/test_cli_run_phase_d_compare.py`

**Step 1: Write the failing tests**

Assert that:
- the new compare report contract accepts explicit prefill and decode sections
- the builder converts `SweepComparison.prefill_compare` / `decode_compare` into dedicated report rows
- the workflow reads `reports/sweep_delta_report.json` from a sweep root and writes `reports/phase_d_compare_report.json`
- the CLI command works on a cached prepared sweep root without rerunning the entire sweep

**Step 2: Run the tests to verify RED**

Run:
```powershell
python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q
python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q
```

Expected: FAIL because no standalone Phase D compare contract/workflow exists yet.

### Task 2: Implement The Minimal Compare Report

**Files:**
- Create: `src/llm_sched/contracts/phase_d_compare_report.py`
- Create: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Create: `src/llm_sched/pipeline/phase_d_compare.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Modify: `src/llm_sched/analysis/__init__.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Modify: `src/llm_sched/cli/main.py`

**Step 1: Add the compare contract**

Define:
- one prefill compare row model
- one decode compare row model
- one top-level report model with counts, baseline target, and passthrough issues

Reuse the existing grouped scalar deltas from `SweepScalarDelta` instead of cloning another delta schema.

**Step 2: Add the analysis builder**

Implement one builder that:
- accepts a `SweepDeltaReport`
- splits comparisons into explicit prefill/decode sections
- copies `profile_diff_fields`, schedule kinds, top-level delta groups, and one lightweight layer-delta count summary

**Step 3: Add the workflow and CLI**

Implement one workflow:
- input: `sweep_root`
- read: `reports/sweep_delta_report.json`
- write: `reports/phase_d_compare_report.json`

Expose it as:
- `run-phase-d-compare --sweep-root <path>`

Do not add visualization consumers in this slice.

### Task 3: Verify And Record The Artifact

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-phase-d-compare-report.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q
python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q
```

Expected: PASS.

**Step 2: Update roadmap with one narrow checkpoint**

If verification is green, record that Phase D now has a standalone compare artifact more explicit than sweep-only consumption, and that downstream consumers no longer need to parse raw `SweepComparison` records directly.
