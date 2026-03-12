# Catalog Phase C Blocked-Case Catalog Return Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make blocked `Phase C` catalog links preserve the current catalog context through `catalog_return`, matching the rest of the `SPEC-19` catalog drill-down flow.

**Architecture:** Keep blocked-case rows server-rendered, but add lightweight `data-workbench-path` and `data-workbench-panel` attributes so the existing catalog JS can hydrate their hrefs with the current `catalog_return`. Reuse the current `buildCatalogReturnUrl()` logic and refresh those links inside the existing `bindCatalogFilters()` refresh path.

**Tech Stack:** Python, pytest, static HTML builder, browser-side JavaScript

---

### Task 1: Add failing tests for runtime link hydration

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Assert that:
- blocked-case workbench links render with a dedicated CSS class plus `data-workbench-path` and `data-workbench-panel`
- `catalog/assets/app.js` contains a helper that refreshes blocked-case links using `catalog_return`

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because blocked-case links are still emitted as static hrefs without runtime hydration hooks.

### Task 2: Implement runtime hydration

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Write minimal implementation**

Render blocked-case workbench links with:
- a static fallback `href` containing `?panel=<panel>`
- `class="blocked-case-workbench-link"`
- `data-workbench-path="..."`
- `data-workbench-panel="..."`

Add a small JS helper that walks `.blocked-case-workbench-link` anchors and rewrites each href to include:
- `panel=<panel>`
- `catalog_return=<current serialized catalog URL>`

Call that helper from the existing `refresh()` path in `bindCatalogFilters()`.

**Step 2: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 3: Refresh docs and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`

**Step 1: Update docs**

Document that blocked-case panel links now preserve catalog context through the same `catalog_return` loop as the other catalog drill-down paths.

**Step 2: Run final verification**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
git diff --check
```

Expected:
- pytest: PASS
- `git diff --check`: no new format errors; existing CRLF warnings are acceptable if unchanged
