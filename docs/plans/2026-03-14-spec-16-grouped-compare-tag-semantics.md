# SPEC-16 Grouped Compare Tag Semantics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Normalize grouped compare direction tags around shared positive/negative/neutral semantics so catalog and workbench communicate the same compare meaning with the same visual language.

**Architecture:** Keep all logic inside the existing static JS/CSS builders. Preserve current direction-tag wording, but remap badge classes from directional `up/down` styling to semantic `positive/negative/neutral` styling so equivalent outcomes such as `candidate faster` and `pressure down` share the same positive treatment.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

## Execution Policy

The user already approved continuing in the current session, so this plan is being implemented directly here.

---

### Task 1: Lock semantic tag behavior with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- semantic tag classes:
  - `direction-tag is-positive`
  - `direction-tag is-negative`
  - `direction-tag is-neutral`
- catalog/workbench JS to stop relying on `is-up` / `is-down` for direction-tag rendering
- existing direction-tag wording to remain present

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "grouped or sweep"
```

Expected: FAIL because direction tags still use `is-up` / `is-down` classes.

### Task 2: Implement semantic tag styling

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Remap the tag helper**

Use:
- `is-positive` for beneficial outcomes like `candidate faster` and `pressure down`
- `is-negative` for harmful outcomes like `candidate slower` and `pressure up`
- `is-neutral` for steady or ambiguous shape-only wording

**Step 2: Align styles**

Replace the old directional CSS selectors with semantic ones in both builders while keeping the same overall visual tone.

### Task 3: Verify and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-grouped-compare-tag-semantics.md`

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
git add docs/plans/2026-03-14-spec-16-grouped-compare-tag-semantics.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: unify compare tag semantics"
```
