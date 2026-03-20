# SPEC-16 Workspace Row Preset Actions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let catalog workspace row cells open common preset-backed compare workflows in one step.

**Architecture:** Keep compare payloads unchanged. Reuse the existing `workspace_detail_preset` state by adding a small row-level preset-link helper and threading it through the row content helpers that already render shared-metric and sweep-layer summaries.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog coverage for row preset actions

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose a helper such as `buildWorkspaceRowPresetLink`
- include row-level preset actions for common workflows
- preserve routing through `workspace_detail_preset`

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because row-level preset actions do not exist yet.

### Task 2: Implement row-level preset actions in catalog builder

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add a minimal row-preset helper**

Implement a helper that builds a workspace-local link for:

- one candidate entry id
- one preset id

**Step 2: Thread the helper through row content**

Update row content so:

- shared metric content can jump to `grouped-vs-estimated-layer`
- sweep layer content can jump to `summary-vs-estimated-layer`

**Step 3: Run the focused catalog test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

### Task 3: Preserve row preset actions in workflow and smoke outputs

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Write the failing assertions**

Add assertions proving generated outputs include:

- the row preset helper
- row-level preset links for the chosen workflows

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because generated outputs do not yet contain the row preset links.

**Step 3: Re-run after implementation**

Once builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-workspace-row-preset-actions.md`

**Step 1: Update roadmap checkpoint**

Record:

- row-level preset actions
- one-step row-to-workflow shortcuts
- continued preset continuity

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
  - row-level preset links in workspace summary cells
  - direct row-to-preset workflow shortcuts for shared-metric and sweep-layer analysis
  - continued reuse of the existing `workspace_detail_preset` state
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction above the current row-plus-preset workspace surface
