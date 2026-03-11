# SPEC-19 Workbench Export And Saved View Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add saved-view and export affordances to the static visualization workbench without changing the visualization bundle contract.

**Architecture:** Reuse the existing URL-state routing as the saved-view mechanism and expose it through a copy-link action. Add a second action that exports the currently active panel plus filtered state to a JSON download. Keep everything inside the generated static `index.html + app.js + styles.css` surface and continue using `visualization_bundle.json` as the only source of truth.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript builders

---

### Task 1: Add failing tests for saved-view/export controls

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing test**

Add assertions that the generated assets include:
- `copy-view-link-button`
- `download-view-json-button`
- `workbench-action-status`
- JavaScript helpers for view serialization and export

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because the current workbench has no saved-view or export controls.

**Step 3: Write minimal implementation**

Implement the smallest builder changes needed to expose these controls.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/visualization/test_workbench_builder.py src/llm_sched/visualization/workbench_builder.py
git commit -m "feat: add workbench saved view controls"
```

### Task 2: Implement saved-view link copy and panel export

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Test: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing test**

Make the test check for:
- `serializeUiState`
- `buildCurrentViewUrl`
- `copyCurrentViewLink`
- `downloadCurrentViewJson`
- JSON export payload construction for the active panel

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because those helpers do not yet exist.

**Step 3: Write minimal implementation**

Add:
- a small action bar in the workbench shell
- save-view status text
- panel-aware URL serialization
- active-panel JSON export using the currently filtered UI state

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: add workbench panel export"
```

### Task 3: Update docs and verify full suite

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Create: `docs/plans/2026-03-07-spec-19-workbench-export-saved-view.md`

**Step 1: Update docs**

Document the new stable behavior:
- current view links can be copied from the static workbench
- active panel state can be exported as JSON

**Step 2: Run targeted verification**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 3: Run full verification**

Run:

```bash
python -m pytest -q
git diff --check
```

Expected:
- all tests pass
- no diff errors

**Step 4: Commit**

```bash
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-e-visualization-workbench-handoff.md docs/plans/2026-03-07-spec-19-workbench-export-saved-view.md
git commit -m "docs: update spec 19 saved view export checkpoint"
```
