# SPEC-16 Workspace Compare Summary Tags Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add semantic compare summary tags to the catalog compare workspace table so users can scan candidate rows without opening details.

**Architecture:** Keep the change inside the existing catalog static JS builder. Reuse the current row-level semantic tag helper to render compact positive/negative/neutral summaries in the compare workspace table, without changing any compare contracts or adding browser state.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock workspace summary tags with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- a dedicated workspace compare summary tag helper in emitted `catalog/assets/app.js`
- semantic tag literals for workspace-row summaries, including `improved`, `regressed`, and `steady`
- workspace compare rows to call the helper directly

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because compare workspace rows do not yet include compact semantic summary tags.

### Task 2: Implement workspace summary tags

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add a compact workspace summary helper**

Create a helper that maps the baseline-versus-candidate primary metric delta to:
- `is-positive` / `improved`
- `is-negative` / `regressed`
- `is-neutral` / `steady`

Reuse the current metric-name heuristic used for scalar compare rows so throughput-style metrics and latency-style metrics share semantics.

**Step 2: Apply the helper to workspace compare rows**

Update `buildWorkspaceCompareRows` to prepend the summary tag in the row overview cells while keeping current delta, ratio, shared metric rows, and links intact.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-compare-summary-tags.md`

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
git diff --check
```

Expected: PASS with no diff errors.

**Step 2: Commit**

Run:

```powershell
git add docs/plans/2026-03-14-spec-16-workspace-compare-summary-tags.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: tag workspace compare summaries"
```
