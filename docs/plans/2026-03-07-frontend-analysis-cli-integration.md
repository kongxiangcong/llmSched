# Frontend Analysis CLI Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an end-to-end CLI path that consumes an initialized run, executes `ONNX -> GraphIR -> canonical GraphIR -> NIG -> AnalysisIR`, and writes stable artifacts/reports back into the run directory.

**Architecture:** Keep `init-run` as a pure setup command and add a separate `run-frontend-analysis` command. Put the orchestration logic in a reusable workflow module, not in the CLI entrypoint, so later tiling / scheduling stages can extend the same run-root driven flow. Persist IR dumps in `dumps/`, persist legality and analysis summaries in `reports/`, and update `manifest.json` / `run-summary.json` on success or failure.

**Tech Stack:** Python 3.14, `typer`, Pydantic contracts, JSON artifacts, ONNX frontend, AnalysisIR estimator.

---

### Task 1: Add failing CLI smoke tests

**Files:**
- Modify: `tests/smoke/test_cli_help.py`
- Create: `tests/smoke/test_cli_run_frontend_analysis.py`

**Step 1: Write the failing tests**

Add smoke tests that:
- verify `llm-sched --help` lists `run-frontend-analysis`
- initialize a run and then execute `run-frontend-analysis --run-root ...`
- assert the command writes:
  - `dumps/graph_ir.json`
  - `dumps/canonical_graph_ir.json`
  - `dumps/nig_ir.json`
  - `dumps/analysis_ir.json`
  - `reports/frontend_legality.json`
  - `reports/pseudo_fallback_summary.json`
- assert `manifest.json` and `run-summary.json` move to `completed`

**Step 2: Run the smoke tests**

Run:

```powershell
python -m pytest tests/smoke/test_cli_help.py tests/smoke/test_cli_run_frontend_analysis.py -v
```

Expected: FAIL because the command does not exist yet.

### Task 2: Add workflow-level failing tests

**Files:**
- Create: `tests/unit/pipeline/test_frontend_analysis_workflow.py`

**Step 1: Write the failing tests**

Add unit tests for a workflow function that:
- loads manifest/profile/scenario/model metadata
- produces the four IR dumps
- emits legality diagnostics
- writes a pseudo/fallback summary with macro counts and totals

Use a temporary run root plus checked-in Gemma3 paths.

**Step 2: Run the focused workflow test**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py -v
```

Expected: FAIL because workflow module does not exist.

### Task 3: Implement the frontend analysis workflow

**Files:**
- Create: `src/llm_sched/pipeline/__init__.py`
- Create: `src/llm_sched/pipeline/frontend_analysis.py`
- Modify: `src/llm_sched/contracts/manifest.py`
- Modify: `src/llm_sched/contracts/run_summary.py`

**Step 1: Implement the reusable workflow**

Add a workflow entrypoint that:
- loads `manifest.json`
- resolves target/scenario/model/config paths
- builds Gemma3 shape bindings
- runs frontend import / canonicalize / legality / lower / estimate
- dumps IR documents
- writes JSON reports
- returns a structured result object for the CLI

**Step 2: Extend run contracts minimally**

If needed, add fields that let the manifest / run summary record:
- stage name
- updated artifact index entries
- failure reason or diagnostics

**Step 3: Run the focused workflow test**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py -v
```

Expected: workflow tests pass.

### Task 4: Wire the CLI command

**Files:**
- Modify: `src/llm_sched/cli/main.py`

**Step 1: Add the new command**

Add:

```python
@app.command("run-frontend-analysis")
def run_frontend_analysis(...):
    ...
```

Behavior:
- accepts `--run-root`
- validates that `manifest.json` exists
- invokes the workflow
- prints a short success/failure message
- exits non-zero on failure

**Step 2: Run the smoke tests again**

Run:

```powershell
python -m pytest tests/smoke/test_cli_help.py tests/smoke/test_cli_run_frontend_analysis.py -v
```

Expected: smoke tests pass.

### Task 5: Add summary/report regression coverage

**Files:**
- Create: `tests/unit/contracts/test_frontend_analysis_report.py`
- Modify: `src/llm_sched/pipeline/frontend_analysis.py`

**Step 1: Add regression tests**

Cover:
- legality report includes issue counts and raw issues
- pseudo/fallback summary includes:
  - `record_counts`
  - `tag_counts`
  - aggregate bytes/cycles

**Step 2: Run the focused tests**

Run:

```powershell
python -m pytest tests/unit/contracts/test_frontend_analysis_report.py tests/unit/pipeline/test_frontend_analysis_workflow.py -v
```

Expected: report and workflow coverage pass.

### Task 6: Docs and full verification

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/phase-a-foundation-handoff.md`

**Step 1: Update docs**

Document:
- the new `run-frontend-analysis` command
- emitted artifacts and report paths
- current scope limit: frontend + pseudo/fallback analysis, no schedule/tile planner yet

**Step 2: Run full verification**

Run:

```powershell
python -m pytest -v
git diff --check
```

Expected: full suite passes; no diff errors.

### Task 7: Real run smoke and commit

**Files:**
- No source changes required unless smoke reveals regressions

**Step 1: Run a real CLI smoke**

Run `init-run` followed by `run-frontend-analysis` on checked-in Gemma3 inputs and confirm:
- run status becomes `completed`
- manifest index contains new dumps/reports
- analysis summary matches current pseudo/fallback counts

**Step 2: Commit**

```powershell
git add docs/development/README.md docs/development/phase-a-foundation-handoff.md docs/plans/2026-03-07-frontend-analysis-cli-integration.md src/llm_sched/cli/main.py src/llm_sched/contracts/manifest.py src/llm_sched/contracts/run_summary.py src/llm_sched/pipeline/__init__.py src/llm_sched/pipeline/frontend_analysis.py tests/smoke/test_cli_help.py tests/smoke/test_cli_run_frontend_analysis.py tests/unit/contracts/test_frontend_analysis_report.py tests/unit/pipeline/test_frontend_analysis_workflow.py
git commit -m "feat: add frontend analysis cli workflow"
```
