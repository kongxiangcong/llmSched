---
phase: 01-cleanup-foundation
status: gaps_found
verified_at: 2026-04-22T00:00:00Z
score: 3/4 success criteria verified
overrides_applied: 0
gaps:
  - truth: "The only remaining pipeline in src/ is ONNX -> task DAG -> scheduling -> descriptor packing"
    status: partial
    reason: "scheduler/frontend.py has undefined references (load_target_profile, load_scenario_profile, FrontendLegalityReport, FrontendBindingReport, FrontendBindingIssue, MacroBindingSummary) and imports build_frontend_import_report/build_workload_decomposition_report from frontend/__init__.py where they are not exported. scheduler/__init__.py imports run_frontend_analysis from the broken scheduler/frontend.py, making the entire scheduler package unimportable via 'from llm_sched.scheduler import ...'. The core scheduler submodules (dual_core, memory, tile, duration, reservations) import correctly when bypassing __init__.py."
    artifacts:
      - path: "src/llm_sched/scheduler/frontend.py"
        issue: "References undefined functions load_target_profile, load_scenario_profile and undefined classes FrontendLegalityReport, FrontendBindingReport, FrontendBindingIssue, MacroBindingSummary"
      - path: "src/llm_sched/scheduler/__init__.py"
        issue: "Imports run_frontend_analysis from broken scheduler/frontend.py, causing entire package import to fail"
      - path: "src/llm_sched/frontend/__init__.py"
        issue: "Does not export build_frontend_import_report or build_workload_decomposition_report, but scheduler/frontend.py tries to import them from here"
    missing:
      - "Add load_target_profile and load_scenario_profile functions (or remove their usage from scheduler/frontend.py)"
      - "Add FrontendLegalityReport, FrontendBindingReport, FrontendBindingIssue, MacroBindingSummary class definitions to models.py or scheduler/frontend.py"
      - "Either export build_frontend_import_report and build_workload_decomposition_report from frontend/__init__.py, or change scheduler/frontend.py to import them directly from their modules"
      - "Or remove scheduler/frontend.py and its export from scheduler/__init__.py if it is not intended to be part of the v2 execution-semantic pipeline"
---

# Phase 1: Cleanup & Foundation Verification Report

**Phase Goal:** Clean codebase ready for v2 development; only execution-semantic pipeline remains
**Verified:** 2026-04-22
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Success Criteria from ROADMAP)

| #   | Truth                                                                 | Status     | Evidence |
| --- | --------------------------------------------------------------------- | ---------- | -------- |
| 1   | `src/` contains no old descriptor generation, workbench, diagnosis, visualization, or report-generation code | VERIFIED   | All 9 old directories absent (analysis, visualization, tools, cli, config, arch, contracts, pipeline, planning). Zero old import paths remain. No v0.9-era module references in src/. |
| 2   | `docs/development/` and `docs/architecture-diagnosis/` are archived or deleted | VERIFIED   | Both directories absent from working tree. docs/plans/ also absent. |
| 3   | README clearly states the project is undergoing complete refactoring and current outputs are not correct | VERIFIED   | README.md contains warning banner, "6 phases" roadmap, no Chinese text, no SPEC/M1/M2 refs, no diagnosis/visualization/sweep/compare/evaluation reports refs. pyproject.toml has numpy>=1.26, requires-python>=3.11, entrypoint llm_sched.cli:run. |
| 4   | The only remaining pipeline in `src/` is ONNX -> task DAG -> scheduling -> descriptor packing | PARTIAL    | Package structure is correct (frontend/, ir/, scheduler/, descriptor/). Core scheduler modules work. BUT scheduler/frontend.py is broken (undefined refs) and scheduler/__init__.py fails to import, breaking the scheduler package surface. |

