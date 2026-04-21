---
phase: 01-cleanup-foundation
plan: 03b
type: execute
wave: 3
depends_on:
  - 01-03a
files_modified:
  - src/llm_sched/scheduler/
  - src/llm_sched/descriptor/
  - src/llm_sched/frontend/
  - src/llm_sched/__init__.py
  - src/llm_sched/pipeline/
  - src/llm_sched/planning/
autonomous: true
requirements:
  - CLEAN-01
  - CLEAN-04
must_haves:
  truths:
    - "scheduler/ contains memory.py, tile.py, dual_core.py from planning/ and frontend.py from pipeline/"
    - "descriptor/ exists as an empty package (Phase 4 populates it)"
    - "frontend/ imports use new flat paths (llm_sched.config, llm_sched.arch, llm_sched.models, llm_sched.ir.schedule)"
    - "No old import paths (llm_sched.planning.*, llm_sched.pipeline.*, llm_sched.contracts.*) remain in src/llm_sched/"
    - "Old subpackages pipeline/ and planning/ are removed"
  artifacts:
    - path: "src/llm_sched/scheduler/__init__.py"
      provides: "Scheduler package exports"
    - path: "src/llm_sched/descriptor/__init__.py"
      provides: "Descriptor package placeholder"
    - path: "src/llm_sched/frontend/__init__.py"
      provides: "Clean frontend exports"
  key_links:
    - from: "scheduler/dual_core.py"
      to: "arch.py"
      via: "import llm_sched.arch"
    - from: "scheduler/memory.py"
      to: "models.py"
      via: "import llm_sched.models"
    - from: "frontend/legality.py"
      to: "arch.py"
      via: "import llm_sched.arch"
---

<objective>
Create scheduler/ and descriptor/ packages, move modules from planning/ and pipeline/, update all imports across frontend/ and scheduler/, and remove old subpackages.

Purpose: Complete the v2 package restructure by creating domain packages and ensuring no broken imports remain.
Output: Clean scheduler/, descriptor/, frontend/ with all imports pointing to new flat paths.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-cleanup-foundation/01-CONTEXT.md

## Decisions Implemented
- D-19: Restructure into flat domain packages:
  - `scheduler/` (merged from `planning/` + `pipeline/`; `memory.py`, `tile.py`, `dual_core.py`, `duration.py`, `reservations.py`, `frontend.py`)
  - `descriptor/` (created in Phase 4; placeholder now)
  - `frontend/` (retained with updated imports)

## Target Structure
```
src/llm_sched/
  __init__.py
  cli.py
  config.py
  arch.py
  models.py
  ir/
    __init__.py
    graph.py
    nig.py
    schedule.py
    common.py
    validators.py
    io.py
  frontend/
    __init__.py
    importer.py
    canonicalize.py
    nig_lowering.py
    binding.py
    legality.py
    model_metadata.py
    shape_binding.py
  scheduler/
    __init__.py
    memory.py
    tile.py
    dual_core.py
    duration.py
    reservations.py
    frontend.py
  descriptor/
    __init__.py
```

