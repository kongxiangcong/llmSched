# Catalog Phase C Blocked Case Drilldown Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let the static `SPEC-19` catalog show which canonical `Phase C` cases are blocked by planner-side closure, downstream closure, or missing matrix coverage without reopening the raw acceptance JSON.

**Architecture:** Extend the catalog metadata with a small structured blocked-case summary derived from `phase_c_acceptance_report.json`. Keep the visualization bundle unchanged, derive the summary only when `run-visualization-catalog` is called with a `workspace_root`, and render a compact blocked-case table inside the existing `Phase C Gate` section.

**Tech Stack:** Python, Pydantic contracts, Phase C acceptance report contract, static HTML/CSS catalog builder, pytest unit/pipeline/smoke tests, Markdown docs

---

### Task 1: Add failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_visualization_catalog.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Contract red test**

Add catalog metadata with `phase_c_blocked_cases` and assert it validates.

**Step 2: Builder red test**

Assert generated catalog HTML renders a blocked-case table with:
- `case_id`
- blocker kind
- planner/downstream status

**Step 3: Workflow red test**

Seed a workspace `phase_c_acceptance_report.json` with:
- one planner-blocked case
- one downstream-blocked case
- one missing canonical case

Assert the catalog manifest copies those three blocked entries.

**Step 4: CLI red test**

Run `run-visualization-catalog --workspace-root ...` and assert the packaged catalog page contains all three blocked-case rows.

### Task 2: Implement blocked-case summary plumbing

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\visualization_catalog.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\__init__.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\visualization_catalog.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add metadata models**

Create a compact blocked-case model carrying:
- `case_id`
- `run_id`
- `blocker_kind`
- `planner_closure_status`
- `downstream_closure_status`
- `remaining_gaps`

Attach an optional list under catalog metadata.

**Step 2: Derive blocked cases from the acceptance report**

Map:
- non-ready case records into planner/downstream/planner+downstream blocked rows
- missing canonical cases into synthetic `missing_case` rows

Keep the summary intentionally small; do not copy the full report.

**Step 3: Render the drilldown**

Extend the existing `Phase C Gate` card with a blocked-case table that appears only when blocked cases exist.

### Task 3: Refresh docs and verify

**Files:**
- Modify: `D:\workspace\llmSched\README.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-e-visualization-workbench-handoff.md`

**Step 1: Document the drilldown**

Record that the static catalog can now show which canonical Phase C cells are blocked and whether the blocker is planner-side, downstream, or missing matrix coverage.

**Step 2: Verify**

```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: pass
