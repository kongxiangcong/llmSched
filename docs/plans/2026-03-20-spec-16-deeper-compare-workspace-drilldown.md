# SPEC-16 Deeper Compare Workspace Drill-Down Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a persistent focused workspace candidate state so catalog workspace compare can render a dedicated deeper drill-down view and preserve that focus in links and exports.

**Architecture:** Keep all compare math and contracts unchanged. Extend the catalog workspace state model with a focused candidate id, reuse the existing compare-summary and layer-diff helpers to render a dedicated focused drill-down card, and thread the same state through workspace URL serialization, JSON export, and SVG snapshot metadata.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add focused workspace candidate coverage to catalog builder tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing catalog test**

Add assertions proving generated catalog assets:

- expose `workspace_candidate` in catalog URL state serialization and hydration
- include focused workspace helpers such as `resolveFocusedWorkspaceCandidate` and `renderFocusedWorkspaceDrilldown`
- preserve focused workspace candidate in workspace export payloads and snapshot metadata

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because the catalog app does not yet model a focused workspace candidate.

**Step 3: Write the minimal catalog assertions**

Cover:

- URL state persistence for `workspace_candidate`
- focused drill-down card rendering hook
- export payload fields such as `focused_workspace_candidate`
- snapshot metadata/header rows containing the focused candidate

**Step 4: Run test to verify it still fails for the expected missing implementation**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL on the new focused-workspace assertions.

### Task 2: Implement focused workspace candidate state in catalog rendering

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Implement the minimal state plumbing**

Add catalog JS support for:

- serializing and hydrating `workspace_candidate`
- resolving the focused candidate from current workspace state with graceful fallback
- rendering row-level focus actions and a dedicated focused drill-down card

**Step 2: Keep existing compare focus semantics intact**

Reuse current helpers for:

- grouped compare sections
- pressure compare sections
- estimated/fitted layer sections
- workbench deep-link construction

Do not add new compare-summary payload fields.

**Step 3: Run the focused catalog test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 3: Preserve focused workspace candidate in workflow outputs

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Write the failing workflow/smoke assertions**

Add assertions proving workflow-generated catalog assets now include focused workspace candidate support in emitted app code and snapshot/export paths.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because workflow outputs do not yet contain the focused workspace drill-down support.

**Step 3: Re-run after implementation**

Once the catalog builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-deeper-compare-workspace-drilldown.md`

**Step 1: Update roadmap checkpoint**

Record:

- focused workspace candidate state
- dedicated focused workspace compare drill-down card
- workspace link/JSON/SVG export continuity for the focused candidate

**Step 2: Update plan completion notes**

Add a short completion note with:

- verification commands run
- test counts
- the next remaining `SPEC-16` or `SPEC-19` gap after this slice

### Task 5: Run focused verification and summarize outcome

**Files:**
- No file changes required

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
python -m pytest tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

**Step 2: Run the broader catalog/workbench safety net if needed**

If the catalog changes touch shared compare rendering helpers, also run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-20
- Implemented:
  - persistent `workspace_candidate` catalog workspace state
  - row-level `Focus In Workspace` actions
  - dedicated `Focused Workspace Compare Drilldown` card
  - focused workspace candidate continuity in copied links, JSON export, and SVG snapshot metadata
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction inside the now-focused workspace/catalog drill-down surface