## Old Structure to Remove
- pipeline/ (frontend_analysis.py, memory_planning.py, tile_planning.py, dual_core_scheduling.py, __init__.py)
- planning/ (dual_core_scheduler.py, memory_planner.py, tile_planner.py, schedule_duration.py, schedule_reservations.py, __init__.py)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create scheduler/ package from planning/ and pipeline/</name>
  <files>
    src/llm_sched/scheduler/__init__.py
    src/llm_sched/scheduler/memory.py
    src/llm_sched/scheduler/tile.py
    src/llm_sched/scheduler/dual_core.py
    src/llm_sched/scheduler/duration.py
    src/llm_sched/scheduler/reservations.py
    src/llm_sched/scheduler/frontend.py
    src/llm_sched/planning/
    src/llm_sched/pipeline/
  </files>
  <read_first>
    - src/llm_sched/planning/dual_core_scheduler.py
    - src/llm_sched/planning/memory_planner.py
    - src/llm_sched/planning/tile_planner.py
    - src/llm_sched/planning/schedule_duration.py
    - src/llm_sched/planning/schedule_reservations.py
    - src/llm_sched/pipeline/frontend_analysis.py
    - src/llm_sched/pipeline/memory_planning.py
    - src/llm_sched/pipeline/tile_planning.py
    - src/llm_sched/pipeline/dual_core_scheduling.py
  </read_first>
  <action>
    Create the scheduler/ package by moving content from planning/ and pipeline/. The scheduler/ package will contain:
    - `memory.py` — from planning/memory_planner.py
    - `tile.py` — from planning/tile_planner.py
    - `dual_core.py` — from planning/dual_core_scheduler.py
    - `duration.py` — from planning/schedule_duration.py
    - `reservations.py` — from planning/schedule_reservations.py
    - `frontend.py` — from pipeline/frontend_analysis.py (renamed to reflect its role)

    Use `git mv` for the moves:
    1. `git mv src/llm_sched/planning/memory_planner.py src/llm_sched/scheduler/memory.py`
    2. `git mv src/llm_sched/planning/tile_planner.py src/llm_sched/scheduler/tile.py`
    3. `git mv src/llm_sched/planning/dual_core_scheduler.py src/llm_sched/scheduler/dual_core.py`
    4. `git mv src/llm_sched/planning/schedule_duration.py src/llm_sched/scheduler/duration.py`
    5. `git mv src/llm_sched/planning/schedule_reservations.py src/llm_sched/scheduler/reservations.py`
    6. `git mv src/llm_sched/pipeline/frontend_analysis.py src/llm_sched/scheduler/frontend.py`

    Then update imports in each moved file:
    - Replace `from llm_sched.config.target_profile import ...` with `from llm_sched.config import ...`
    - Replace `from llm_sched.config.scenario_profile import ...` with `from llm_sched.config import ...`
    - Replace `from llm_sched.arch.capabilities import ...` with `from llm_sched.arch import ...`
    - Replace `from llm_sched.contracts.memory_plan import ...` with `from llm_sched.models import ...`
    - Replace `from llm_sched.contracts.tiling_plan import ...` with `from llm_sched.models import ...`
    - Replace `from llm_sched.ir.nig import ...` with `from llm_sched.ir.nig import ...` (unchanged)
    - Replace `from llm_sched.ir.common import ...` with `from llm_sched.ir.common import ...` (unchanged)
    - Replace `from llm_sched.ir.schedule_ir import ...` with `from llm_sched.ir.schedule import ...`

    Create `src/llm_sched/scheduler/__init__.py`:
    ```python
    """Scheduler package for memory planning, tile planning, and dual-core scheduling."""

    from llm_sched.scheduler.dual_core import plan_dual_core_schedule
    from llm_sched.scheduler.duration import estimate_stage_duration_slots
    from llm_sched.scheduler.frontend import run_frontend_analysis
    from llm_sched.scheduler.memory import plan_memory_artifact
    from llm_sched.scheduler.reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )
    from llm_sched.scheduler.tile import plan_tiling_artifact

    __all__ = [
        "build_reservation_timeline",
        "estimate_stage_duration_slots",
        "find_earliest_issue_slot",
        "plan_dual_core_schedule",
        "plan_memory_artifact",
        "plan_tiling_artifact",
        "reserve_resource_windows",
        "run_frontend_analysis",
    ]
    ```

    Delete the old planning/ and pipeline/ directories:
    - `git rm -r src/llm_sched/planning/`
    - `git rm -r src/llm_sched/pipeline/`
  </action>
  <verify>
    <automated>
      test -d src/llm_sched/scheduler && echo "OK scheduler dir exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/scheduler/memory.py && echo "OK memory.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/scheduler/tile.py && echo "OK tile.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/scheduler/dual_core.py && echo "OK dual_core.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/scheduler/duration.py && echo "OK duration.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/scheduler/reservations.py && echo "OK reservations.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/scheduler/frontend.py && echo "OK frontend.py exists" || (echo "FAIL" && exit 1)
      test -d src/llm_sched/planning && echo "FAIL planning dir still exists" && exit 1 || echo "OK planning dir removed"
      test -d src/llm_sched/pipeline && echo "FAIL pipeline dir still exists" && exit 1 || echo "OK pipeline dir removed"
      python3 -c "from llm_sched.scheduler import plan_dual_core_schedule, plan_memory_artifact, plan_tiling_artifact; print('OK scheduler imports')"
    </automated>
  </verify>
  <acceptance_criteria>
    - scheduler/ directory exists with memory.py, tile.py, dual_core.py, duration.py, reservations.py, frontend.py, __init__.py
    - planning/ and pipeline/ directories do not exist
    - All moved files have updated imports pointing to new flat paths (llm_sched.config, llm_sched.arch, llm_sched.models, llm_sched.ir.schedule)
    - `python3 -c "from llm_sched.scheduler import plan_dual_core_schedule, plan_memory_artifact, plan_tiling_artifact"` succeeds
  </acceptance_criteria>
  <done>scheduler/ package created from planning/ and pipeline/; old directories removed.</done>
