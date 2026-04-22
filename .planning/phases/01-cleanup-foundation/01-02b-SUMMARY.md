# Plan 01-02b Summary: IR, Contracts, and Config Cleanup

## Objective
Delete IR modules, flatten contracts to models.py, and remove config loader. Verify no retained modules reference deleted paths.

## What Was Done

- Deleted `ir/descriptor_ir.py` and `ir/analysis_ir.py`
- Rewrote `ir/validators.py` to remove descriptor_ir and analysis_ir validators
- Rewrote `ir/__init__.py` to export retained IR types
- Created `contracts/models.py` by flattening manifest, artifact_layout, run_summary, memory_plan, tiling_plan
- Included `Diagnostic` class in models.py (formerly in config.loader) since RunSummary and pipeline result classes depend on it
- Deleted all old contract files (33 files)
- Rewrote `contracts/__init__.py` to export from models.py
- Deleted `config/loader.py`
- Rewrote `config/__init__.py` to export only TargetProfile and ScenarioProfile
- Updated all retained planning and pipeline modules to import from `llm_sched.contracts.models` instead of deleted contract submodules
- Updated all retained modules to import from `llm_sched.config` instead of `llm_sched.config.target_profile` / `llm_sched.config.scenario_profile`
- Updated retained modules to import from `llm_sched.arch` instead of `llm_sched.arch.capabilities`
- Removed deleted `analysis_ir` and report-type dependencies from `pipeline/frontend_analysis.py`
- Moved helper functions from deleted `planning/single_core_scheduler.py` into `planning/dual_core_scheduler.py`

## Commits

- `4f54a09` — cleanup: remove v0.9-era ir, contracts, config modules; flatten contracts to models.py

## Self-Check

- [x] descriptor_ir.py and analysis_ir.py deleted
- [x] validators.py has no references to DescriptorIR, AnalysisIR
- [x] ir/__init__.py exports retained types
- [x] models.py exists and contains classes from all five kept contract files
- [x] No old contract files remain
- [x] config/loader.py deleted
- [x] No retained Python file imports from descriptor_ir, analysis_ir, config.loader, or old contracts submodules
- [x] `git status` is clean

## Deviations

- `Diagnostic` class was moved into `contracts/models.py` rather than being deleted, because `RunSummary` and all pipeline result classes (`FrontendAnalysisResult`, `MemoryPlanningResult`, `DualCoreSchedulingResult`, `TilePlanningResult`) use it for their `diagnostics` field.
- `pipeline/frontend_analysis.py` had significant report-generation code removed along with the deleted report-type imports, since the entire module will be rewritten in Phase 2.
- Helper functions from deleted `planning/single_core_scheduler.py` were appended to `planning/dual_core_scheduler.py` to keep the dual-core scheduler implementation intact.
