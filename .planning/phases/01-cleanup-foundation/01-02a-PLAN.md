---
phase: 01-cleanup-foundation
plan: 02a
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm_sched/pipeline/
  - src/llm_sched/planning/
autonomous: true
requirements:
  - CLEAN-01
  - CLEAN-04
must_haves:
  truths:
    - "pipeline/ contains only execution-semantic modules (frontend_analysis, memory_planning, tile_planning, dual_core_scheduling)"
    - "planning/ no longer has single_core_scheduler.py, descriptor_builder.py, descriptor_packer.py"
  artifacts:
    - path: "src/llm_sched/pipeline/__init__.py"
      provides: "Clean pipeline exports"
      absent_exports:
        - "run_descriptor_generation"
        - "run_single_core_scheduling"
        - "run_performance_estimation"
        - "run_prefill_evaluation"
        - "run_decode_evaluation"
        - "run_diagnosis_analysis"
        - "run_diagnosis_packaging"
        - "run_diagnosis_workbench"
        - "run_sweep_analysis"
        - "run_phase_d_compare"
        - "run_visualization_packaging"
        - "run_visualization_catalog"
        - "run_visualization_workbench"
        - "run_phase_c_acceptance"
        - "run_memory_planner_closure"
    - path: "src/llm_sched/planning/__init__.py"
      provides: "Clean planning exports"
      absent_exports:
        - "plan_single_core_schedule"
        - "build_descriptor_artifacts"
        - "pack_descriptor_bundle"
  key_links:
    - from: "planning/dual_core_scheduler.py"
      to: "contracts/memory_plan.py"
      via: "import llm_sched.contracts.memory_plan"
      note: "Will be updated in Plan 03 restructure"
    - from: "planning/memory_planner.py"
      to: "contracts/memory_plan.py"
      via: "import llm_sched.contracts.memory_plan"
      note: "Will be updated in Plan 03 restructure"
---

<objective>
Selectively delete pipeline and planning modules that are unambiguously v0.9-era, and rewrite the package __init__.py files to export only retained symbols.

Purpose: Remove the largest deletion targets within mixed directories before the more delicate IR, contracts, and config cleanup in Plan 02b.
Output: Clean pipeline/ and planning/ directories ready for restructure in Plan 03.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-cleanup-foundation/01-CONTEXT.md
@.planning/PROJECT.md

## Decisions Implemented
- D-03: pipeline/descriptor_generation.py deleted entirely
- D-04: pipeline/single_core_scheduling.py deleted entirely
- D-05: pipeline/performance_estimation.py deleted entirely

## Modules to DELETE in pipeline/
- descriptor_generation.py (D-03)
- single_core_scheduling.py (D-04)
- performance_estimation.py (D-05)
- decode_evaluation.py
- diagnosis_analysis.py
- diagnosis_packaging.py
- diagnosis_workbench.py
- phase_c_acceptance.py
- phase_d_compare.py
- prefill_evaluation.py
- sweep_analysis.py
- visualization_packaging.py
- visualization_catalog.py
- visualization_workbench.py
- memory_planner_closure.py

## Modules to KEEP in pipeline/
- frontend_analysis.py
- memory_planning.py
- tile_planning.py
- dual_core_scheduling.py
- __init__.py (rewritten)

## Modules to DELETE in planning/
- single_core_scheduler.py
- descriptor_builder.py
- descriptor_packer.py

