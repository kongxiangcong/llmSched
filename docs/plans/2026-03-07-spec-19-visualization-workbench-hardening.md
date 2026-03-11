# SPEC-19 Visualization Workbench Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add first-pass search, filter, and block drill-down interactions to the static visualization workbench without changing the run-root workflow or introducing a frontend framework.

**Architecture:** Keep `VisualizationBundle` as the only UI data source and harden the generated static workbench in place. The builder will extend `index.html`, `app.js`, and `styles.css` to render graph/timeline controls, apply client-side filtering, and expose timeline block details in a dedicated drill-down surface.

**Tech Stack:** Python 3.14, existing static workbench builder, HTML/CSS/JavaScript, pytest unit tests.

---

### Task 1: Add Hardening Tests For Search, Filter, And Drill-Down

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing tests**

Extend builder tests to cover:
- graph search input and stage/core filter controls in generated HTML
- timeline detail shell in generated HTML
- client-side helpers for graph filtering and timeline block detail rendering in generated JS
- no regression in optional sweep-panel behavior

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/visualization/test_workbench_builder.py -q`
Expected: FAIL because the current workbench does not render these controls.

**Step 3: Write minimal implementation**

Do not change pipeline or contract layers yet. Only harden the builder output.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/visualization/test_workbench_builder.py -q`
Expected: PASS

### Task 2: Harden The Static Workbench Builder

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`

**Step 1: Implement graph and timeline control shells**

Render:
- graph search box
- stage filter select
- core filter select
- timeline detail panel

Keep the HTML static and browser-only.

**Step 2: Implement minimal client-side interactions**

In `app.js`, add:
- graph node text filtering
- timeline row filtering by stage/core/query
- timeline block click-to-detail rendering

Keep all data sourced from the already loaded bundle. Do not fetch any additional files.

**Step 3: Harden styles**

Add intentional styling for:
- control rows
- active table rows
- detail panel
- empty-state messaging after filtering

**Step 4: Run focused tests**

Run: `python -m pytest tests/unit/visualization/test_workbench_builder.py -q`
Expected: PASS

### Task 3: Docs And Verification

**Files:**
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- new search/filter/drill-down capabilities
- unchanged data-source boundary (`visualization_bundle.json`)
- remaining gaps such as cross-run catalog and richer export

**Step 2: Run focused verification**

Run:
- `python -m pytest tests/unit/visualization/test_workbench_builder.py -q`

Expected: PASS

**Step 3: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 4: Commit**

```bash
git add src/llm_sched/visualization/workbench_builder.py docs/development/phase-e-visualization-workbench-handoff.md docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-07-spec-19-visualization-workbench-hardening.md tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: harden spec 19 visualization workbench interactions"
```
