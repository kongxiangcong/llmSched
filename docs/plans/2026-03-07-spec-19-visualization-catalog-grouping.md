# SPEC-19 Visualization Catalog Grouping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the static visualization catalog with cross-run grouping and navigation so engineers can scan a workspace-sized run set faster without leaving the static UI model.

**Architecture:** Keep the existing catalog workflow, CLI, and artifact contract stable. Only harden the generated static catalog page by adding client-side search, scenario-group navigation, and grouped run sections derived from the existing catalog entries.

**Tech Stack:** Python 3.14, existing static catalog builder, HTML/CSS/JavaScript, pytest unit tests.

---

### Task 1: Add Grouping And Navigation Tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing tests**

Extend catalog builder tests to cover:
- search input in generated HTML
- scenario group navigation shell in generated HTML
- grouped section container in generated HTML
- client-side helpers for catalog search and grouping in generated JS

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py -q`
Expected: FAIL because the current catalog page does not render these controls.

### Task 2: Harden The Static Catalog Builder

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Implement static navigation shell**

Render:
- search box
- overview stats cards
- group navigation region
- grouped run sections keyed by `scenario_name`

Keep the current catalog manifest and workflow unchanged.

**Step 2: Implement minimal client-side grouping and filtering**

In `app.js`, add:
- text search against run id / scenario / target / schedule
- scenario grouping helper
- synchronized rendering for summary table and grouped sections

Do not fetch any new files or add runtime persistence in this batch.

**Step 3: Harden styles**

Add styling for:
- stat cards
- group navigation chips
- grouped section cards
- filtered empty states

**Step 4: Run focused verification**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py -q`
Expected: PASS

### Task 3: Docs, Full Verification, Commit

**Files:**
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- grouped catalog navigation behavior
- unchanged data-source boundary
- remaining gaps such as richer workspace grouping and deep links

**Step 2: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 3: Commit**

```bash
git add src/llm_sched/visualization/catalog_builder.py docs/development/phase-e-visualization-workbench-handoff.md docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-07-spec-19-visualization-catalog-grouping.md tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: harden spec 19 visualization catalog navigation"
```