## Modules to KEEP in planning/
- dual_core_scheduler.py
- memory_planner.py
- tile_planner.py
- schedule_duration.py
- schedule_reservations.py
- __init__.py (rewritten)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Selectively delete pipeline modules and rewrite pipeline/__init__.py</name>
  <files>
    src/llm_sched/pipeline/descriptor_generation.py
    src/llm_sched/pipeline/single_core_scheduling.py
    src/llm_sched/pipeline/performance_estimation.py
    src/llm_sched/pipeline/decode_evaluation.py
    src/llm_sched/pipeline/diagnosis_analysis.py
    src/llm_sched/pipeline/diagnosis_packaging.py
    src/llm_sched/pipeline/diagnosis_workbench.py
    src/llm_sched/pipeline/phase_c_acceptance.py
    src/llm_sched/pipeline/phase_d_compare.py
    src/llm_sched/pipeline/prefill_evaluation.py
    src/llm_sched/pipeline/sweep_analysis.py
    src/llm_sched/pipeline/visualization_packaging.py
    src/llm_sched/pipeline/visualization_catalog.py
    src/llm_sched/pipeline/visualization_workbench.py
    src/llm_sched/pipeline/memory_planner_closure.py
    src/llm_sched/pipeline/__init__.py
  </files>
  <read_first>
    - src/llm_sched/pipeline/__init__.py (current exports)
    - src/llm_sched/pipeline/frontend_analysis.py (confirm it stays)
    - src/llm_sched/pipeline/memory_planning.py (confirm it stays)
    - src/llm_sched/pipeline/tile_planning.py (confirm it stays)
    - src/llm_sched/pipeline/dual_core_scheduling.py (confirm it stays)
  </read_first>
  <action>
    1. Delete the 15 pipeline modules listed in <files> using `git rm`:
       - `git rm src/llm_sched/pipeline/descriptor_generation.py`
       - `git rm src/llm_sched/pipeline/single_core_scheduling.py`
       - `git rm src/llm_sched/pipeline/performance_estimation.py`
       - `git rm src/llm_sched/pipeline/decode_evaluation.py`
       - `git rm src/llm_sched/pipeline/diagnosis_analysis.py`
       - `git rm src/llm_sched/pipeline/diagnosis_packaging.py`
       - `git rm src/llm_sched/pipeline/diagnosis_workbench.py`
       - `git rm src/llm_sched/pipeline/phase_c_acceptance.py`
       - `git rm src/llm_sched/pipeline/phase_d_compare.py`
       - `git rm src/llm_sched/pipeline/prefill_evaluation.py`
       - `git rm src/llm_sched/pipeline/sweep_analysis.py`
       - `git rm src/llm_sched/pipeline/visualization_packaging.py`
       - `git rm src/llm_sched/pipeline/visualization_catalog.py`
       - `git rm src/llm_sched/pipeline/visualization_workbench.py`
       - `git rm src/llm_sched/pipeline/memory_planner_closure.py`

    2. Rewrite `src/llm_sched/pipeline/__init__.py` to export only the four retained modules:

    ```python
    """Workflow entrypoints for execution-semantic pipeline."""

    from llm_sched.pipeline.dual_core_scheduling import (
        DualCoreSchedulingResult,
        run_dual_core_scheduling,
    )
    from llm_sched.pipeline.frontend_analysis import FrontendAnalysisResult, run_frontend_analysis
    from llm_sched.pipeline.memory_planning import MemoryPlanningResult, run_memory_planning
    from llm_sched.pipeline.tile_planning import TilePlanningResult, run_tile_planning

    __all__ = [
        "DualCoreSchedulingResult",
        "FrontendAnalysisResult",
        "MemoryPlanningResult",
        "TilePlanningResult",
        "run_dual_core_scheduling",
        "run_frontend_analysis",
        "run_memory_planning",
        "run_tile_planning",
    ]
    ```
  </action>
  <verify>
    <automated>
      test -f src/llm_sched/pipeline/descriptor_generation.py && echo "FAIL" && exit 1 || echo "OK descriptor_generation deleted"
      test -f src/llm_sched/pipeline/single_core_scheduling.py && echo "FAIL" && exit 1 || echo "OK single_core_scheduling deleted"
      test -f src/llm_sched/pipeline/performance_estimation.py && echo "FAIL" && exit 1 || echo "OK performance_estimation deleted"
      test -f src/llm_sched/pipeline/decode_evaluation.py && echo "FAIL" && exit 1 || echo "OK decode_evaluation deleted"
      test -f src/llm_sched/pipeline/diagnosis_analysis.py && echo "FAIL" && exit 1 || echo "OK diagnosis_analysis deleted"
      test -f src/llm_sched/pipeline/diagnosis_packaging.py && echo "FAIL" && exit 1 || echo "OK diagnosis_packaging deleted"
      test -f src/llm_sched/pipeline/diagnosis_workbench.py && echo "FAIL" && exit 1 || echo "OK diagnosis_workbench deleted"
      test -f src/llm_sched/pipeline/phase_c_acceptance.py && echo "FAIL" && exit 1 || echo "OK phase_c_acceptance deleted"
      test -f src/llm_sched/pipeline/phase_d_compare.py && echo "FAIL" && exit 1 || echo "OK phase_d_compare deleted"
      test -f src/llm_sched/pipeline/prefill_evaluation.py && echo "FAIL" && exit 1 || echo "OK prefill_evaluation deleted"
      test -f src/llm_sched/pipeline/sweep_analysis.py && echo "FAIL" && exit 1 || echo "OK sweep_analysis deleted"
      test -f src/llm_sched/pipeline/visualization_packaging.py && echo "FAIL" && exit 1 || echo "OK visualization_packaging deleted"
      test -f src/llm_sched/pipeline/visualization_catalog.py && echo "FAIL" && exit 1 || echo "OK visualization_catalog deleted"
      test -f src/llm_sched/pipeline/visualization_workbench.py && echo "FAIL" && exit 1 || echo "OK visualization_workbench deleted"
      test -f src/llm_sched/pipeline/memory_planner_closure.py && echo "FAIL" && exit 1 || echo "OK memory_planner_closure deleted"
      grep -q "run_descriptor_generation" src/llm_sched/pipeline/__init__.py && echo "FAIL" && exit 1 || echo "OK init clean"
      grep -q "run_dual_core_scheduling" src/llm_sched/pipeline/__init__.py && echo "OK init has dual_core" || (echo "FAIL" && exit 1)
    </automated>
  </verify>
  <acceptance_criteria>
    - None of the 15 deleted pipeline files exist
    - `src/llm_sched/pipeline/__init__.py` exports exactly: DualCoreSchedulingResult, FrontendAnalysisResult, MemoryPlanningResult, TilePlanningResult, run_dual_core_scheduling, run_frontend_analysis, run_memory_planning, run_tile_planning
    - `grep -c "run_descriptor_generation" src/llm_sched/pipeline/__init__.py` returns 0
  </acceptance_criteria>
  <done>Pipeline directory contains only execution-semantic modules and clean __init__.py.</done>
