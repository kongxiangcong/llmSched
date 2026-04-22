---
phase: 01-cleanup-foundation
plan: 03a
subsystem: infra
tags: [pydantic, typer, python-packaging, git-mv]

requires:
  - phase: 01-02a
    provides: "Contracts/models flattened in Plan 02b"
  - phase: 01-02b
    provides: "Old pipeline and planning modules removed"
provides:
  - "Flat domain files at package root: cli.py, config.py, arch.py, models.py"
  - "Renamed IR modules: graph.py, schedule.py"
  - "Clean package layout without old subpackages"
affects:
  - "01-03b"
  - "01-04"
  - "Phase 2 frontend work"

tech-stack:
  added: []
  patterns:
    - "Flat domain modules at package root instead of nested subpackages"
    - "Pydantic v2 BaseModel with ConfigDict(extra='forbid')"
    - "git mv for rename history preservation"

key-files:
  created:
    - "src/llm_sched/cli.py"
    - "src/llm_sched/config.py"
    - "src/llm_sched/arch.py"
    - "src/llm_sched/models.py"
  modified:
    - "src/llm_sched/ir/__init__.py"
    - "src/llm_sched/ir/validators.py"
    - "src/llm_sched/ir/graph.py (renamed from graph_ir.py)"
    - "src/llm_sched/ir/schedule.py (renamed from schedule_ir.py)"

key-decisions:
  - "Merged config/scenario_profile.py and config/target_profile.py into single config.py"
  - "Merged arch/capabilities.py, arch/constraints.py, arch/query_api.py into single arch.py"
  - "Used git mv for graph_ir.py→graph.py and schedule_ir.py→schedule.py to preserve history"

patterns-established:
  - "Flat root modules: domain concepts live as top-level .py files, not subpackages"
  - "Import path simplification: from llm_sched.config import TargetProfile instead of from llm_sched.config.target_profile"

requirements-completed:
  - CLEAN-01
  - CLEAN-04

# Metrics
duration: 2min
completed: 2026-04-22
---

# Phase 1 Plan 03a: Flat Domain Files and IR Renames Summary

**Flat domain modules (cli.py, config.py, arch.py, models.py) at package root and IR file renames (graph_ir.py→graph.py, schedule_ir.py→schedule.py) per D-19**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-22T00:08:49Z
- **Completed:** 2026-04-22T00:11:06Z
- **Tasks:** 2 (Task 3 was a combined commit instruction; tasks 1 and 2 were committed individually per executor protocol)
- **Files modified:** 12

## Accomplishments
- Created flat domain files at package root by merging old subpackage contents
- Removed old subpackages: cli/, config/, arch/, contracts/
- Renamed IR modules graph_ir.py→graph.py and schedule_ir.py→schedule.py with git mv
- Updated all internal imports to use new flat paths
- All import smoke tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create flat domain files at package root** - `8a0f84f` (feat)
2. **Task 2: Rename and restructure ir/ modules** - `3a8cb09` (refactor)

## Files Created/Modified
- `src/llm_sched/cli.py` - Minimal Typer CLI stub for Plan 04
- `src/llm_sched/config.py` - Merged TargetProfile and ScenarioProfile schemas
- `src/llm_sched/arch.py` - Merged ArchitectureCapabilities, constraints, and query API
- `src/llm_sched/models.py` - Flattened Pydantic schemas (moved from contracts/models.py)
- `src/llm_sched/ir/graph.py` - Renamed from graph_ir.py
- `src/llm_sched/ir/schedule.py` - Renamed from schedule_ir.py
- `src/llm_sched/ir/__init__.py` - Updated exports for renamed modules
- `src/llm_sched/ir/validators.py` - Updated imports for renamed modules

## Decisions Made
- Followed D-19 flat package structure decision from context
- Merged multi-file subpackages into single root modules to reduce import complexity
- Preserved git history on renamed IR files via git mv

## Deviations from Plan

### Task 3 Deviation

The plan's Task 3 specified a single combined commit: "git add -A && git commit -m 'restructure: create flat root files and rename ir modules per D-19'". Per the executor protocol, each task is committed atomically. Tasks 1 and 2 were committed individually, which achieves the same end state with better granularity. No functional deviation.

**Total deviations:** 0
**Impact on plan:** None — same end state, better commit granularity.

## Issues Encountered
- Import smoke tests initially failed because llm_sched package is not installed; resolved by setting PYTHONPATH=/home/ubuntu/llmSched/src

## Known Stubs

| File | Line | Description | Reason |
|------|------|-------------|--------|
| `src/llm_sched/cli.py` | 5-10 | Minimal Typer app with no commands | Full CLI implementation deferred to Plan 04 |

## Threat Flags

No new security-relevant surface introduced.

## Next Phase Readiness
- Package root layout is clean and ready for downstream Plan 03b (scheduler/ and descriptor/ creation)
- All import paths are stable
- No blockers

## Self-Check: PASSED

- [x] `src/llm_sched/cli.py` exists
- [x] `src/llm_sched/config.py` exists and exports TargetProfile, ScenarioProfile
- [x] `src/llm_sched/arch.py` exists and exports ArchitectureCapabilities, ArchitectureQueryAPI
- [x] `src/llm_sched/models.py` exists and exports MemoryPlanArtifact, TilingPlanArtifact
- [x] `src/llm_sched/ir/graph.py` exists
- [x] `src/llm_sched/ir/schedule.py` exists
- [x] Old subpackages cli/, config/, arch/, contracts/ removed
- [x] Commits 8a0f84f and 3a8cb09 exist in git log
- [x] All import smoke tests pass

---
*Phase: 01-cleanup-foundation*
*Completed: 2026-04-22*
