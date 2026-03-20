# SPEC-16 Analysis Flow Workbench Bridge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Carry `workspace_analysis_flow` across catalog-to-workbench links and turn it into a first-class workbench sweep workflow surface.

**Architecture:** Reuse the existing catalog analysis-flow intent layer, add one workbench-side flow mapping for compare/layer defaults, and preserve the resulting flow state across URL hydration, sweep rendering, and export metadata without changing compare payload contracts.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing tests for the cross-surface analysis-flow bridge

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write failing catalog assertions**

Add assertions proving focused workspace compare paths can emit workbench links that preserve analysis-flow state.

**Step 2: Write failing workbench assertions**

Add assertions proving generated workbench assets:

- hydrate and serialize `analysis_flow`
- render an `Analysis Workflow` summary
- preserve structured analysis-flow export metadata

**Step 3: Run the focused unit tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because workbench does not yet speak analysis-flow state.

### Task 2: Implement catalog-to-workbench analysis-flow continuity

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Extend workbench link helpers**

Thread active analysis-flow state into the focused workspace compare links that open workbench sweep/summary surfaces.

**Step 2: Keep the link scope narrow**

Only attach analysis-flow state where the user is already in a focused workspace compare workflow, so generic catalog browsing behavior stays unchanged.

**Step 3: Run catalog/workbench unit tests**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
```

Expected: still FAIL until workbench support lands.

### Task 3: Implement workbench analysis-flow support

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add workbench URL state**

Hydrate and serialize `analysis_flow`.

**Step 2: Resolve flow defaults**

Map supported analysis flows onto stable compare-focus and layer-diff defaults.

**Step 3: Render analyst-facing workbench summary**

Expose one compact `Analysis Workflow` block in the sweep panel describing the active flow and its resolved focus choices.

**Step 4: Preserve export continuity**

Add one human-readable header row and one structured metadata field for the resolved workbench analysis flow.

**Step 5: Re-run focused unit tests**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-20
- Implemented:
  - focused catalog workbench links now preserve `analysis_flow` in sweep and selected-panel deep links
  - workbench sweep now renders an `Analysis Workflow` summary block based on resolved flow defaults
  - workbench export metadata now preserves `focused_analysis_flow` and `focused_analysis_flow_summary`
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q` -> `9 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `19 passed`
- Next:
  - richer compare interaction above the current analysis-flow-backed catalog/workbench workflow surface

### Task 4: Preserve the bridge in pipeline and smoke outputs

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_workbench_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_workbench.py`

**Step 1: Add failing workflow/smoke assertions**

Assert generated assets preserve:

- analysis-flow query params on focused workbench links
- workbench analysis-flow summary strings
- workbench analysis-flow export metadata keys

**Step 2: Re-run the focused workflow/smoke set**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS after implementation.

### Task 5: Record the slice and verify end-to-end

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-analysis-flow-workbench-bridge.md`

**Step 1: Update roadmap checkpoint**

Record:

- catalog-to-workbench analysis-flow deep links
- workbench analysis-workflow summary
- export continuity for workbench analysis-flow state

**Step 2: Update plan completion notes**

Add:

- verification commands run
- test counts
- next remaining `SPEC-16` gap after this slice

**Step 3: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS.
