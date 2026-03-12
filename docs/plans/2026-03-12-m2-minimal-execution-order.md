# M2 Closure Minimal Execution Order Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining `Phase C / M2` backlog in the smallest order that can change milestone status, while keeping `SPEC-19` work limited to M2-facing debug acceleration.

**Architecture:** Treat `run-phase-c-acceptance` and `run-phase-c-gate` as the single source of truth. First close planner-side `SPEC-08` blockers, then rerun the canonical matrix and only patch concrete downstream gaps that still block acceptance. Keep `SPEC-19` work strictly incremental and only when it shortens the loop for diagnosing blocked canonical cases.

**Tech Stack:** Python 3.11, Typer CLI, Pydantic contracts, pytest unit/smoke suites, static visualization catalog/workbench.

---

### Task 1: Freeze The Current M2 Blocker List

**Files:**
- Review: `README.md`
- Review: `docs/development/evaluation-compiler-roadmap.md`
- Review: `docs/plans/2026-03-11-phase-c-acceptance-rewrite.md`
- Review: `docs/plans/2026-03-12-spec-08-planner-closure-gate.md`
- Output: `workspace_root/reports/phase_c_acceptance_report.json`

**Step 1: Rebuild the canonical acceptance report**

Run: `python -m llm_sched.cli.main run-phase-c-acceptance --report-root <report-root> --workspace-root <workspace-root>`

Expected: `phase_c_acceptance_report.json` is regenerated with fresh case-level gaps.

**Step 2: Run the formal gate**

Run: `python -m llm_sched.cli.main run-phase-c-gate --report-root <report-root> --workspace-root <workspace-root>`

Expected: exit `0` only if the canonical matrix is `ready_for_acceptance`; otherwise use the report as the backlog source.

**Step 3: Classify every remaining blocker**

Bucket each blocked case into exactly one primary lane:
- `SPEC-08` planner closure
- `SPEC-10/11` scheduler acceptance-list evidence
- `SPEC-12` downstream consumer proof
- `SPEC-19` visibility-only follow-up

**Step 4: Refuse new side quests**

Do not open new frontend, service, or compare-mode work unless a blocker from Step 3 points there directly.

### Task 2: Close SPEC-08 Planner-Side Blockers First

**Files:**
- Modify: `src/llm_sched/planning/memory_planner.py`
- Modify: `src/llm_sched/analysis/memory_planner_closure_builder.py`
- Modify: `src/llm_sched/pipeline/memory_planner_closure.py`
- Test: `tests/unit/planning/test_memory_planner.py`
- Test: `tests/unit/analysis/test_memory_planner_closure_builder.py`
- Test: `tests/unit/pipeline/test_memory_planner_closure_workflow.py`

**Step 1: Pick one concrete planner blocker from the fresh acceptance report**

Use the first blocked canonical case with planner-side remaining gaps, especially overflow-region or fit-reasoning gaps.

**Step 2: Add or tighten the failing regression**

Run the smallest affected test file first:
- `python -m pytest tests/unit/planning/test_memory_planner.py -q`
- `python -m pytest tests/unit/analysis/test_memory_planner_closure_builder.py -q`
- `python -m pytest tests/unit/pipeline/test_memory_planner_closure_workflow.py -q`

Expected: one test should fail before any implementation change if the blocker is not already covered.

**Step 3: Implement the minimal planner-side fix**

Limit edits to planner or closure-reporting code that explains or resolves the concrete blocker. Do not widen macro scope or reopen already accepted `SPEC-09` boundaries.

**Step 4: Verify the targeted planner suite**

Run:
- `python -m pytest tests/unit/planning/test_memory_planner.py -q`
- `python -m pytest tests/unit/analysis/test_memory_planner_closure_builder.py -q`
- `python -m pytest tests/unit/pipeline/test_memory_planner_closure_workflow.py -q`

Expected: all affected planner tests pass.

### Task 3: Rerun Phase C And Patch Only Concrete Downstream Gaps

**Files:**
- Modify: `src/llm_sched/analysis/phase_c_acceptance_report_builder.py`
- Modify: `src/llm_sched/pipeline/phase_c_acceptance.py`
- Modify: `src/llm_sched/contracts/phase_c_acceptance_report.py`
- Test: `tests/unit/pipeline/test_phase_c_acceptance_workflow.py`
- Test: `tests/unit/contracts/test_phase_c_acceptance_report.py`

**Step 1: Regenerate the matrix after each planner-side fix**

Run:
- `python -m llm_sched.cli.main run-phase-c-acceptance --report-root <report-root> --workspace-root <workspace-root>`
- `python -m llm_sched.cli.main run-phase-c-gate --report-root <report-root> --workspace-root <workspace-root>`

Expected: either the planner blocker count drops or the next concrete downstream gap becomes visible.

**Step 2: Only patch downstream consumers that still appear in the report**

Priority order:
1. `SPEC-12` packed-summary consumer proof gaps
2. `SPEC-10/11` acceptance-list evidence gaps
3. anything else only if it remains in the canonical matrix output

**Step 3: Keep the accepted Phase C boundaries intact**

Do not reopen:
- broader `SPEC-09` macro coverage
- generic `SPEC-10/11` exploration outside the acceptance list
- new default `SPEC-12` per-record drill-down work

**Step 4: Verify the acceptance surface**

Run:
- `python -m pytest tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/unit/contracts/test_phase_c_acceptance_report.py -q`
- `python -m pytest tests/smoke -m local_smoke -q`

Expected: targeted acceptance tests stay green and the smoke subset remains representative.

### Task 4: Use SPEC-19 Only As An M2 Debug Accelerator

**Files:**
- Review: `docs/plans/2026-03-12-catalog-phase-c-blocked-case-drilldown.md`
- Review: `docs/plans/2026-03-12-catalog-phase-c-blocked-case-links.md`
- Review: `docs/plans/2026-03-12-planner-blocked-memory-query-links.md`
- Review: `docs/plans/2026-03-12-structured-downstream-consumer-links.md`
- Modify only if needed: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify only if needed: `src/llm_sched/visualization/catalog_builder.py`
- Modify only if needed: `src/llm_sched/visualization/workbench_builder.py`

**Step 1: Only take a SPEC-19 task if a blocked case is still slow to debug**

Examples:
- a planner blocker cannot land on the right memory region quickly
- a downstream blocker still cannot land on the right summary or coverage section

**Step 2: Prefer tiny drill-down improvements over new product surface**

Allowed:
- one more deep link
- one more filter/focus affordance
- one more blocked-case inspection aid

Not allowed:
- new service layer
- broader compare-mode expansion
- screenshot/export feature work unrelated to a current M2 blocker

**Step 3: Re-verify only the affected catalog/workbench slice**

Run:
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`

Expected: the debug accelerator remains green without becoming the mainline priority.