**Score:** 3/4 success criteria verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/llm_sched/cli.py` | Single compile command CLI | VERIFIED | Exactly one command "compile". Validates .onnx extension, config exists, creates output dir. No old commands. |
| `src/llm_sched/config.py` | TargetProfile + ScenarioProfile | VERIFIED | Imports successfully. Contains all profile classes. |
| `src/llm_sched/arch.py` | Simplified hardware model | VERIFIED | Imports successfully. Contains ArchitectureCapabilities. |
| `src/llm_sched/models.py` | Flattened Pydantic schemas | VERIFIED | Imports successfully. Contains MemoryPlanArtifact, TilingPlanArtifact, RunManifest, RunSummary, FrontendImportReport, WorkloadDecompositionReport. |
| `src/llm_sched/ir/graph.py` | Graph IR | VERIFIED | Renamed from graph_ir.py. Imports successfully. |
| `src/llm_sched/ir/schedule.py` | Schedule IR | VERIFIED | Renamed from schedule_ir.py. Imports successfully. |
| `src/llm_sched/ir/nig.py` | NIG IR | VERIFIED | Imports successfully. |
| `src/llm_sched/ir/validators.py` | IR validators | VERIFIED | No descriptor_ir or analysis_ir references. Exports validate_graph_ir, validate_nig_ir, validate_schedule_ir. |
| `src/llm_sched/scheduler/__init__.py` | Clean scheduler exports | BROKEN | Imports run_frontend_analysis from broken scheduler/frontend.py. Causes entire package import to fail. |
| `src/llm_sched/scheduler/dual_core.py` | Dual-core scheduler | VERIFIED | Imports successfully when bypassing __init__.py. |
| `src/llm_sched/scheduler/memory.py` | Memory planner | VERIFIED | Imports successfully when bypassing __init__.py. |
| `src/llm_sched/scheduler/tile.py` | Tile planner | VERIFIED | Imports successfully when bypassing __init__.py. |
| `src/llm_sched/scheduler/duration.py` | Schedule duration | VERIFIED | Imports successfully when bypassing __init__.py. |
| `src/llm_sched/scheduler/reservations.py` | Reservation helpers | VERIFIED | Imports successfully when bypassing __init__.py. |
| `src/llm_sched/scheduler/frontend.py` | Frontend analysis workflow | BROKEN | Undefined functions and classes. Cannot be imported. |
| `src/llm_sched/descriptor/__init__.py` | Placeholder package | VERIFIED | Exists with placeholder docstring. |
| `src/llm_sched/frontend/__init__.py` | Clean frontend exports | PARTIAL | Does not export build_frontend_import_report or build_workload_decomposition_report, but those functions exist in submodules and are importable directly. |
| `tests/test_cleanup_verification.py` | Cleanup verification test | VERIFIED | 5/5 tests pass. |
| `README.md` | v2 README | VERIFIED | Warning banner, 6-phase roadmap, no legacy content. |
| `pyproject.toml` | Updated metadata | VERIFIED | Correct entrypoint, numpy dependency, minimal pytest config. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `scheduler/dual_core.py` | `arch.py` | `from llm_sched.arch import ...` | VERIFIED | Import works |
| `scheduler/memory.py` | `models.py` | `from llm_sched.models import ...` | VERIFIED | Import works |
| `frontend/legality.py` | `arch.py` | `from llm_sched.arch import ...` | VERIFIED | Import works |
| `scheduler/frontend.py` | `frontend/__init__.py` | `from llm_sched.frontend import ...` | BROKEN | Tries to import build_frontend_import_report and build_workload_decomposition_report which are not exported from frontend/__init__.py |
| `scheduler/__init__.py` | `scheduler/frontend.py` | `from llm_sched.scheduler.frontend import run_frontend_analysis` | BROKEN | Cascades from broken scheduler/frontend.py |

### Data-Flow Trace (Level 4)

Not applicable for cleanup phase — no dynamic data rendering artifacts to trace.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Cleanup verification tests pass | `python3 -m pytest tests/test_cleanup_verification.py -v` | 5 passed | PASS |
| CLI has only compile command | `python3 -c "from llm_sched.cli import app; print({cmd.name for cmd in app.registered_commands})"` | `{'compile'}` | PASS |
| Config imports work | `python3 -c "from llm_sched.config import TargetProfile, ScenarioProfile"` | OK | PASS |
| Arch imports work | `python3 -c "from llm_sched.arch import ArchitectureCapabilities"` | OK | PASS |
| Models imports work | `python3 -c "from llm_sched.models import MemoryPlanArtifact, TilingPlanArtifact"` | OK | PASS |
| IR imports work | `python3 -c "from llm_sched.ir import GraphIR, NIGIR, ScheduleIR"` | OK | PASS |
| Scheduler package import | `python3 -c "from llm_sched.scheduler import plan_dual_core_schedule"` | ImportError | FAIL |
| Scheduler submodules import | Direct import of dual_core, memory, tile, duration, reservations | OK | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| CLEAN-01 | 01-01, 01-02a, 01-02b, 01-03a, 01-03b, 01-06 | Remove all old descriptor generation, workbench, diagnosis, visualization, and report-generation implementations from `src/` | SATISFIED | All old directories and files deleted. Zero old import paths remain. |
| CLEAN-02 | 01-01 | Archive or delete `docs/development/` and `docs/architecture-diagnosis/` content | SATISFIED | Both directories absent. |
| CLEAN-03 | 01-05 | Update README to state the project is undergoing complete refactoring and current outputs are not correct | SATISFIED | README contains warning banner and all required content. |
| CLEAN-04 | 01-02a, 01-02b, 01-03a, 01-03b, 01-04, 01-06 | Retain only execution-semantic pipeline (ONNX -> task DAG -> scheduling -> descriptor packing) | PARTIAL | Structure is correct but scheduler/frontend.py is broken and scheduler/__init__.py is unimportable. Core scheduler modules (dual_core, memory, tile, duration, reservations) work correctly. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/llm_sched/scheduler/frontend.py` | 56-57 | Calls undefined functions `load_target_profile`, `load_scenario_profile` | Blocker | Module cannot be imported |
| `src/llm_sched/scheduler/frontend.py` | 158, 163, 173, 185, 201, 209 | References undefined classes `FrontendLegalityReport`, `FrontendBindingReport`, `FrontendBindingIssue`, `MacroBindingSummary` | Blocker | Module cannot be imported |
| `src/llm_sched/scheduler/frontend.py` | 16-26 | Imports `build_frontend_import_report` and `build_workload_decomposition_report` from `llm_sched.frontend` where they are not exported | Blocker | Module cannot be imported |
| `src/llm_sched/scheduler/__init__.py` | 5 | Imports `run_frontend_analysis` from broken `scheduler/frontend.py` | Blocker | Entire scheduler package is unimportable |
| `src/llm_sched/cli.py` | 28-29 | Compile command is a stub (echo only) | Info | Expected — Phase 2 will wire actual logic |
| `src/llm_sched/descriptor/__init__.py` | 1-4 | Placeholder docstring only | Info | Expected — Phase 4 will populate |

### Human Verification Required

None — all verifiable items have been checked programmatically.

### Gaps Summary

Phase 1 cleanup achieved its structural goals: old v0.9-era code is removed, directories are deleted, imports are cleaned, README is rewritten, CLI is simplified, and tests pass. However, one file — `src/llm_sched/scheduler/frontend.py` — was moved from `pipeline/frontend_analysis.py` during restructuring but retains v0.9-era dependencies (manifest-based run-root infrastructure, report types that no longer exist, config loader functions that were deleted). This file is imported by `scheduler/__init__.py`, making the entire scheduler package unimportable via its public surface.

The core scheduler modules (`dual_core.py`, `memory.py`, `tile.py`, `duration.py`, `reservations.py`) are intact and importable individually. The gap is specifically in the moved `frontend.py` module and the `__init__.py` that re-exports it.

**Recommended fix:** Either (a) remove `scheduler/frontend.py` and its export from `scheduler/__init__.py` since the frontend workflow belongs in Phase 2, or (b) fix the undefined references and import paths in `scheduler/frontend.py` to make it compatible with the v2 package structure.

---

_Verified: 2026-04-22_
_Verifier: Claude (gsd-verifier)_
