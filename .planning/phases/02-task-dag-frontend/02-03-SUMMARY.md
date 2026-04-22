---
phase: 02-task-dag-frontend
plan: 03
subsystem: frontend
tags: [pydantic, task-dag, validation, kahn-algorithm, topological-sort]

# Dependency graph
requires:
  - phase: 02-task-dag-frontend
    provides: TaskDAG IR schema (TaskDAG, TaskNode, TaskInput, TaskOutput) and NIG-to-TaskDAG builder from plans 02-01 and 02-02
provides:
  - validate_task_dag() function with acyclic, missing-producer, and orphaned-task checks
  - Pydantic @model_validator validate_input_references on TaskDAG
  - Automatic validation at end of build_task_dag()
  - Comprehensive unit tests for TaskDAG IR schema and builder validation
  - Frontend and IR module exports wired correctly
affects:
  - 03-scheduler (TaskDAG validation must pass before scheduler consumes it)
  - 04-descriptor-engine (relies on valid TaskDAG as input)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic model_validator(mode='after') for cross-field validation"
    - "Kahn's algorithm for topological sort / cycle detection in DAGs"
    - "TaskDAGBuildError with diagnostics list for structured failure reporting"

key-files:
  created:
    - tests/unit/ir/test_task_dag.py
  modified:
    - src/llm_sched/ir/task_dag.py
    - src/llm_sched/frontend/task_dag_builder.py
    - src/llm_sched/frontend/__init__.py
    - tests/unit/frontend/test_task_dag_builder.py

key-decisions:
  - "Edges property semantics: maps consumer -> list of producers (dependencies), not producer -> consumers"
  - "Orphan detection uses Input/Constant tasks as reachability seeds; build_task_dag auto-creates these, so orphan check is primarily a safety net for manually constructed DAGs"
  - "Missing source_task_id is caught at two levels: Pydantic construction-time validator (validate_input_references) and runtime validate_task_dag() for post-mutation checks"

patterns-established:
  - "Dual-layer validation: Pydantic model validators catch schema violations at construction time; explicit validate_* functions catch semantic violations after mutation"
  - "Diagnostic-rich exceptions: TaskDAGBuildError carries a list of specific failure strings for precise debugging"

requirements-completed: [FRONT-01, FRONT-02, FRONT-03]

# Metrics
duration: 4min
completed: 2026-04-22
---

# Phase 2 Plan 03: TaskDAG Validation and Integration Summary

**TaskDAG hardened with Kahn's algorithm acyclic check, input-reference validation, orphaned-task detection, and 20 unit tests across IR schema and builder**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-22T15:11:49Z
- **Completed:** 2026-04-22T15:16:19Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `validate_task_dag()` with three correctness checks: missing producer references, cycle detection via Kahn's algorithm, and orphaned-task reachability analysis
- Added Pydantic `@model_validator(mode="after") validate_input_references` to `TaskDAG` for construction-time input reference validation
- Wired automatic `validate_task_dag()` call at the end of `build_task_dag()`
- Created `tests/unit/ir/test_task_dag.py` with 7 tests covering serialization, edges property, duplicate ID rejection, missing source rejection, defaults, round-trip, and IR-level validator
- Appended 5 validation tests to `tests/unit/frontend/test_task_dag_builder.py` covering acyclic pass, cycle detection, orphaned task detection, direct validator call, and error diagnostics
- Verified frontend and IR module exports include all TaskDAG builder and type symbols

## Task Commits

Each task was committed atomically:

1. **Task 1: Add validation logic to task_dag_builder.py and task_dag.py** - `7a42c47` (feat)
2. **Task 2: Create test files for TaskDAG IR schema and builder validation** - `5ffa6d2` (test)
3. **Task 3: Wire TaskDAG builder into frontend pipeline exports** - no commit needed (exports already correct from prior plans)

## Files Created/Modified

- `src/llm_sched/ir/task_dag.py` - Added `validate_input_references` Pydantic model validator
- `src/llm_sched/frontend/task_dag_builder.py` - Added `validate_task_dag()` function with acyclic, missing-producer, and orphaned-task checks; wired into `build_task_dag()`
- `src/llm_sched/frontend/__init__.py` - Added `validate_task_dag` to imports and `__all__`
- `tests/unit/ir/test_task_dag.py` - 7 tests for TaskDAG IR schema (new file)
- `tests/unit/frontend/test_task_dag_builder.py` - 5 additional validation tests appended to existing file

## Decisions Made

- Edges property semantics confirmed: maps consumer -> list of producers (dependency direction). Test expectation corrected accordingly.
- Orphan detection is a safety net for manually constructed DAGs; `build_task_dag` auto-creates Input/Constant tasks for all consumed tensors, making natural orphans impossible.
- Two-layer validation approach: Pydantic catches construction-time issues; `validate_task_dag` catches post-mutation issues.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test expectation for edges property direction**
- **Found during:** Task 2 (writing IR schema tests)
- **Issue:** Test expected `edges == {"task.a": ["task.b"]}` (producer -> consumers), but actual semantics are consumer -> producers
- **Fix:** Updated test expectation to `{"task.a": [], "task.b": ["task.a"]}` and added clarifying comment
- **Files modified:** `tests/unit/ir/test_task_dag.py`
- **Verification:** `pytest tests/unit/ir/test_task_dag.py` passes
- **Committed in:** `5ffa6d2` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed orphaned task test to use manually constructed DAG**
- **Found during:** Task 2 (writing builder validation tests)
- **Issue:** Attempted to make `build_task_dag` produce an orphan via NIGIR, but builder auto-creates Input/Constant tasks for all consumed tensors, so orphans are impossible in normal operation
- **Fix:** Changed test to construct invalid TaskDAG directly and call `validate_task_dag()`, bypassing the builder
- **Files modified:** `tests/unit/frontend/test_task_dag_builder.py`
- **Verification:** `pytest tests/unit/frontend/test_task_dag_builder.py` passes
- **Committed in:** `5ffa6d2` (Task 2 commit)

**3. [Rule 1 - Bug] Fixed diagnostics test to bypass Pydantic construction-time validator**
- **Found during:** Task 2 (writing builder validation tests)
- **Issue:** Test attempted to create TaskDAG with invalid `source_task_id` at construction time, but new Pydantic validator rejects this before `validate_task_dag` can run
- **Fix:** Construct valid TaskDAG first, then mutate `inputs` list directly to inject invalid reference
- **Files modified:** `tests/unit/frontend/test_task_dag_builder.py`
- **Verification:** `pytest tests/unit/frontend/test_task_dag_builder.py` passes
- **Committed in:** `5ffa6d2` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 - bugs in test expectations/construction)
**Impact on plan:** All auto-fixes were test-level corrections. No implementation changes beyond what the plan specified.

## Issues Encountered

None - all issues were test expectation mismatches discovered and resolved during test writing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TaskDAG builder is validated and ready for scheduler consumption
- All frontend exports are wired correctly
- No blockers for Phase 3 (Scheduler)

---
*Phase: 02-task-dag-frontend*
*Completed: 2026-04-22*
