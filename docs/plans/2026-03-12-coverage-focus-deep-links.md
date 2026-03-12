# Coverage Focus Deep Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add structured `coverage_focus` deep links so `descriptor_generation` Phase C blocked cases can open the workbench coverage panel at the packed-descriptor section instead of landing on a generic coverage view.

**Architecture:** Reuse the existing `downstream_missing_consumers` metadata in catalog blocked-case records and map `descriptor_generation` to a new `coverage_focus=packed-descriptor` URL parameter. Extend the static workbench app to hydrate that focus state, highlight the relevant coverage cards, and preserve the focus in copied/current-view URLs and catalog-return links.

**Tech Stack:** Python, Pydantic contracts, static HTML/JS builders, pytest

---

### Task 1: Lock the new behavior with failing tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing test**

- Add a catalog builder expectation that a blocked case with `downstream_missing_consumers=["descriptor_generation"]` renders a coverage link with `coverage_focus=packed-descriptor`.
- Add a workbench builder expectation that `coverage_focus` is serialized/hydrated in the static app and that coverage cards expose packed-descriptor focus hooks.
- Add a CLI catalog smoke expectation that the generated HTML carries the same focus parameter and hydration data attributes.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because catalog links do not yet emit `coverage_focus`, and workbench assets do not yet hydrate or render packed-descriptor focus hooks.

### Task 2: Implement minimal catalog deep-link plumbing

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Write the minimal implementation**

- Add a helper that maps `descriptor_generation` blocked cases to `coverage_focus="packed-descriptor"`.
- Extend blocked-case href building and JS hydration data attributes to include `coverage_focus` when present.

**Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: Catalog tests pass while workbench focus tests still fail until the workbench builder is updated.

### Task 3: Implement minimal workbench coverage focus behavior

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`

**Step 1: Write the minimal implementation**

- Add `coverageFocus` to workbench URL state hydration/serialization.
- Mark the packed-descriptor coverage cards with a shared focus target.
- Highlight those cards when `coverage_focus=packed-descriptor` is active and keep the parameter in current-view links.

**Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS with `coverage_focus` preserved in static app output and packed-descriptor focus hooks present.

### Task 4: Verify the full slice and document it

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`

**Step 1: Update docs**

- Note that descriptor-generation blocked cases now deep-link to the packed-descriptor coverage section via structured focus metadata.

**Step 2: Run final verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
git diff --check
```

Expected: PASS, with only pre-existing LF/CRLF warnings from `git diff --check`.