</task>

<task type="auto">
  <name>Task 2: Create descriptor/ placeholder package and update frontend/ imports</name>
  <files>
    src/llm_sched/descriptor/__init__.py
    src/llm_sched/frontend/__init__.py
    src/llm_sched/frontend/onnx_importer.py
    src/llm_sched/frontend/nig_lowering.py
    src/llm_sched/frontend/legality.py
    src/llm_sched/__init__.py
  </files>
  <read_first>
    - src/llm_sched/frontend/__init__.py
    - src/llm_sched/frontend/onnx_importer.py
    - src/llm_sched/frontend/nig_lowering.py
    - src/llm_sched/frontend/legality.py
    - src/llm_sched/__init__.py
  </read_first>
  <action>
    1. Create `src/llm_sched/descriptor/__init__.py` as a placeholder:
       ```python
       """Descriptor packing and parsing for v0.10 format.

       Populated in Phase 4.
       """
       ```

    2. Update imports in frontend/ modules to use new flat paths:
       - In `frontend/onnx_importer.py`: replace `from llm_sched.contracts.frontend_import_report import ...` with the appropriate import. Since contracts/ was flattened and frontend_import_report.py was deleted, REMOVE the import and the function that uses it (`build_frontend_import_report`), or stub it out. The executor should read the file and decide: if `build_frontend_import_report` is only called internally and produces a report type that no longer exists, remove the function and its import. Keep `import_onnx_to_graph_ir`.
       - In `frontend/nig_lowering.py`: replace `from llm_sched.contracts.workload_decomposition_report import ...` — the workload_decomposition_report.py was deleted. Remove the import and `build_workload_decomposition_report` function if it depends on deleted types. Keep `lower_graph_ir_to_nig`.
       - In `frontend/legality.py`: replace `from llm_sched.arch.capabilities import ArchitectureCapabilities` with `from llm_sched.arch import ArchitectureCapabilities`.

    3. Rewrite `src/llm_sched/frontend/__init__.py` to export only functions that remain after import cleanup:
       ```python
       """Frontend entrypoints for model import and graph canonicalization."""

       from llm_sched.frontend.binding import bind_nig_ir
       from llm_sched.frontend.canonicalize import canonicalize_graph_ir
       from llm_sched.frontend.legality import (
           FrontendLegalityError,
           FrontendLegalityIssue,
           collect_frontend_legality_issues,
           validate_frontend_legality,
       )
       from llm_sched.frontend.model_metadata import GemmaModelMetadata, load_gemma_model_metadata
       from llm_sched.frontend.nig_lowering import GraphToNIGLoweringError, lower_graph_ir_to_nig
       from llm_sched.frontend.onnx_importer import import_onnx_to_graph_ir
       from llm_sched.frontend.shape_binding import FrontendShapeBinding, build_gemma3_shape_bindings

       __all__ = [
           "FrontendLegalityError",
           "FrontendLegalityIssue",
           "FrontendShapeBinding",
           "GemmaModelMetadata",
           "GraphToNIGLoweringError",
           "bind_nig_ir",
           "build_gemma3_shape_bindings",
           "canonicalize_graph_ir",
           "collect_frontend_legality_issues",
           "import_onnx_to_graph_ir",
           "load_gemma_model_metadata",
           "lower_graph_ir_to_nig",
           "validate_frontend_legality",
       ]
       ```

    4. Update `src/llm_sched/__init__.py` to a minimal package docstring:
       ```python
       """llm_sched v2 — v0.10 descriptor compiler."""
       ```
  </action>
  <verify>
    <automated>
      test -d src/llm_sched/descriptor && echo "OK descriptor dir exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/descriptor/__init__.py && echo "OK descriptor __init__ exists" || (echo "FAIL" && exit 1)
      grep -q "llm_sched.contracts" src/llm_sched/frontend/onnx_importer.py && echo "FAIL frontend has old contracts import" && exit 1 || echo "OK frontend imports clean"
      grep -q "llm_sched.contracts" src/llm_sched/frontend/nig_lowering.py && echo "FAIL nig_lowering has old contracts import" && exit 1 || echo "OK nig_lowering imports clean"
      grep -q "llm_sched.arch.capabilities" src/llm_sched/frontend/legality.py && echo "FAIL legality has old arch import" && exit 1 || echo "OK legality imports clean"
      python3 -c "from llm_sched.frontend import import_onnx_to_graph_ir, lower_graph_ir_to_nig, canonicalize_graph_ir; print('OK frontend imports')"
    </automated>
  </verify>
  <acceptance_criteria>
    - descriptor/ directory exists with __init__.py
    - frontend/onnx_importer.py has no references to llm_sched.contracts
    - frontend/nig_lowering.py has no references to llm_sched.contracts
    - frontend/legality.py imports from llm_sched.arch (not llm_sched.arch.capabilities)
    - `python3 -c "from llm_sched.frontend import import_onnx_to_graph_ir, lower_graph_ir_to_nig, canonicalize_graph_ir"` succeeds
  </acceptance_criteria>
  <done>descriptor/ placeholder created; frontend/ imports updated to new flat paths.</done>
