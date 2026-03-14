# SPEC-16 Direction Tag Markup Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce grouped compare tag template duplication in catalog and workbench behind a shared direction-tag markup helper.

**Architecture:** Keep the change inside the existing static JS builders. Add a tiny `buildDirectionTagMarkup(semanticClass, label)` helper in both generated apps and reuse it from grouped compare tag rendering, while preserving all current labels and semantic classes.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the markup helper with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- emitted `app.js` to expose `function buildDirectionTagMarkup`
- grouped compare tag rendering to call `buildDirectionTagMarkup`

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "build_visualization_catalog_generates_static_index_assets or build_visualization_workbench_generates_static_assets_with_sweep_panel"
```

Expected: FAIL because grouped compare tags still inline the `<span class="direction-tag ...">...</span>` markup.

### Task 2: Implement the markup helper

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add `buildDirectionTagMarkup`**

Create a helper that returns:

```javascript
`<span class="direction-tag ${semanticClass}">${label}</span>`
```

**Step 2: Reuse the helper**

Update grouped compare tag rendering to call the helper for:
- `steady`
- `candidate faster/slower`
- `pressure up/down`
- `schedule shifted up/down`
- `shifted up/down`

Keep scalar-row tags and workspace summary tags unchanged for this slice.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-direction-tag-markup-helper.md`

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
git add docs/plans/2026-03-14-spec-16-direction-tag-markup-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "refactor: share direction tag markup helper"
```
