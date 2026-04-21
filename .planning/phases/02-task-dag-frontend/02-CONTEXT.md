# Phase 2: Task DAG Frontend - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Given an ONNX model, extract model structure and map it to a task-unit dependency DAG. Graph nodes are identified by macro_op type (attention, GEMM, RMSNorm, GEGLU, element-wise, RoPE, KV load/store). Reshape, transpose, squeeze, unsqueeze, and gather ops are filtered out and not modeled as tasks. The task DAG correctly represents data dependencies between task units.

</domain>

<decisions>
## Implementation Decisions

### Task DAG IR structure
- **D-01:** Create a new `TaskDAG` IR class, separate from NIGIR. NIGIR stays as the "lowered workload graph" and TaskDAG becomes the "execution-ready task graph". This gives clean separation of concerns.
- **D-02:** `TaskDAG` lives in `ir/task_dag.py` with `TaskNode` and `TaskDAG` Pydantic models.
- **D-03:** `TaskNode` fields: `task_id`, `macro_op`, `inputs` (list of `TaskInput` with `source_task_id` and `tensor_name`), `outputs` (list of `TaskOutput` with `tensor_name` and `shape`), `attrs` (dict), `audit_ref` (traceability to original ONNX nodes).
- **D-04:** The existing pipeline (ONNX → GraphIR → NIGIR) stays intact. A new `frontend/task_dag_builder.py` module transforms NIGIR → TaskDAG.

### Layout op transparency
- **D-05:** Reshape, transpose, squeeze, unsqueeze, and gather ops are completely elided from the task DAG. They do not appear as TaskNodes.
- **D-06:** Tensor name rewriting handles the data-flow effects of elided layout ops: if a task's input was produced by a layout op, trace back through the layout-op chain to find the real producer task and wire the dependency directly.
- **D-07:** Layout ops that were classified as `LayoutFallback` or `ShapeHelper` in the canonicalizer are also elided — they are not compute tasks.

### Dependency edge modeling
- **D-08:** Dependencies are explicit via `TaskInput` objects that reference `source_task_id` (the task that produces the tensor) and `tensor_name`. No implicit string matching required to traverse the DAG.
- **D-09:** The TaskDAG includes a `edges` property (derived) that returns adjacency information for topological sorting and graph traversal.
- **D-10:** Constants and weights are represented as tasks with `macro_op="Constant"` so that all data dependencies are uniform (no special-case handling for initializers).

### Macro_op mapping
- **D-11:** Phase 2 uses the existing macro_op labels from NIG lowering (GEMM, WDQ_GEMM, RMSNORM, RMSNORM_GEMM, SDPA, SDPA_DECODE, GEGLU, ROPE, KVSTORE, KVLOAD, EMBEDDING_LOOKUP, ELEM_ADD, etc.).
- **D-12:** Mapping macro_ops to v0.10 descriptor families is deferred to Phase 4. The task DAG stays agnostic to descriptor format details.

### Layer boundaries
- **D-13:** The task DAG is a flat graph of compute tasks with dependencies. No layer grouping or boundary detection in Phase 2.
- **D-14:** Layer grouping is a scheduler concern (Phase 3). The scheduler will partition the task DAG into layers based on execution semantics and memory planning.

### Task DAG validation
- **D-15:** The frontend validates DAG properties before emitting: acyclic (via topological sort check), all input tensors resolve to a producer task, no orphaned tasks (except graph outputs).
- **D-16:** Validation failures raise a `TaskDAGBuildError` with diagnostic information (orphaned tensors, cycle paths, missing producers).

### Input/Output handling
- **D-17:** Graph inputs (model inputs) are represented as `TaskNode` with `macro_op="Input"` so downstream tasks have explicit dependencies on them.
- **D-18:** Graph outputs are tracked in `TaskDAG.output_tasks` (the set of tasks whose outputs are graph outputs).

### Claude's Discretion
- Exact Pydantic field names and types for TaskNode/TaskDAG
- Specific implementation of tensor name rewriting for elided layout ops
- Exact error message format in TaskDAGBuildError
- Whether to cache derived properties (edges, topological order) on the TaskDAG instance

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project requirements and scope
- `.planning/PROJECT.md` — Vision, constraints, key decisions, and out-of-scope table
- `.planning/REQUIREMENTS.md` — FRONT-01 through FRONT-03 requirements and traceability
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, and dependencies

### Prior phase context
- `.planning/phases/01-cleanup-foundation/01-CONTEXT.md` — Package structure decisions (D-19), IR retention decisions, CLI shape

### Existing frontend code (to retain and extend)
- `src/llm_sched/frontend/onnx_importer.py` — ONNX import logic (stays)
- `src/llm_sched/frontend/canonicalize.py` — Canonicalization logic (stays)
- `src/llm_sched/frontend/nig_lowering.py` — NIG lowering with macro_op identification (stays)
- `src/llm_sched/ir/graph_ir.py` — GraphIR schema (stays)
- `src/llm_sched/ir/nig.py` — NIGIR schema (stays)
- `src/llm_sched/ir/schedule_ir.py` — ScheduleIR schema (reference for dependency modeling patterns)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GraphIR` / `GraphNode` (in `ir/graph_ir.py`) — Core data structure for ONNX frontend; stays intact
- `NIGIR` / `NIGNode` (in `ir/nig.py`) — Already has macro_op, inputs, outputs, shape, dtype; serves as input to TaskDAG builder
- `nig_lowering.py` — Already maps canonical ops to macro_ops (GEMM, RMSNORM, SDPA, etc.); no changes needed
- `canonicalize.py` — Already fuses layout ops into higher-level patterns (KVLoad, KVStore); some layout ops become LayoutFallback/ShapeHelper
- `ScheduleIR` / `ScheduleBlock` (in `ir/schedule_ir.py`) — Reference for explicit dependency modeling via `depends_on` list pattern
- `AuditRef` (in `ir/common.py`) — Reusable traceability structure

### Established Patterns
- Pydantic v2 `BaseModel` with `ConfigDict(extra="forbid")` used throughout IR schemas
- IR serialization via `model_dump(mode="json")` pattern
- Pipeline functions return result objects with `status: Literal["completed", "failed"]` and `diagnostics` list
- Frontend pipeline: `import_onnx_to_graph_ir()` → `canonicalize_graph_ir()` → `lower_graph_ir_to_nig()` → (new) `build_task_dag()`

### Integration Points
- `frontend/task_dag_builder.py` (new) consumes `NIGIR` and produces `TaskDAG`
- `frontend/` → `ir/nig.py` → `ir/task_dag.py` → `scheduler/` (Phase 3)
- The new `compile` CLI command (from Phase 1, D-09) will call the full pipeline through task DAG generation
</code_context>

<specifics>
## Specific Ideas

- The task DAG should be a "pure" compute graph — every node represents work the NPU must do
- Layout ops are transparent; their only effect is tensor shape/layout changes that the NPU handles implicitly
- Explicit edges make the DAG traversable without string dictionary lookups
- Keep the existing ONNX → GraphIR → NIGIR pipeline intact; add NIGIR → TaskDAG as a new stage
</specifics>

<deferred>
## Deferred Ideas

- Mapping macro_ops to v0.10 descriptor families — Phase 4
- Layer boundary detection and grouping — Phase 3
- Memory class and layout annotations on tasks — Phase 3 (scheduler adds these)
- Quant binding propagation — Phase 3
- Task-to-core assignment — Phase 3

</deferred>

---

*Phase: 02-task-dag-frontend*
*Context gathered: 2026-04-22*
