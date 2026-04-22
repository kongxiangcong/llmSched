---
phase: 02-task-dag-frontend
plan: 02-01
subsystem: ir

tags: [pydantic-v2, task-dag, ir-schema]

requires:
  - phase: 01-cleanup
    provides: Clean src/ with existing IR modules (common.py, graph.py, nig.py, schedule.py)

provides:
  - TaskDAG Pydantic v2 schema with TaskInput, TaskOutput, TaskNode, TaskDAG models
  - Adjacency-list edges property on TaskDAG
  - Unique task_id validation via model_validator
  - Package-level exports in ir/__init__.py

affects:
  - 02-02 (TaskDAG Builder — consumes these types)
  - 03-scheduling (Scheduler — consumes TaskDAG as input)

tech-stack:
  added: []
  patterns:
    - "Pydantic v2 BaseModel with ConfigDict(extra='forbid') for all IR types"
    - "AuditRef default_factory pattern for traceability"
    - "model_validator(mode='after') for cross-field validation"
    - "@property for derived adjacency list from explicit input dependencies"

key-files:
  created:
    - src/llm_sched/ir/task_dag.py
  modified:
    - src/llm_sched/ir/__init__.py

key-decisions:
  - "TaskInput uses explicit source_task_id + tensor_name rather than opaque tensor id, making dataflow explicit at the IR level"
  - "TaskOutput carries shape as list[int] to preserve tensor metadata for downstream scheduling"
  - "edges property is derived from inputs (not stored) to prevent inconsistency"

patterns-established:
  - "IR schema files live in src/llm_sched/ir/ with module-per-schema naming"
  - "All IR models use ConfigDict(extra='forbid') to catch field typos early"
  - "Container models (TaskDAG) validate structural invariants (unique IDs) at construction time"

requirements-completed:
  - FRONT-01

metrics:
  duration: 5min
  completed: 2026-04-22
---

# Phase 2 Plan 02-01: TaskDAG IR Schema Summary

**TaskDAG intermediate representation with explicit tensor-level dependencies, unique-task validation, and derived adjacency edges, exported as Pydantic v2 models.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-22T00:00:00Z
- **Completed:** 2026-04-22T00:05:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Created `TaskInput`, `TaskOutput`, `TaskNode`, and `TaskDAG` Pydantic v2 models in `src/llm_sched/ir/task_dag.py`
- `TaskDAG` validates unique `task_id`s via `@model_validator(mode="after")`
- `TaskDAG.edges` property returns adjacency list mapping each task to its dependency task IDs
- Updated `ir/__init__.py` to export all new types
- All acceptance criteria verified: py_compile, grep checks, and runtime import tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create TaskDAG IR schema** - `f246545` (feat)

## Files Created/Modified

- `src/llm_sched/ir/task_dag.py` - TaskDAG IR schema: TaskInput, TaskOutput, TaskNode, TaskDAG
- `src/llm_sched/ir/__init__.py` - Added exports for TaskDAG, TaskInput, TaskNode, TaskOutput

## Decisions Made

- Followed existing IR patterns from `graph.py`, `nig.py`, and `schedule.py` for consistency
- Used `Field(default_factory=list)` and `Field(default_factory=dict)` for mutable defaults
- Used `Field(default_factory=AuditRef)` for audit_ref to match NIGNode/GraphNode pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `python` executable not found on system; used `python3` instead for py_compile and runtime checks. No impact on deliverables.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TaskDAG schema is ready for Plan 02-02 (TaskDAG Builder) to construct instances from ONNX graphs
- Scheduler (Phase 3) can depend on these types for its input contract

## Self-Check: PASSED

- [x] `src/llm_sched/ir/task_dag.py` exists
- [x] `src/llm_sched/ir/__init__.py` modified
- [x] Commit `f246545` exists in git log
- [x] All acceptance criteria verified

---
*Phase: 02-task-dag-frontend*
*Completed: 2026-04-22*
