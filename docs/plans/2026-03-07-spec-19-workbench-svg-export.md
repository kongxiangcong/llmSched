# SPEC-19 Workbench SVG Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an exportable image workflow to the static visualization workbench by generating SVG snapshots for the active panel.

**Architecture:** Reuse the current saved-view/export action bar and extend it with one additional image-export action. The generated JavaScript will derive a compact textual snapshot from the active panel data and current UI state, render it into an SVG string, and download it as a static image file. This avoids browser automation and preserves `visualization_bundle.json` as the only data source.

**Tech Stack:** Python, pytest, static HTML/CSS/JavaScript builders

---

### Task 1: Add failing tests for SVG export controls

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing test**

Add assertions that the generated assets include:
- `download-panel-svg-button`
- `Export current panel SVG`
- JavaScript helpers for SVG snapshot building and download

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because the current workbench only supports JSON export.

**Step 3: Write minimal implementation**

Implement the smallest builder changes needed to expose SVG export.

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/visualization/test_workbench_builder.py src/llm_sched/visualization/workbench_builder.py
git commit -m "feat: add workbench svg export controls"
```

### Task 2: Implement active-panel SVG snapshot export

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Test: `tests/unit/visualization/test_workbench_builder.py`

**Step 1: Write the failing test**

Make the test check for:
- `buildPanelSnapshotLines`
- `escapeSvgText`
- `buildPanelSnapshotSvg`
- `downloadCurrentPanelSvg`

**Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: FAIL because the workbench has no image-export helper path.

**Step 3: Write minimal implementation**

Add:
- one SVG export button in the action bar
- helper functions to derive snapshot lines from the active panel export payload
- SVG generation from those lines
- image download for the active panel

**Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/unit/visualization/test_workbench_builder.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: add workbench svg snapshot export"
```

### Task 3: Update docs and verify full suite

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Create: `docs/plans/2026-03-07-spec-19-workbench-svg-export.md`

**Step 1: Update docs**

Document the new stable behavior:
- active panel can be exported as SVG
- screenshot gap is now narrowed to richer rendered-image workflows, not basic image export absence

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
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-e-visualization-workbench-handoff.md docs/plans/2026-03-07-spec-19-workbench-svg-export.md
git commit -m "docs: update spec 19 svg export checkpoint"
```