</task>

<task type="auto">
  <name>Task 3: Globally grep and replace old import paths across src/llm_sched/</name>
  <files>
    src/llm_sched/
  </files>
  <read_first>
    - src/llm_sched/scheduler/memory.py
    - src/llm_sched/scheduler/tile.py
    - src/llm_sched/scheduler/dual_core.py
    - src/llm_sched/scheduler/duration.py
    - src/llm_sched/scheduler/reservations.py
    - src/llm_sched/scheduler/frontend.py
    - src/llm_sched/frontend/onnx_importer.py
    - src/llm_sched/frontend/nig_lowering.py
    - src/llm_sched/frontend/legality.py
    - src/llm_sched/frontend/canonicalize.py
    - src/llm_sched/frontend/binding.py
    - src/llm_sched/frontend/model_metadata.py
    - src/llm_sched/frontend/shape_binding.py
  </read_first>
  <action>
    Search across all Python files in src/llm_sched/ for old import paths and update them to new paths. The old paths that must be replaced are:

    | Old path | New path |
    |----------|----------|
    | `from llm_sched.planning.` | `from llm_sched.scheduler.` |
    | `from llm_sched.pipeline.` | `from llm_sched.scheduler.` |
    | `from llm_sched.contracts.` | `from llm_sched.models` |
    | `from llm_sched.config.target_profile` | `from llm_sched.config` |
    | `from llm_sched.config.scenario_profile` | `from llm_sched.config` |
    | `from llm_sched.arch.capabilities` | `from llm_sched.arch` |
    | `from llm_sched.arch.constraints` | `from llm_sched.arch` |
    | `from llm_sched.arch.query_api` | `from llm_sched.arch` |
    | `from llm_sched.ir.graph_ir` | `from llm_sched.ir.graph` |
    | `from llm_sched.ir.schedule_ir` | `from llm_sched.ir.schedule` |

    Use `grep -rn` to find occurrences, then use `sed -i` or direct file edits to update each occurrence. Be careful not to over-replace (e.g., do not replace references inside strings or comments unless they are import statements).

    After all replacements, run the verify command to confirm zero remaining old-path references.
  </action>
  <verify>
    <automated>
      grep -rn "from llm_sched.planning\." src/llm_sched/ && echo "FAIL old planning imports remain" && exit 1 || echo "OK no old planning imports"
      grep -rn "from llm_sched.pipeline\." src/llm_sched/ && echo "FAIL old pipeline imports remain" && exit 1 || echo "OK no old pipeline imports"
      grep -rn "from llm_sched.contracts\." src/llm_sched/ && echo "FAIL old contracts imports remain" && exit 1 || echo "OK no old contracts imports"
      grep -rn "from llm_sched.config\.target_profile" src/llm_sched/ && echo "FAIL old config target_profile imports remain" && exit 1 || echo "OK no old config target_profile imports"
      grep -rn "from llm_sched.config\.scenario_profile" src/llm_sched/ && echo "FAIL old config scenario_profile imports remain" && exit 1 || echo "OK no old config scenario_profile imports"
      grep -rn "from llm_sched.arch\.capabilities" src/llm_sched/ && echo "FAIL old arch capabilities imports remain" && exit 1 || echo "OK no old arch capabilities imports"
      grep -rn "from llm_sched.arch\.constraints" src/llm_sched/ && echo "FAIL old arch constraints imports remain" && exit 1 || echo "OK no old arch constraints imports"
      grep -rn "from llm_sched.arch\.query_api" src/llm_sched/ && echo "FAIL old arch query_api imports remain" && exit 1 || echo "OK no old arch query_api imports"
      grep -rn "from llm_sched.ir\.graph_ir" src/llm_sched/ && echo "FAIL old ir graph_ir imports remain" && exit 1 || echo "OK no old ir graph_ir imports"
      grep -rn "from llm_sched.ir\.schedule_ir" src/llm_sched/ && echo "FAIL old ir schedule_ir imports remain" && exit 1 || echo "OK no old ir schedule_ir imports"
    </automated>
  </verify>
  <acceptance_criteria>
    - Zero occurrences of `from llm_sched.planning.`, `from llm_sched.pipeline.`, `from llm_sched.contracts.` across all Python files in src/llm_sched/
    - Zero occurrences of old config, arch, and ir subpackage imports
  </acceptance_criteria>
  <done>All old import paths globally replaced across src/llm_sched/.</done>
