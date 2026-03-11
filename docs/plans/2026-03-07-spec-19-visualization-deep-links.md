# SPEC-19 Visualization Deep Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add static deep links from the cross-run catalog into focused workbench panels without changing the visualization bundle contract.

**Architecture:** Keep the workbench as a static `index.html + app.js + styles.css` surface. The catalog will generate panel-aware links using URL query parameters, and the workbench will parse those parameters to select the requested panel and seed relevant UI filters. This keeps `visualization_bundle.json` as the only data source and avoids introducing a service layer.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript builders

---

### Task 1: Add failing tests for panel-deep-link generation

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that:
- catalog group sections render panel-deep-link URLs for timeline, memory, and coverage
- workbench assets contain URL-state parsing helpers and panel activation from query params

**Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because the current static assets do not expose deep-link URLs or query-param handling.

**Step 3: Write minimal implementation**

Implement the smallest workbench/catalog builder changes needed to satisfy the new assertions.

**Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py
git commit -m "feat: add spec 19 visualization deep links"
```

### Task 2: Add workbench URL-state routing

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Test: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing test**

Add assertions for generated `app.js` that:
- parses `window.location.search`
- supports `panel`, `graph_query`, `timeline_query`, `timeline_stage`, `timeline_core`, and `detail_block`
- uses the requested panel as initial active panel

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because the workbench currently hard-codes `summary` as the active panel and ignores URL state.

**Step 3: Write minimal implementation**

Add URL-state parsing and initial state hydration in the generated JavaScript without changing the bundle schema.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: add workbench url state routing"
```

### Task 3: Add catalog panel-link shortcuts

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`
- Test: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions for:
- per-run quick links to `summary`, `timeline`, `memory`, and `coverage`
- timeline links using panel-aware URL parameters

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because the catalog currently only links to the workbench root page.

**Step 3: Write minimal implementation**

Emit quick-link chips in group cards and keep the table row entry link unchanged.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: add catalog panel shortcut links"
```

### Task 4: Update docs and verify full suite

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Create: `docs/plans/2026-03-07-spec-19-visualization-deep-links.md`

**Step 1: Update docs**

Document the new stable behavior:
- catalog group cards can jump directly to focused workbench panels
- workbench supports URL-state routing for panel selection and filter hydration

**Step 2: Run targeted verification**

Run:

```bash
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q
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
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-e-visualization-workbench-handoff.md docs/plans/2026-03-07-spec-19-visualization-deep-links.md
git commit -m "docs: update spec 19 deep link checkpoint"
```
