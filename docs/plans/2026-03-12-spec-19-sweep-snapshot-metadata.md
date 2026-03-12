# SPEC-19 Sweep Snapshot Metadata Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a structured `snapshot_metadata` surface to focused sweep exports and use it to render a stable focused header block inside SVG snapshots.

**Architecture:** Keep the existing static workbench export path. Extend the sweep export helper with one `snapshot_metadata` object, then let the SVG snapshot path consume that object for title/header rendering instead of rebuilding focused summary strings ad hoc.

**Tech Stack:** Python 3.11, static visualization workbench builder, existing workbench workflow/CLI, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
  - `9 passed in 0.35s`
- `python -m pytest tests/smoke/test_cli_run_visualization_workbench.py -q`
  - `2 passed in 104.58s`

---

### Task 1: Add Failing Tests For Structured Snapshot Metadata

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Write the failing tests**

Assert that generated workbench assets now expose:
- `buildSweepSnapshotMetadata(...)`
- `snapshot_metadata` plus `header_rows`
- `renderPanelSnapshotHeader(...)`
- `Snapshot Focus` strings for focused SVG header rendering

**Step 2: Run red**

Run:
```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
python -m pytest tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: fail because sweep export currently carries focus details, but not a structured snapshot metadata object or focused SVG header renderer.

**Step 3: Write minimal implementation**

Implement:
- one `buildSweepSnapshotMetadata(...)` helper inside the workbench app JS
- one `snapshot_metadata` object in the sweep export payload
- one `renderPanelSnapshotHeader(...)` path that renders focused header rows above the SVG body text

Do not add a new export format or service surface.

**Step 4: Run green**

Run the same commands again and expect PASS.

### Task 2: Record The Screenshot-Workflow Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-19-sweep-snapshot-metadata.md`

**Step 1: Add one roadmap checkpoint**

If verification is green, record that focused sweep exports now expose structured snapshot metadata and that SVG snapshots render a focused header block from that payload.

**Step 2: Keep the follow-up narrow**

Record that the remaining screenshot gap is richer layout/export workflow on top of the current JSON-plus-SVG metadata path, not a new compare workflow.
