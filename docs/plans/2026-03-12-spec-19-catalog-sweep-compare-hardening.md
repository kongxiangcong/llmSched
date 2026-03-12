# SPEC-19 Catalog Sweep Compare Hardening Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the existing `SPEC-19` catalog compare tray and workspace compare surface so matched sweep layer compare rows are easier to scan and easier to drill into.

**Architecture:** Keep the current catalog compare surface and local `sweep_comparisons` matching logic. Add deterministic ordering and top-N truncation for rendered `layer_deltas`, then add an explicit matched sweep drill-down link that opens the workbench `sweep` panel for the run that owns the matched summary.

**Tech Stack:** Python 3.11, static catalog builder JS, existing visualization catalog contracts/pipeline, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `11 passed`
- `python -m pytest tests/smoke/test_cli_run_visualization_catalog.py -q`
  - `6 passed`

---

### Task 1: Add Failing Catalog Builder And Workflow Tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Assert that:
- catalog app JS declares deterministic sweep-layer ordering and top-N truncation helpers
- rendered assets mention the truncation summary string
- rendered assets include an explicit sweep drill-down link label for matched compare pairs

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/visualization/test_catalog_builder.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: fail because the current catalog compare UI renders raw `layer_deltas` without ordering, truncation, or explicit sweep drill-down.

**Step 3: Write minimal implementation**

Implement:
- deterministic `layer_deltas` sorting by absolute cycle delta, then layer id
- top-N truncation with a clear “showing top N of M” summary
- explicit matched sweep drill-down link to the workbench `sweep` panel

Keep the hardening scoped to the current compare tray/workspace surface. Do not add new compare tabs or backend services.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Verify And Record The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-19-catalog-sweep-compare-hardening.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/visualization/test_catalog_builder.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke**

Run:
```powershell
python -m pytest tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

**Step 3: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-19` checkpoint documenting that catalog sweep compare now renders ordered top-N layer deltas plus explicit sweep drill-down links.
