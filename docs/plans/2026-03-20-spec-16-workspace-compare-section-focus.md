# SPEC-16 Workspace Compare Section Focus Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a persistent focused compare-section state to the catalog workspace so users can deep-link, export, and inspect one specific compare section inside the focused workspace drill-down card.

**Architecture:** Keep compare payloads unchanged. Extend catalog workspace URL/state handling with `workspace_detail_focus`, add section-link helpers around the existing grouped/pressure/layer drill-down content, and preserve the selected section in focused workspace export metadata and snapshot titles.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing coverage for focused workspace section state

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing catalog assertions**

Add assertions proving generated catalog assets:

- expose `workspace_detail_focus` in catalog state serialization
- include focused workspace section helpers such as `currentWorkspaceDetailFocus`, `buildWorkspaceDetailFocusLink`, and `orderWorkspaceDrilldownSections`
- preserve the focused workspace detail section in export payloads and snapshot metadata

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because the focused workspace detail section state does not exist yet.

### Task 2: Implement focused workspace section interaction in catalog builder

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Implement the minimal state plumbing**

Add support for:

- `workspace_detail_focus` URL serialization/hydration
- a small fixed detail-section label map
- row and focused-card links that retarget the current focused workspace section

**Step 2: Reuse existing compare content**

Keep rendering based on the existing helpers:

- `buildMatchedCompareSummaryRows`
- `renderPressureCompareSummary`
- `renderWorkspaceLayerDrilldownRows`

Only add ordering, labels, and stable focus state around them.

**Step 3: Run the focused catalog test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 3: Preserve focused workspace section in workflow and smoke outputs

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Write the failing workflow/smoke assertions**

Add assertions proving workflow-generated catalog assets now include:

- `workspace_detail_focus`
- focused section helper functions
- focused section metadata/export strings

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because workflow outputs do not yet contain the focused section support.

**Step 3: Re-run after implementation**

Once the builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-workspace-compare-section-focus.md`

**Step 1: Update roadmap checkpoint**

Record:

- focused workspace detail-section state
- focused compare section links/actions
- workspace export continuity for the active detail section

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
  - persistent `workspace_detail_focus` catalog workspace state
  - focused compare-section links inside the focused workspace drill-down card
  - focused workspace detail continuity in copied links, JSON export, and SVG snapshot metadata
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction above the current candidate-plus-section focused workspace surface
