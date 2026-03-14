# SPEC-16 Workspace Sweep Summary Tags Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add compact sweep-layer summary tags to the catalog compare workspace table so users can tell whether a candidate has regressions, mixed layer outcomes, or no regressions before opening layer details.

**Architecture:** Keep the change inside the existing catalog static JS builder. Reuse the current `direction-tag` visual language with a small sweep-summary helper that inspects existing `layer_deltas`, without changing compare payload contracts or adding browser state.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock sweep summary tags with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- a dedicated workspace sweep summary tag helper in emitted `catalog/assets/app.js`
- the workspace compare table to call the helper directly
- emitted assets to include sweep-summary labels such as `candidate regressions`, `mixed`, and `none`

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because the `Sweep Layer Deltas` cell does not yet include a compact semantic summary tag.

### Task 2: Implement workspace sweep summary tags

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add a sweep summary helper**

Create a helper that derives:
- `is-negative` / `candidate regressions` when any layer delta regresses and no mixed handling is needed
- `is-neutral` / `mixed` when both regressing and non-regressing layer outcomes appear
- `is-neutral` / `none` when no candidate regression layers are present

Use only the existing `layer_deltas[*].delta_cycles` data already present in the compare surface.

**Step 2: Apply the helper to the workspace table**

Update `buildWorkspaceCompareRows` so the `Sweep Layer Deltas` cell renders the compact tag ahead of the existing sweep summary text, drilldown link, and layer rows.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-sweep-summary-tags.md`

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
git add docs/plans/2026-03-14-spec-16-workspace-sweep-summary-tags.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: tag workspace sweep summaries"
```
