# SPEC-19 Compare Modes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add richer static compare modes to the visualization catalog through baseline/candidate role swap and compare scope switching.

**Architecture:** Extend the existing catalog-only browser state in `catalog_builder.py` without changing pipeline contracts or catalog manifests. Keep all behavior inside static HTML/JS generation so compare-mode logic stays decoupled from artifact schemas.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript generation

---

### Task 1: Add failing tests for compare-mode controls

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- `catalog-compare-scope-filter` in generated `index.html`
- `swap-compare-order-button` in generated `index.html`
- `function swapCompareSelectionOrder` in generated `assets/app.js`
- `function buildWorkspaceCandidateSet` in generated `assets/app.js`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py -q`
Expected: FAIL because the compare-mode controls and helper functions do not exist yet.

### Task 2: Implement minimal static compare-mode behavior

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Write minimal implementation**

Update the static catalog builder to:
- render compare workspace controls with a scope selector and swap button
- support swapping baseline/candidate order inside the current two-run selection
- support candidate-set selection based on `same-scenario` or `all-visible`
- keep current compare tray and existing links working

**Step 2: Run targeted test to verify it passes**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py -q`
Expected: PASS

### Task 3: Update docs and verify the batch

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-e-visualization-workbench-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Step 1: Document the new compare-mode capability**

Add concise notes that catalog compare now supports:
- baseline/candidate role swap
- compare scope switching for same-scenario versus all-visible runs

**Step 2: Run verification**

Run: `python -m pytest -q`
Expected: PASS

Run: `git diff --check`
Expected: no diff errors

**Step 3: Commit**

Run:
```bash
git add docs/plans/2026-03-08-spec-19-compare-modes.md tests/unit/visualization/test_catalog_builder.py src/llm_sched/visualization/catalog_builder.py docs/development/phase-e-visualization-workbench-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md
git commit -m "feat: add spec 19 compare modes"
```
