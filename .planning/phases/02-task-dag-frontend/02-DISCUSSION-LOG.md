# Phase 2: Task DAG Frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 2-task-dag-frontend
**Areas discussed:** Task DAG IR structure, Layout op transparency, Dependency edge modeling, Macro_op mapping, Layer boundaries, Task DAG validation, Input/Output handling

---

## Task DAG IR structure

| Option | Description | Selected |
|--------|-------------|----------|
| New TaskDAG class | Create separate `TaskDAG` IR in `ir/task_dag.py`, distinct from NIGIR | ✓ |
| Extend NIGIR | Add dependency edges and task DAG methods directly to NIGIR | |
| Reuse ScheduleIR | Adapt existing ScheduleIR as the task DAG representation | |

**User's choice:** New TaskDAG class (auto-selected — recommended default)
**Notes:** NIGIR carries scheduling-specific baggage (quant bindings, memory class, layout, legal_opcodes). A clean TaskDAG focused on compute tasks and dependencies provides better separation of concerns. ScheduleIR is too scheduling-specific (blocks, barriers, cores, durations).

---

## Layout op transparency

| Option | Description | Selected |
|--------|-------------|----------|
| Completely elide | Remove layout ops from DAG; rewrite tensor dependencies to skip over them | ✓ |
| Pass-through tasks | Represent layout ops as TaskNodes with a special "no-op" macro_op | |
| Keep in DAG | Include layout ops as regular tasks and let scheduler ignore them | |

**User's choice:** Completely elide (auto-selected — recommended default)
**Notes:** FRONT-03 explicitly says "do not model them as tasks." Eliding them and rewriting tensor dependencies matches the constraint that these ops are "transparent to NPU execution." The canonicalizer already fuses some layout ops into higher-level patterns; remaining ones classified as LayoutFallback or ShapeHelper should also be removed.

---

## Dependency edge modeling

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit edge objects | TaskInput references source_task_id and tensor_name directly | ✓ |
| Implicit tensor matching | Keep tensor-name-based dependency resolution (like NIGIR) | |
| Adjacency list only | Store edges separately from task nodes | |

**User's choice:** Explicit edge objects (auto-selected — recommended default)
**Notes:** Explicit edges make the DAG structure machine-traversable without string dictionary lookups. This aligns with ScheduleIR's `depends_on` pattern but is more complete (includes tensor names). Derived adjacency list available as property.

---

## Macro_op mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend maps to families | Phase 2 assigns v0.10 descriptor family to each task | |
| Frontend stays agnostic | Phase 2 uses macro_op labels; Phase 4 maps to families | ✓ |

**User's choice:** Frontend stays agnostic (auto-selected — recommended default)
**Notes:** Family mapping is a descriptor packing concern. The frontend should not know about v0.10 descriptor format details. Existing macro_op labels from NIG lowering (GEMM, RMSNORM, SDPA, etc.) are sufficient.

---

## Layer boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend detects layers | TaskDAG includes explicit layer grouping | |
| Scheduler handles layers | TaskDAG is flat; Phase 3 partitions into layers | ✓ |

**User's choice:** Scheduler handles layers (auto-selected — recommended default)
**Notes:** Layer grouping depends on execution ordering and memory planning, which are scheduling concerns. A flat task DAG is more flexible and correct.

---

## Task DAG validation

| Option | Description | Selected |
|--------|-------------|----------|
| Strict validation | Validate acyclic, connected, all inputs resolve before emitting | ✓ |
| Lenient validation | Allow partial/invalid DAGs with warnings | |
| No validation | Trust upstream; validate only in scheduler | |

**User's choice:** Strict validation (auto-selected — recommended default)
**Notes:** The frontend should guarantee structural correctness before passing to scheduler. Fail fast with `TaskDAGBuildError` containing diagnostic info.

---

## Input/Output handling

| Option | Description | Selected |
|--------|-------------|----------|
| Tasks for inputs/outputs | Represent graph inputs as Input tasks and track output tasks | ✓ |
| Special-case inputs | Keep inputs as external references, not tasks | |

**User's choice:** Tasks for inputs/outputs (auto-selected — recommended default)
**Notes:** Uniform handling — all data dependencies point to tasks. Graph inputs become Input tasks; graph outputs are tracked in `TaskDAG.output_tasks`.

---

## Claude's Discretion

- Exact Pydantic field names and types for TaskNode/TaskDAG
- Specific implementation of tensor name rewriting for elided layout ops
- Exact error message format in TaskDAGBuildError
- Whether to cache derived properties (edges, topological order) on the TaskDAG instance

## Deferred Ideas

- Mapping macro_ops to v0.10 descriptor families — Phase 4
- Layer boundary detection and grouping — Phase 3
- Memory class and layout annotations on tasks — Phase 3
- Quant binding propagation — Phase 3
- Task-to-core assignment — Phase 3
