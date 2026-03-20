# SPEC-16 Workspace Analysis Flows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a named analysis-flow layer above workspace compare presets so common catalog compare workflows have stable, user-facing entry points.

**Architecture:** Keep compare payloads and preset definitions unchanged. Extend catalog workspace state with `workspace_analysis_flow`, add a small flow-to-preset resolver, and preserve the active flow in focused workspace links and export metadata while rendering through the already-existing preset layer.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog coverage for analysis flows

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose `workspace_analysis_flow`
- include helpers such as `currentWorkspaceAnalysisFlow` and `resolveWorkspaceAnalysisFlow`
- preserve active flow metadata such as `focused_workspace_analysis_flow`

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because analysis-flow state does not exist yet.

### Task 2: Implement the analysis-flow layer in catalog builder

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add minimal state plumbing**

Implement:

- URL serialization/hydration for `workspace_analysis_flow`
- a small flow-to-preset mapping
- active-flow labels in focused workspace UI and export metadata

**Step 2: Reuse the preset layer**

When an analysis flow is active:

- resolve it to the existing preset ids
- let preset-based section rendering continue unchanged

**Step 3: Run the focused catalog test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 3: Preserve the new state in workflow and smoke outputs

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Write the failing assertions**

Add assertions proving generated outputs include:

- `workspace_analysis_flow`
- analysis-flow resolver helpers
- focused metadata strings for the active flow

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because generated outputs do not yet include analysis-flow support.

**Step 3: Re-run after implementation**

Once builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-workspace-analysis-flows.md`

**Step 1: Update roadmap checkpoint**

Record:

- analysis-flow state
- flow-to-preset resolution
- continued link/export continuity

**Step 2: Update plan completion notes**

Add:

- verification commands run
- test counts
- the next remaining `SPEC-16` gap after this slice

### Task 5: Run focused verification

**Files:**
- No file changes required

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-20
- Implemented:
  - optional `workspace_analysis_flow` state in catalog workspace
  - flow-to-preset resolution above the existing preset layer
  - analysis-flow continuity in focused workspace links, JSON export, and SVG snapshot metadata
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction above the current analysis-flow-backed workspace surface
