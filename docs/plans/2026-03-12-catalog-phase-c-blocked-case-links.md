# Catalog Phase C Blocked-Case Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add direct drill-down links from blocked `Phase C` catalog rows into the corresponding packaged workbench when a blocked case has a concrete run.

**Architecture:** Keep the current workspace-level `phase_c_blocked_cases` summary small and static. Extend each blocked-case record with an optional catalog-relative workbench link that is derived during `run-visualization-catalog`, then render that link inside the existing `Blocked Cases` table without changing `SPEC-18` bundle contracts.

**Tech Stack:** Python, Pydantic, pytest, static HTML builder

---

### Task 1: Add failing tests for blocked-case links

**Files:**
- Modify: `tests/unit/contracts/test_visualization_catalog.py`
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Add assertions that:
- blocked-case contract accepts an optional `workbench_entry_path`
- builder renders a clickable workbench link for blocked cases with a path
- workflow copies the matching run's workbench path into `phase_c_blocked_cases`
- CLI smoke output contains the blocked-case workbench link in `catalog/index.html`

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because blocked-case records do not yet carry or render workbench links.

### Task 2: Implement blocked-case link plumbing

**Files:**
- Modify: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Write minimal implementation**

Add an optional `workbench_entry_path` field to `VisualizationCatalogPhaseCBlockedCase`.

During `run_visualization_catalog(...)`, build a run-id to workbench-entry lookup from already-resolved catalog entries and attach the matching relative path to each blocked case when a run id exists.

Update the `Blocked Cases` table so rows with a `workbench_entry_path` render an `Open Workbench` link, while missing/duplicate rows keep a `-` placeholder.

**Step 2: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 3: Refresh docs and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`

**Step 1: Update docs**

Document that catalog blocked-case rows can now jump directly into packaged workbenches when a concrete run exists.

**Step 2: Run final verification**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
git diff --check
```

Expected:
- pytest: PASS
- `git diff --check`: no new format errors; existing CRLF warnings are acceptable if unchanged