</task>

<task type="auto">
  <name>Task 2: Selectively delete planning modules and rewrite planning/__init__.py</name>
  <files>
    src/llm_sched/planning/single_core_scheduler.py
    src/llm_sched/planning/descriptor_builder.py
    src/llm_sched/planning/descriptor_packer.py
    src/llm_sched/planning/__init__.py
  </files>
  <read_first>
    - src/llm_sched/planning/__init__.py (current exports)
    - src/llm_sched/planning/dual_core_scheduler.py (confirm it stays)
    - src/llm_sched/planning/memory_planner.py (confirm it stays)
    - src/llm_sched/planning/tile_planner.py (confirm it stays)
    - src/llm_sched/planning/schedule_duration.py (confirm it stays)
    - src/llm_sched/planning/schedule_reservations.py (confirm it stays)
  </read_first>
  <action>
    1. Delete the three planning modules:
       - `git rm src/llm_sched/planning/single_core_scheduler.py`
       - `git rm src/llm_sched/planning/descriptor_builder.py`
       - `git rm src/llm_sched/planning/descriptor_packer.py`

    2. Rewrite `src/llm_sched/planning/__init__.py`:

    ```python
    """Planning entrypoints for scheduling and memory/tile planning."""

    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_duration_slots
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    __all__ = [
        "build_reservation_timeline",
        "estimate_stage_duration_slots",
        "find_earliest_issue_slot",
        "plan_dual_core_schedule",
        "plan_memory_artifact",
        "plan_tiling_artifact",
        "reserve_resource_windows",
    ]
    ```
  </action>
  <verify>
    <automated>
      test -f src/llm_sched/planning/single_core_scheduler.py && echo "FAIL" && exit 1 || echo "OK single_core_scheduler deleted"
      test -f src/llm_sched/planning/descriptor_builder.py && echo "FAIL" && exit 1 || echo "OK descriptor_builder deleted"
      test -f src/llm_sched/planning/descriptor_packer.py && echo "FAIL" && exit 1 || echo "OK descriptor_packer deleted"
      grep -q "plan_single_core_schedule" src/llm_sched/planning/__init__.py && echo "FAIL" && exit 1 || echo "OK init clean"
      grep -q "plan_dual_core_schedule" src/llm_sched/planning/__init__.py && echo "OK init has dual_core" || (echo "FAIL" && exit 1)
    </automated>
  </verify>
  <acceptance_criteria>
    - single_core_scheduler.py, descriptor_builder.py, descriptor_packer.py do not exist
    - planning/__init__.py exports exactly: build_reservation_timeline, estimate_stage_duration_slots, find_earliest_issue_slot, plan_dual_core_schedule, plan_memory_artifact, plan_tiling_artifact, reserve_resource_windows
  </acceptance_criteria>
  <done>Planning directory contains only scheduling/memory/tile modules and clean __init__.py.</done>
</task>

<task type="auto">
  <name>Task 3: Commit pipeline and planning deletions</name>
  <files>.git/</files>
  <read_first>
    - git status output from Tasks 1-2
  </read_first>
  <action>
    Stage all changes from Tasks 1-2 and commit:

    `git add -A && git commit -m "cleanup: remove v0.9-era pipeline and planning modules"`

    If pre-commit hooks fail, investigate and fix.
  </action>
  <verify>
    <automated>
      git log -1 --oneline | grep -q "cleanup: remove v0.9-era pipeline and planning modules"
    </automated>
  </verify>
  <acceptance_criteria>
    - `git log -1 --oneline` contains "cleanup: remove v0.9-era pipeline and planning modules"
    - `git status` is clean
  </acceptance_criteria>
  <done>Pipeline and planning deletions committed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Working tree -> git index | Changes staged before commit; reversible until commit |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-02a | Denial of Service | Working tree | accept | Same as T-01-01; git history preserves old files. |
</threat_model>

<verification>
1. pipeline/ has exactly 5 .py files: __init__.py, frontend_analysis.py, memory_planning.py, tile_planning.py, dual_core_scheduling.py
2. planning/ has exactly 6 .py files: __init__.py, dual_core_scheduler.py, memory_planner.py, tile_planner.py, schedule_duration.py, schedule_reservations.py
3. All deleted files are absent and committed
</verification>

<success_criteria>
- pipeline/ contains only execution-semantic modules
- planning/ no longer has single-core or descriptor modules
- All changes committed
</success_criteria>

<output>
After completion, create `.planning/phases/01-cleanup-foundation/01-02a-SUMMARY.md`
</output>
