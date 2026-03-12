# SPEC-19 Sweep Export Detail Summary Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend workbench `sweep` export so focused candidate/layer state is accompanied by one explicit focused layer-delta detail summary, and make export file naming plus snapshot titles reflect the current focus.

**Architecture:** Keep the existing static workbench path. Enrich the existing sweep export helper with one optional focused layer summary object, then reuse that payload when building snapshot lines, snapshot titles, and download filenames.

**Tech Stack:** Python 3.11, static visualization workbench builder, existing workbench workflow/CLI, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
  - `9 passed in 0.32s`
- `python -m pytest tests/smoke/test_cli_run_visualization_workbench.py -q`
  - `2 passed in 102.64s`

---

### Task 1: Add Failing Tests For Focused Detail Summary And Focus-Aware Naming

**Files:**
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Write the failing tests**

Assert that generated workbench assets now expose:
- `focused_layer_delta_summary` in sweep export payload
- `Focused Layer Summary` strings for export/snapshot surfaces
- helpers for focus-aware snapshot titles and export filenames

**Step 2: Run red**

Run:
```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
python -m pytest tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: fail because the current sweep export only carries focused counts and still uses generic panel snapshot titles and filenames.

**Step 3: Write minimal implementation**

Implement:
- one optional `focused_layer_delta_summary` field in the sweep export helper
- one focus-aware snapshot-title helper
- one focus-aware export-filename helper reused by JSON and SVG download paths

Do not introduce a new workflow or additional compare state.

**Step 4: Run green**

Run the same commands again and expect PASS.

### Task 2: Record The Narrow Hardening Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-19-sweep-export-detail-summary.md`

**Step 1: Add one roadmap checkpoint**

If verification is green, record that sweep export now includes a focused layer summary row and that workbench download filenames / snapshot titles preserve current focus.

**Step 2: Keep the remaining gap narrow**

Record that the remaining export gap is richer screenshot workflow on top of the current focus-aware JSON/SVG path, not a new contract or service layer.
