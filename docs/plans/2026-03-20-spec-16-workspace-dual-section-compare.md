# SPEC-16 Workspace Dual-Section Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let the focused catalog workspace drill-down preserve and render one optional secondary compare section for the same candidate pair.

**Architecture:** Keep compare payloads unchanged. Extend catalog workspace state with `workspace_secondary_detail_focus`, reuse the existing section helpers to render both the primary and optional secondary sections, and preserve the same pair of section ids in link/export metadata.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog coverage for secondary section state

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose `workspace_secondary_detail_focus`
- include helpers such as `currentWorkspaceSecondaryDetailFocus` and `currentWorkspaceSecondaryDetailFocusLabel`
- preserve the secondary section in focused workspace metadata/export output

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because secondary section state does not exist yet.

### Task 2: Implement dual-section focused workspace rendering

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add minimal secondary section state plumbing**

Implement:

- URL serialization/hydration for `workspace_secondary_detail_focus`
- label helpers for the secondary section
- metadata continuity in focused workspace export output

**Step 2: Reuse the existing section content**

Update focused workspace rendering so:

- the primary focused section still renders first
- the optional secondary section renders immediately after it when distinct
- duplicate primary/secondary ids collapse to one rendered section

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

- `workspace_secondary_detail_focus`
- the secondary section helpers
- focused metadata strings for the secondary section

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because workflow outputs do not yet include secondary section support.

**Step 3: Re-run after implementation**

Once builder changes land, rerun:

```powershell
python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 4: Record the slice in roadmap and plan notes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\spec16-compare-modes\docs\plans\2026-03-20-spec-16-workspace-dual-section-compare.md`

**Step 1: Update roadmap checkpoint**

Record:

- optional secondary workspace detail section
- focused workspace dual-section rendering
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
  - optional `workspace_secondary_detail_focus` state in catalog workspace
  - focused workspace drill-down rendering for primary plus optional secondary compare sections
  - secondary section continuity in copied links, JSON export, and SVG snapshot metadata
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - richer compare interaction above the current dual-section focused workspace surface
