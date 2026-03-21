# Project Closeout Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decide whether the project can now be treated as close-enough for overall closeout, with any remaining work reclassified as downstream polish instead of active blockers.

**Architecture:** This is a docs-first audit plus verification slice. It re-reads the current roadmap/README status, reruns the highest-signal keep-green commands, and then publishes a project-level closeout judgment in the roadmap and README. No new product feature or contract expansion belongs in this slice.

**Tech Stack:** Markdown planning docs, roadmap/README status docs, focused `pytest` smoke and regression commands

---

### Task 1: Reconfirm the project boundary

**Files:**
- Read: `D:/workspace/llmSched/README.md`
- Read: `D:/workspace/llmSched/docs/development/evaluation-compiler-roadmap.md`
- Read: `D:/workspace/llmSched/docs/plans/2026-03-21-m3-close-out-blocker-audit.md`
- Read: `D:/workspace/llmSched/docs/plans/2026-03-22-spec-16-spec-19-closeout.md`

**Step 1: Re-read the current stop-lines**

Confirm the current docs already treat these lanes as practically closed:

- `SPEC-13`
- `SPEC-14/15`
- `SPEC-16` recommendation-detail
- `SPEC-19` current static catalog/workbench surface

**Step 2: Define the audit question**

Use one explicit question for the rest of the slice:

- are there any remaining true blockers that justify keeping the project open by default?

### Task 2: Re-run project-level keep-green proof

**Files:**
- Test: `D:/workspace/llmSched/tests/smoke`
- Test: `D:/workspace/llmSched/tests/unit/analysis/test_descriptor_estimator.py`
- Test: `D:/workspace/llmSched/tests/unit/contracts/test_perf_report.py`
- Test: `D:/workspace/llmSched/tests/unit/analysis/test_perf_summary_builder.py`
- Test: `D:/workspace/llmSched/tests/unit/pipeline/test_performance_estimation_workflow.py`
- Test: `D:/workspace/llmSched/tests/smoke/test_phase_d_perf_foundation_matrix.py`
- Test: `D:/workspace/llmSched/tests/smoke/test_cli_run_performance_estimation.py`
- Test: `D:/workspace/llmSched/tests/unit/visualization/test_catalog_builder.py`
- Test: `D:/workspace/llmSched/tests/unit/visualization/test_workbench_builder.py`
- Test: `D:/workspace/llmSched/tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Test: `D:/workspace/llmSched/tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Test: `D:/workspace/llmSched/tests/smoke/test_cli_run_visualization_catalog.py`
- Test: `D:/workspace/llmSched/tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Run broader smoke proof**

Run:

```powershell
python -m pytest tests/smoke -m local_smoke -q
python -m pytest tests/smoke -m milestone_matrix -q
```

Expected: pass

**Step 2: Re-run highest-signal Phase D proof**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q
```

Expected: pass

**Step 3: Re-run highest-signal visualization proof**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: pass

### Task 3: Publish the closeout judgment

**Files:**
- Modify: `D:/workspace/llmSched/README.md`
- Modify: `D:/workspace/llmSched/docs/development/evaluation-compiler-roadmap.md`
- Create or modify: `D:/workspace/llmSched/docs/plans/2026-03-22-project-closeout-audit.md`

**Step 1: Record the result**

If Task 2 stays green, write the judgment as:

- project is now at `close-enough / practical stop-line`
- remaining work is downstream polish, targeted follow-up, or future research
- reopening should require concrete failing evidence

**Step 2: Keep the exclusions explicit**

State that this slice does not reopen:

- new `SPEC-19` convenience interaction by default
- frozen `SPEC-16` recommendation-detail expansion
- closed `SPEC-13` fidelity polish

### Task 4: Final verification and commit

**Files:**
- Modify if needed: `D:/workspace/llmSched/docs/plans/2026-03-22-project-closeout-audit.md`

**Step 1: Re-read git diff and status**

Confirm the slice only changed audit/status docs.

**Step 2: Commit**

Commit the audit if the verification evidence supports the closeout judgment.

---

## Audit Result

- judgment: `close-enough / practical stop-line`
- why this now holds:
  - broader keep-green remains fresh green through `local_smoke` and `milestone_matrix`
  - the current `SPEC-13` estimator lane remains green on its highest-signal focused regression selection
  - the current `SPEC-19` static catalog/workbench surface remains green on its highest-signal focused regression selection
  - earlier closure decisions for `SPEC-13`, `SPEC-14/15`, and `SPEC-16` recommendation-detail still align with the current roadmap and README
- fresh verification evidence:
  - `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
  - `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `32 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- exclusion boundary:
  - do not reopen frozen `SPEC-16` recommendation-detail expansion by default
  - do not keep the project open for `SPEC-19` richer screenshot or convenience polish
  - do not reopen closed `SPEC-13` fidelity polish without new concrete failing evidence
