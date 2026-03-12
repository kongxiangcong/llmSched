# Catalog Phase C Gate Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface the workspace-level `Phase C` gate summary inside the `SPEC-19` static catalog so catalog users can see canonical matrix readiness without reopening `phase_c_acceptance_report.json`.

**Architecture:** Keep the existing per-run visualization bundle unchanged. Add one optional workspace-level `phase_c_gate_summary` block to the catalog artifact metadata, populate it only when `run-visualization-catalog` receives a `workspace_root` with `reports/phase_c_acceptance_report.json`, and render that summary in the catalog header.

**Tech Stack:** Python, Pydantic contracts, static HTML/JS catalog builder, existing Phase C acceptance report contract, pytest unit/pipeline/smoke tests, Markdown docs

---

### Task 1: Add failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_visualization_catalog.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Contract red test**

Add a metadata fixture with optional `phase_c_gate_summary` and assert it validates.

**Step 2: Builder red test**

Call `build_visualization_catalog(...)` with a `phase_c_gate_summary` and assert generated HTML contains:
- `Phase C Gate`
- overall status
- planner/downstream blocked counts

**Step 3: Workflow red test**

Provide a `workspace_root` with:
- packaged run roots
- `reports/phase_c_acceptance_report.json`

Assert catalog manifest metadata copies the summary.

**Step 4: CLI red test**

Run `run-visualization-catalog --workspace-root ...` and assert generated `index.html` contains the new `Phase C Gate` section.

### Task 2: Implement the catalog summary

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\visualization_catalog.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\visualization_catalog.py`

**Step 1: Add optional summary contract**

Create a small `VisualizationCatalogPhaseCGateSummary` model with:
- `status`
- `ready_case_count`
- `blocked_case_count`
- `planner_blocked_case_count`
- `downstream_blocked_case_count`
- `missing_case_count`
- `duplicate_case_count`

Attach it as an optional field under `VisualizationCatalogMetadata`.

**Step 2: Populate summary from workspace report**

When `workspace_root` is provided and `workspace_root/reports/phase_c_acceptance_report.json` exists, load `PhaseCAcceptanceReport` and map it into the catalog metadata summary. Do not fail catalog generation if the report is absent.

**Step 3: Render header summary**

Add a compact card or banner in the catalog header showing the Phase C gate status and blocked-count breakdown.

### Task 3: Refresh docs and verify

**Files:**
- Modify: `D:\workspace\llmSched\README.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-e-visualization-workbench-handoff.md`

**Step 1: Document the visible gate summary**

Record that the static catalog can now surface workspace-level `Phase C` readiness when built from a workspace root.

**Step 2: Verify**

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: pass
