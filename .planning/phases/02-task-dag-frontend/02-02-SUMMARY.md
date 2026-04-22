---
phase: 2
plan: "02-02"
subsystem: "frontend"
tags: ["task-dag", "nigir", "builder", "transformation"]
dependency_graph:
  requires: ["02-01"]
  provides: ["02-03", "SCHED-01"]
  affects: ["FRONT-01", "FRONT-02", "FRONT-03"]
tech_stack:
  added: []
  patterns: ["NIGIR producer map", "tensor rewrite chain", "elided-node tracing"]
key_files:
  created:
    - "src/llm_sched/frontend/task_dag_builder.py"
    - "tests/unit/frontend/test_task_dag_builder.py"
  modified:
    - "src/llm_sched/frontend/__init__.py"
decisions:
  - "Layout ops (LAYOUT_FALLBACK, SHAPE_HELPER, ATTENTION_MASK_PREP) are elided at the TaskDAG level, not modeled as tasks"
  - "Graph inputs and constants get explicit Input/Constant task nodes so the scheduler sees all tensor producers"
  - "output_tasks inferred from tensors produced but never consumed (no explicit NIGIR output list)"
metrics:
  duration: "~10 min"
  completed_date: "2026-04-22"
---

# Phase 2 Plan 02-02: Task DAG Builder — NIGIR to TaskDAG Transformation Summary

## One-liner

Implemented `frontend/task_dag_builder.py` that transforms NIGIR into TaskDAG by eliding layout ops, tracing tensor dependencies through elided chains, and wiring graph inputs and constants as explicit task nodes.

## What Was Built

- **`src/llm_sched/frontend/task_dag_builder.py`** — Core builder module:
  - `TaskDAGBuildError` exception with diagnostics support
  - `_ELIDED_MACRO_OPS` constant defining layout ops to elide
  - `build_task_dag(nig_ir, graph_input_names)` — main transformation function
  - `_resolve_tensor_name()` — follows rewrite chains through elided nodes
  - `_find_non_elided_producer()` — traces back through elided producers
  - `_sanitize_tensor_name()` — creates valid task IDs from tensor names

- **`tests/unit/frontend/test_task_dag_builder.py`** — 8 comprehensive unit tests

- **`src/llm_sched/frontend/__init__.py`** — exports `build_task_dag` and `TaskDAGBuildError`

## Task Execution Log

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Implement TaskDAG builder with elision, tracing, Input/Constant tasks, output_tasks inference | `9c1cb62` | `src/llm_sched/frontend/task_dag_builder.py`, `src/llm_sched/frontend/__init__.py` |
| 2 | Add 8 unit tests covering compute ops, elision, inputs, constants, chain tracing, outputs, audit_ref, attrs | `d03d7c3` | `tests/unit/frontend/test_task_dag_builder.py` |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- [x] `src/llm_sched/frontend/task_dag_builder.py` exists
- [x] `tests/unit/frontend/test_task_dag_builder.py` exists
- [x] `src/llm_sched/frontend/__init__.py` exports builder
- [x] Commit `9c1cb62` exists
- [x] Commit `d03d7c3` exists
- [x] All 8 pytest tests pass
- [x] `python -m py_compile` passes for both files
- [x] Imports work from package and direct module
