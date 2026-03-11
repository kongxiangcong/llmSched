# SPEC-19 Catalog Compare Tray Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a static cross-run compare tray to the visualization catalog so users can select runs and inspect a lightweight delta summary without leaving the catalog page.

**Architecture:** Keep the catalog fully static and browser-side. Reuse `VisualizationCatalogEntry` as the only data source, add client-side selection state, and render a compare tray that summarizes baseline/candidate metadata, primary metric delta, and comparison links back into workbench summary pages. This avoids changing pipeline contracts or introducing a new service layer.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript builders

---

### Task 1: Add failing tests for compare tray controls

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that the generated catalog assets include:
- `catalog-compare-tray`
- `compare-toggle`
- JavaScript helpers for compare selection and summary rendering

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because the current catalog has no compare tray or compare-state helpers.

**Step 3: Write minimal implementation**

Implement the smallest builder changes needed to expose compare controls and tray rendering.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/visualization/test_catalog_builder.py src/llm_sched/visualization/catalog_builder.py
git commit -m "feat: add catalog compare tray controls"
```

### Task 2: Implement compare selection and delta summary

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`
- Test: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing test**

Make the test check for:
- `toggleCompareSelection`
- `renderCompareTray`
- `buildCompareSummary`
- compare links back to selected workbench summary pages

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because the catalog does not yet support selection or compare summaries.

**Step 3: Write minimal implementation**

Add:
- compare toggles in table rows and grouped run cards
- two-entry selection limit with deterministic replacement
- compare tray summary for metric delta, ratio, and mismatch notes
- baseline/candidate summary links

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: add catalog compare summary"
```

### Task 3: Update docs and verify full suite

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Create: `docs/plans/2026-03-08-spec-19-catalog-compare-tray.md`

**Step 1: Update docs**

Document the new stable behavior:
- catalog supports client-side multi-run selection
- catalog compare tray summarizes cross-run deltas and links back to workbench summary pages

**Step 2: Run targeted verification**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS

**Step 3: Run full verification**

Run:

```bash
python -m pytest -q
git diff --check
```

Expected:
- all tests pass
- no diff errors

**Step 4: Commit**

```bash
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-e-visualization-workbench-handoff.md docs/plans/2026-03-08-spec-19-catalog-compare-tray.md
git commit -m "docs: update spec 19 catalog compare checkpoint"
```
