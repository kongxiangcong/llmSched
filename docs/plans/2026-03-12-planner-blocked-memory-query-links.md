# Planner Blocked Memory Query Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make planner-blocked `Phase C` catalog links deep-link into the workbench memory panel with a prefilled region query when the blocked gap identifies a specific region.

**Architecture:** Add a minimal `memory_query` URL state to the static workbench, limited to filtering memory-panel region summaries by text. Extend blocked-case catalog links so planner-side blockers parse a region name from known gap strings such as `overflow region: ping`, emit that query in the fallback href and data attributes, and let the existing blocked-case link hydration preserve it alongside `catalog_return`.

**Tech Stack:** Python, pytest, static HTML builder, browser-side JavaScript

---

### Task 1: Add failing tests

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/smoke/test_cli_run_visualization_workbench.py`
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Assert that:
- workbench index now exposes `memory-search-input`
- workbench app JS includes `memory_query` URL state
- planner blocked-case links render `memory_query=ping` when the remaining gap includes `overflow region: ping`
- blocked-case hydration carries the same query through runtime link rewriting

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/smoke/test_cli_run_visualization_workbench.py tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because neither the workbench nor the blocked-case links currently support `memory_query`.

### Task 2: Implement minimal memory-query support

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Write minimal implementation**

In the workbench:
- add `memory_query` to URL hydration and UI state serialization
- render a `Memory Search` input in the memory panel
- filter memory-panel region/backing-store/memory-class rows by that query

In the catalog:
- parse planner gap strings for `overflow region: <name>`
- append `memory_query=<name>` to planner blocked-case memory links when found
- carry that query through blocked-case runtime link hydration together with `catalog_return`

**Step 2: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/smoke/test_cli_run_visualization_workbench.py tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 3: Refresh docs and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`

**Step 1: Update docs**

Document that planner-blocked catalog links now deep-link into memory inspection with an inferred region query when possible.

**Step 2: Run final verification**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
git diff --check
```

Expected:
- pytest: PASS
- `git diff --check`: no new format errors; existing CRLF warnings are acceptable if unchanged
