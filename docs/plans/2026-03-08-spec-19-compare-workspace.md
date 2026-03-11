# SPEC-19 Compare Workspace Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the current two-run catalog compare tray into a stronger workspace compare surface centered on a pinned baseline run.

**Architecture:** Keep the catalog static and browser-only. Reuse the existing compare selection state, treat the first selected run as the baseline, and render a scenario-scoped compare workspace for all visible runs that share the baseline scenario. This adds a richer comparison surface without changing `VisualizationCatalogEntry` or introducing any service/backend flow.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript builders

---

### Task 1: Add failing tests for compare workspace shell

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that the generated catalog assets include:
- `catalog-compare-workspace`
- `catalog-compare-workspace-content`
- JavaScript helpers for workspace compare rendering

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because the current catalog only has a two-run compare tray.

**Step 3: Write minimal implementation**

Implement the smallest builder changes needed to expose the workspace compare shell and helpers.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/visualization/test_catalog_builder.py src/llm_sched/visualization/catalog_builder.py
git commit -m "feat: add compare workspace shell"
```

### Task 2: Implement baseline-pinned scenario compare workspace

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`
- Test: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing test**

Make the test check for:
- `buildWorkspaceCompareRows`
- `renderCompareWorkspace`
- `Workspace Compare`
- summary links back to selected workbench pages

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because those helpers do not exist yet.

**Step 3: Write minimal implementation**

Add:
- one workspace compare section below the compare tray
- baseline = first selected run
- candidate set = currently visible runs with the same scenario
- per-row delta / ratio / mismatch note / summary link

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: add scenario compare workspace"
```

### Task 3: Update docs and verify full suite

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Create: `docs/plans/2026-03-08-spec-19-compare-workspace.md`

**Step 1: Update docs**

Document the new stable behavior:
- the catalog now supports a baseline-pinned scenario compare workspace
- the first selected run acts as the baseline for workspace compare

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
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-e-visualization-workbench-handoff.md docs/plans/2026-03-08-spec-19-compare-workspace.md
git commit -m "docs: update spec 19 compare workspace checkpoint"
```
