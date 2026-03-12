# SPEC-19 Sweep Export Focus Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make workbench `sweep` panel exports and snapshots explicitly carry the currently focused candidate/layer state instead of only dumping filtered comparison rows.

**Architecture:** Keep the current static workbench flow. Add one sweep-export helper that produces a stable focus-aware payload, reuse it for panel JSON export and snapshot line generation, and avoid opening any new compare workflow or service layer.

**Tech Stack:** Python 3.11, static visualization workbench builder, existing visualization workbench workflow/CLI, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
  - `9 passed in 0.32s`
- `python -m pytest tests/smoke/test_cli_run_visualization_workbench.py -q`
  - `2 passed in 109.21s`

---

### Task 1: Add Failing Workbench Export-Focus Tests

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Write the failing tests**

Assert that generated workbench assets now expose:
- a dedicated `buildSweepExportData(...)` helper
- explicit `focused_sweep_candidate` / `focused_sweep_layer` fields
- explicit `focused_comparison_count` / `focused_layer_delta_count` fields
- snapshot/export-facing labels for baseline target and focused counts

**Step 2: Run red**

Run:
```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
python -m pytest tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: fail because workbench JS only exports filtered `comparisons` and snapshot lines still read focus state directly from `UI_STATE`.

**Step 3: Write minimal implementation**

Implement:
- one focus-aware sweep export helper
- one `buildPanelExportData("sweep")` path that reuses that helper
- one `buildPanelSnapshotLines("sweep")` path that reads the exported focus metadata instead of bypassing it

Do not add a new workflow, contract, or service surface.

**Step 4: Run green**

Run the same commands again and expect PASS.

### Task 2: Record The Focused Export Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-19-sweep-export-focus.md`

**Step 1: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-19` checkpoint documenting that sweep panel JSON/SVG export now preserves focused candidate/layer metadata and focused counts.

**Step 2: Keep the open follow-up narrow**

Record that the remaining `SPEC-19` export gap is richer screenshot/export workflows on top of the current focus-aware panel JSON/SVG path, not a new compare workflow.
