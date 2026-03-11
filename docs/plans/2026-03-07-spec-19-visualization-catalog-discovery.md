# SPEC-19 Visualization Catalog Discovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the static visualization catalog so it can discover packaged runs from a sweep workspace or a generic workspace root, while preserving explicit `run_root` inputs.

**Architecture:** Keep the existing catalog artifact and builder unchanged. Add discovery logic in the catalog workflow so it can gather packaged run roots from three sources: explicit run roots, `sweep_root/reports/sweep_delta_report.json`, and a workspace directory scan. The CLI will expose `--run-root`, `--sweep-root`, and `--workspace-root`, with deterministic deduplication before packaging.

**Tech Stack:** Python 3.14, existing catalog workflow/CLI pattern, Pydantic contracts already in repo, pytest unit/smoke tests.

---

### Task 1: Add Discovery Tests For Workflow And CLI

**Files:**
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Add tests covering:
- discovery from `sweep_root` using `reports/sweep_delta_report.json`
- discovery from `workspace_root` by scanning packaged child runs
- deduplication when the same run is present in explicit and discovered sources
- clean failure when no catalog sources are provided

**Step 2: Run tests to verify they fail**

Run:
- `python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q`

Expected: FAIL because discovery inputs are not yet supported.

### Task 2: Implement Discovery In Workflow And CLI

**Files:**
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Modify: `src/llm_sched/cli/main.py`

**Step 1: Add minimal discovery helpers**

Implement:
- sweep-root discovery from `SweepDeltaReport.run_records`
- workspace-root discovery from packaged child directories
- deterministic deduplication of discovered run roots

Do not change the catalog contract or builder in this batch.

**Step 2: Extend workflow signature**

Update:
- `run_visualization_catalog(catalog_root, run_roots=None, sweep_root=None, workspace_root=None)`

Rules:
- explicit `run_roots` remain supported
- discovered roots are appended and deduplicated
- fail clearly when the final run-root set is empty

**Step 3: Extend CLI**

Update:
- `llm-sched run-visualization-catalog --catalog-root ... [--run-root ...] [--sweep-root ...] [--workspace-root ...]`

Keep the user-facing output short and deterministic.

**Step 4: Run focused verification**

Run:
- `python -m pytest tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q`

Expected: PASS

### Task 3: Docs, Full Verification, Commit

**Files:**
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- new discovery sources
- current scan boundary for workspace discovery
- unchanged static catalog contract

**Step 2: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 3: Commit**

```bash
git add src/llm_sched/pipeline/visualization_catalog.py src/llm_sched/pipeline/__init__.py src/llm_sched/cli/main.py docs/development/phase-e-visualization-workbench-handoff.md docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-07-spec-19-visualization-catalog-discovery.md tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py
git commit -m "feat: add spec 19 visualization catalog discovery"
```
