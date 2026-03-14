# SPEC-16 Workspace Ratio Summary Tags Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add semantic compare summary tags to the catalog workspace `Primary Ratio` column so users can read direction and magnitude in one scan line.

**Architecture:** Keep the change inside the existing catalog static JS builder. Reuse the current workspace compare semantic mapping for positive/negative/neutral outcomes, but emit a dedicated ratio-column helper so the ratio cell can evolve independently without changing compare payload contracts.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock ratio summary tags with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- a dedicated ratio summary tag helper in emitted `catalog/assets/app.js`
- the workspace compare table to call the ratio helper directly
- ratio-column semantic tag markers to be visible in emitted assets

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because the `Primary Ratio` column does not yet include a dedicated semantic summary tag.

### Task 2: Implement ratio summary tags

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add a ratio summary helper**

Create a helper that reuses the current workspace compare semantic mapping and emits:
- `is-positive` / `improved`
- `is-negative` / `regressed`
- `is-neutral` / `steady`

Mark the rendered tag as ratio-specific so tests and future styling can target the ratio column separately.

**Step 2: Apply the helper to the `Primary Ratio` column**

Update `buildWorkspaceCompareRows` so the ratio cell renders the dedicated semantic tag alongside the existing ratio value, while preserving the current `n/a` fallback behavior.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-ratio-summary-tags.md`

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
git add docs/plans/2026-03-14-spec-16-workspace-ratio-summary-tags.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: tag workspace compare ratios"
```