</task>

<task type="auto">
  <name>Task 4: Commit restructure completion</name>
  <files>.git/</files>
  <read_first>
    - git status output from Tasks 1-3
  </read_first>
  <action>
    Stage all changes and commit:

    `git add -A && git commit -m "restructure: create scheduler and descriptor packages, update all imports per D-19"`

    If pre-commit hooks fail, investigate and fix.
  </action>
  <verify>
    <automated>
      git log -1 --oneline | grep -q "restructure: create scheduler and descriptor packages, update all imports per D-19"
    </automated>
  </verify>
  <acceptance_criteria>
    - `git log -1 --oneline` contains "restructure: create scheduler and descriptor packages, update all imports per D-19"
    - `git status` is clean
  </acceptance_criteria>
  <done>Package restructure committed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Working tree -> git index | Moves and edits staged before commit |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03b-01 | Denial of Service | Import breakage | mitigate | Verify all imports with python3 -c "from X import Y" after each move. Global grep ensures no stale imports remain. |
| T-03b-02 | Tampering | File content during move | accept | git mv preserves content; only imports are edited. |
</threat_model>

<verification>
1. scheduler/ has: memory.py, tile.py, dual_core.py, duration.py, reservations.py, frontend.py, __init__.py
2. descriptor/ has: __init__.py
3. frontend/ has current modules with updated imports
4. Old directories (pipeline/, planning/) are absent
5. Zero old import paths remain in src/llm_sched/
6. All python import smoke tests pass
</verification>

<success_criteria>
- src/llm_sched/scheduler/ contains memory.py, tile.py, dual_core.py, duration.py, reservations.py, frontend.py
- src/llm_sched/descriptor/ exists with __init__.py
- src/llm_sched/frontend/ imports use new flat paths
- Old subpackages pipeline/ and planning/ are removed
- No old import paths (planning, pipeline, contracts, old config/arch/ir subpackages) remain in src/llm_sched/
- All import smoke tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-cleanup-foundation/01-03b-SUMMARY.md`
</output>
