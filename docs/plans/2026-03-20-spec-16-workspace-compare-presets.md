# SPEC-16 Workspace Compare Presets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a small preset layer so catalog workspace compare can snap to common primary/secondary section pairings in one action.

**Architecture:** Keep compare payloads unchanged. Extend catalog workspace state with `workspace_detail_preset`, add a small preset-to-section mapping in the static builder, and preserve the active preset in focused workspace links and export metadata while continuing to render from the resolved section ids.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog coverage for workspace compare presets

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose `workspace_detail_preset`
- include helpers such as `currentWorkspaceDetailPreset` and `resolveWorkspaceDetailPreset`
- preserve preset metadata such as `focused_workspace_detail_preset`

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because workspace compare presets do not exist yet.

### Task 2: Implement the preset layer in catalog builder

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add minimal preset state plumbing**

Implement:

- URL serialization/hydration for `workspace_detail_preset`
- a small preset-to-section mapping
- a helper to resolve active preset ids into primary/secondary section ids

**Step 2: Preserve the preset in focused workspace output**

Update focused workspace rendering and export metadata so:

- preset labels are visible when active
- explicit section rendering uses the resolved preset pair

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

- `workspace_detail_preset`
- preset resolver helpers
- focused preset metadata strings

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because workflow outputs do not yet include preset support.

**Step 3: Re-run after implementation**

Once builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-workspace-compare-presets.md`

**Step 1: Update roadmap checkpoint**

Record:

- workspace compare preset state
- preset-to-section resolution
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
  - optional `workspace_detail_preset` state in catalog workspace
  - preset-to-section resolution for focused workspace compare
  - preset continuity in copied links, JSON export, and SVG snapshot metadata
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction above the current preset-backed focused workspace surface
