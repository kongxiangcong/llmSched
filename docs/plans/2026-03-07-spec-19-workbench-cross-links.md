# SPEC-19 Workbench Cross Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add deeper descriptor/block/tensor hyperlinks inside the static visualization workbench without changing the visualization bundle contract.

**Architecture:** Keep the workbench as a static page driven only by `visualization_bundle.json`. Add panel-local search state and cross-panel link builders in generated JavaScript so coverage issues can jump to timeline block detail, timeline blocks can jump to coverage/graph filters, and KV formula entries can jump to timeline filters. This preserves the current static architecture and reuses existing identifiers already exposed by the bundle.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript builders

---

### Task 1: Add failing tests for workbench cross-link affordances

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing test**

Add assertions that the generated workbench assets include:
- a coverage search input
- URL-state support for `coverage_query`
- JavaScript helpers for panel-link construction and coverage issue filtering
- rendered cross-link targets for timeline detail, coverage issues, and KV formula entries

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because the current workbench does not yet expose cross-link helpers or coverage-query state.

**Step 3: Write minimal implementation**

Implement the smallest builder changes needed to support these links.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/visualization/test_workbench_builder.py src/llm_sched/visualization/workbench_builder.py
git commit -m "feat: add workbench cross panel links"
```

### Task 2: Implement workbench cross-panel hyperlinks

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Test: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing test**

Make the test check for:
- `buildPanelLink(...)`
- `filterCoverageIssues(...)`
- `coverage-search-input`
- `coverage_query`
- link generation in coverage/timeline/memory rendering paths

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because the builder does not yet generate those assets.

**Step 3: Write minimal implementation**

Add:
- `coverageQuery` to UI state
- URL hydration for `coverage_query`
- a generic panel-link builder
- coverage filtering
- timeline detail quick links into graph and coverage
- KV formula quick links into timeline filters

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: add workbench descriptor and tensor links"
```

### Task 3: Update docs and verify full suite

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Create: `docs/plans/2026-03-07-spec-19-workbench-cross-links.md`

**Step 1: Update docs**

Document the new stable behavior:
- coverage issues link into timeline block detail
- timeline blocks link into graph/coverage filters
- KV formulas link into timeline filtering

**Step 2: Run targeted verification**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
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
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-e-visualization-workbench-handoff.md docs/plans/2026-03-07-spec-19-workbench-cross-links.md
git commit -m "docs: update spec 19 workbench cross link checkpoint"
```
