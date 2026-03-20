# SPEC-16 Workspace Row Section Actions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add direct row-to-section actions in the catalog workspace table so users can focus a candidate and the relevant compare section in one step.

**Architecture:** Keep compare payloads unchanged. Reuse the existing `workspace_candidate` and `workspace_detail_focus` state by extending workspace row content helpers to emit section-specific focus links from the overview table, then preserve the same state in focused workspace links and exports.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog coverage for row section actions

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose a helper such as `buildWorkspaceRowSectionFocusLink`
- include row-level `Focus Compare Section` actions in workspace summary cells
- preserve the same `workspace_candidate` plus `workspace_detail_focus` routing primitive

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because row-level section-targeted actions do not exist yet.

### Task 2: Implement row-to-section actions in catalog builder

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add a minimal row-link helper**

Implement a helper that builds a workspace-local link for:

- one candidate entry id
- one target detail section id

**Step 2: Thread the helper through row content**

Update workspace row content helpers so:

- primary delta content links to `summary`
- primary ratio content links to `summary`
- shared metric content links to `grouped-metrics`
- sweep layer content links to `estimated-layer`

**Step 3: Run the focused catalog test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 3: Preserve row section actions in workflow and smoke outputs

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Write the failing assertions**

Add assertions proving workflow-generated assets now include:

- the row section focus helper
- row-level `Focus Compare Section` actions

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because generated outputs do not yet contain the row section actions.

**Step 3: Re-run after implementation**

Once builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-workspace-row-section-actions.md`

**Step 1: Update roadmap checkpoint**

Record:

- row-level section-targeted actions
- one-step candidate-plus-section focus links
- continued workspace export continuity

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
  - row-level candidate-plus-section focus links in workspace summary cells
  - direct routing from overview table cells into focused workspace compare sections
  - continued reuse of the existing `workspace_candidate` and `workspace_detail_focus` state
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction above the current row-plus-card focused workspace surface
