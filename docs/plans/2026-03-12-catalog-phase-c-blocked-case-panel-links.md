# Catalog Phase C Blocked-Case Panel Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make blocked `Phase C` catalog rows open the most relevant packaged workbench panel by default instead of always landing on the generic workbench entry.

**Architecture:** Reuse the existing blocked-case table and existing workbench `?panel=` deep-link contract. Keep metadata unchanged, derive the suggested panel directly from `blocker_kind` during static HTML rendering, and limit the heuristic to a small mapping: planner-related blockers go to `memory`, downstream blockers go to `coverage`.

**Tech Stack:** Python, pytest, static HTML builder

---

### Task 1: Add failing rendering tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing test**

Assert that:
- planner-blocked rows render a workbench link with `?panel=memory`
- downstream-blocked rows render a workbench link with `?panel=coverage`
- missing-case rows still render no workbench link

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because blocked-case links still point at the bare workbench entry path.

### Task 2: Implement panel-link rendering

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Write minimal implementation**

Add a small helper that maps:
- `planner` and `planner_and_downstream` -> `memory`
- `downstream` -> `coverage`
- `missing_case` and `duplicate_case` -> no link

Use that helper to render the blocked-case workbench cell as `Open Memory` or `Open Coverage` with `?panel=<panel>` appended to the existing `workbench_entry_path`.

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

Document that blocked-case links now land on the suggested memory or coverage panel by default.

**Step 2: Run final verification**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
git diff --check
```

Expected:
- pytest: PASS
- `git diff --check`: no new format errors; existing CRLF warnings are acceptable if unchanged
