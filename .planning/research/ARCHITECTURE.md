# Architecture Patterns: NPU Descriptor Compiler (v0.10)

**Domain:** NPU descriptor compiler for transformer LLM workloads
**Researched:** 2026-04-21
**Confidence:** HIGH (based on direct codebase analysis and authoritative schema files)

---

## 1. Recommended Architecture

### 1.1 Core Principle

The compiler is a **single-direction dataflow pipeline** with four conceptual tiers:

```
ONNX Model  →  Task DAG  →  Scheduled Tasks  →  Verified Descriptor Set
     |              |              |                    |
  Frontend    Task-Centric    Scheduling        Descriptor
  (keep)        (new)          (rewrite)         (new)
```

Each tier consumes the output of the previous tier and produces a typed, serializable IR. There is no feedback loop from descriptors back to scheduling, and no additive diagnosis/visualization layers post-compilation. The only "downstream" output beyond descriptors is structural metrics and per-layer timelines.

### 1.2 Component Map

```
+-------------------+     +-------------------+     +-------------------+     +-------------------+
|   ONNX Frontend   | --> |   Task DAG Builder | --> |  Task Scheduler   | --> | Descriptor Engine |
|   (refactored)    |     |   (new)            |     |  (rewritten)      |     |   (new)           |
+-------------------+     +-------------------+     +-------------------+     +-------------------+
        |                         |                         |                         |
   GraphIR                 TaskDAGIR               ScheduleIR             DescriptorSetIR
   (existing)              (new Pydantic)          (existing shape,      (new Pydantic)
                                                      new semantics)
```

---

## 2. Component Boundaries

### 2.1 ONNX Frontend (REFACTOR — keep structure, change output)

**Responsibility:** Parse ONNX, canonicalize patterns, emit a task-centric dependency graph instead of node-centric NIG.

**Location:** `src/llm_sched/frontend/`

**What to keep:**
- `onnx_importer.py` — ONNX parsing and GraphIR generation is validated and correct.
- `canonicalize.py` — Pattern fusion (MatMul+Add→Linear, RMSNorm fusion, GeGLU, RoPE, SDPA, etc.) is the product of extensive work. Keep the fusion logic.

**What to change:**
- `nig_lowering.py` — Currently lowers canonical GraphIR into NIG (node-centric with stages: dma_in, prepare, compute, store). Replace with a **TaskDAG builder** that emits one task node per macro_op, not one schedule block per stage. Layout ops (Reshape, Transpose, Squeeze, Unsqueeze, Gather) are filtered out, not modeled.
- `binding.py` / `shape_binding.py` — Keep shape binding logic. Adapt to bind shapes at the task level rather than the NIG node level.

**Boundary contract:**
- **Input:** ONNX model file path + shape bindings
- **Output:** `TaskDAGIR` (new IR) — a Pydantic model containing task nodes with dependency edges, shapes, and task family assignments
- **Does NOT talk to:** scheduler, memory planner, descriptor engine directly. Only via serialized IR.

### 2.2 Task DAG Builder (NEW)

**Responsibility:** Transform canonical GraphIR into a task-centric dependency DAG where each node is an executable task (one of 11 families), and edges are data dependencies.

**Location:** `src/llm_sched/ir/task_dag_ir.py` + `src/llm_sched/frontend/task_dag_builder.py`

**Key design decisions:**
- One task node = one descriptor (eventually). No more dma_in/prepare/compute/store sub-stages per node.
- Task families map 1:1 to the 11 v0.10 families: RMSNORM, WDQ_GEMM, SDPA, SDPA_DECODE, GEMM, ELEM_ADD, GEGLU, ROPE, KVLOAD, KVSTORE, RMSNORM_GEMM.
- Filter out reshape, transpose, squeeze, unsqueeze, gather ops per requirement FRONT-03. These are transparent to NPU execution.
- Each task node carries: task_type_id, input/output tensor refs, resolved shapes, quantization params, attention binding (if applicable), and dependency edges.

**Boundary contract:**
- **Input:** Canonical GraphIR
- **Output:** `TaskDAGIR`
- **Talks to:** No other components at build time. Consumes GraphIR only.

### 2.3 Task Scheduler (REWRITE)

**Responsibility:** Take a task-centric DAG and produce a linear execution order with dependency resolution, core assignment (single/dual), and relative timing.

**Location:** `src/llm_sched/planning/task_scheduler.py` (new), replacing `single_core_scheduler.py` and `dual_core_scheduler.py`

**What to keep from existing scheduler:**
- The dependency resolution algorithm (topological sort with priority heap) is sound.
- Resource reservation timeline logic (`schedule_reservations.py`, `schedule_duration.py`) can be adapted.

**What to rewrite:**
- The existing scheduler operates on NIG nodes and expands each into 3-4 stage blocks (dma_in, prepare, compute, store). The new scheduler operates on **tasks** directly. Each task is a single schedulable unit.
- Memory planning must be rewritten to operate on the task DAG (SCHED-01), not the NIG. The existing memory planner (`memory_planner.py`) allocates per-node-stage and uses ping-pong regions. The new planner should allocate buffers per task's input/output operands.
- Tile planning (`tile_planner.py`) should be retained but adapted to operate on task nodes rather than NIG nodes. The candidate generation and ranking logic is correct.

**Boundary contract:**
- **Input:** `TaskDAGIR` + `MemoryPlan` + `TilingPlan`
- **Output:** `ScheduleIR` (reuse existing schema shape, but `blocks` now represent tasks not stages)
- **Talks to:** Memory planner (via `MemoryPlan` artifact), Tile planner (via `TilingPlan` artifact)

### 2.4 Descriptor Engine (NEW)

**Responsibility:** Convert scheduled tasks into v0.10 descriptor bitstreams, verify round-trip correctness, and output structural metrics.

**Location:** `src/llm_sched/descriptor/` (new package)

**Sub-components:**

#### 2.4.1 Schema Layer (`schema.py`)
- Load and validate `family_lut.yaml`, `field_tables.yaml`, `layout.yaml` at import time.
- Provide programmatic access to field definitions, bit widths, valid ranges, and must-be-zero positions.
- Single source of truth for all descriptor structure knowledge.

#### 2.4.2 Semantic Builder (`semantic_builder.py`)
- Input: one scheduled task + its memory allocation + tiling info
- Output: a semantic descriptor representation (plain Python dataclass or Pydantic model) with fields like `task_type_id`, `m`, `n`, `k`, `tile_m`, buffers list, loop slots, template slots.
- Family-specific logic lives here: GEMM interprets `family_mode` as `accum_dtype`; KVSTORE interprets `primary_surface_slot` as `primary_input_surface`.

#### 2.4.3 Encoder (`encoder.py`)
- Input: semantic descriptor
- Output: list of 64-bit words (Python ints)
- Implements bitfield packing per `field_tables.yaml`
- Computes CRC-16/CCITT-FALSE over all words

#### 2.4.4 Parser (`parser.py`)
- Input: list of 64-bit words
- Output: semantic descriptor
- Mechanical reverse of encoder. Used for verification.

#### 2.4.5 Verifier (`verifier.py`)
- Four verification layers per DESC-06:
  1. **Structural:** record lengths match primary_header derivation
  2. **Reserved-bit:** all must-be-zero positions are zero
  3. **Semantic:** field values are in valid ranges per family LUT
  4. **Round-trip:** `pack(parse(pack(task))) == pack(task)` (bit-exact)

#### 2.4.6 Metrics Collector (`metrics.py`)
- Input: descriptor set
- Output: per-layer and full-graph metrics (descriptor count, total words, bit-field utilization, timeline)

**Boundary contract:**
- **Input:** `ScheduleIR` + `TaskDAGIR` + `MemoryPlan`
- **Output:** `DescriptorSetIR` (new) + verification report + metrics report
- **Talks to:** No upstream components. Self-contained after scheduling.

### 2.5 IR Layer (ADAPT)

**Responsibility:** Typed, versioned, serializable representations at every pipeline boundary.

**Location:** `src/llm_sched/ir/`

**What to keep:**
- `common.py` — `AuditRef` pattern is correct and should be preserved for traceability.
- `graph_ir.py` — Keep as-is.
- `io.py` — JSON serialization utilities.

**What to add:**
- `task_dag_ir.py` — New IR for task-centric DAG. Replaces `nig.py` as the primary mid-level IR.

**What to remove:**
- `nig.py` — Remove after TaskDAGIR is stable. NIG is node-centric with stage decomposition; the new model is task-centric.
- `descriptor_ir.py` — Remove. The old descriptor IR models v0.9 512-bit fixed-layout descriptors with packing profiles. The new format is variable-length v0.10.
- `analysis_ir.py` — Remove with diagnosis layer.
- `schedule_ir.py` — Keep the schema shape but adapt semantics (blocks = tasks, not stages).

### 2.6 Contracts Layer (PRUNE)

**Responsibility:** Pydantic schemas for artifacts, reports, and manifest structures.

**Location:** `src/llm_sched/contracts/`

**What to keep:**
- `manifest.py` — Run manifest tracking artifact_index.
- `artifact_layout.py` — Directory layout builder.
- `memory_plan.py` — Memory allocation contracts (adapt to task-centric).
- `tiling_plan.py` — Tile candidate contracts.
- `run_summary.py` — Execution summary.

**What to remove:**
- All diagnosis-related contracts (`diagnosis_*.py`)
- All visualization-related contracts (`visualization_*.py`)
- All evaluation/report contracts (`prefill_report.py`, `decode_report.py`, `sweep_report.py`, `roofline_report.py`, etc.)
- `isa_coverage_report.py` — Replace with descriptor verification report.
- `packed_descriptor_bundle.py` — Replace with new v0.10 bundle contract.

### 2.7 Pipeline Layer (REWRITE)

**Responsibility:** Run-root workflow implementations that load artifacts, invoke builders/planners, and persist results.

**Location:** `src/llm_sched/pipeline/`

**What to keep:**
- The pattern of one workflow module per phase, consuming prior artifacts, producing new ones, updating manifest.
- Error handling pattern (try/except at workflow boundary, diagnostics in run-summary).

**What to rewrite:**
- `frontend_analysis.py` — Adapt to emit TaskDAGIR instead of bound NIG.
- `memory_planning.py` — Rewrite to operate on TaskDAGIR.
- `tile_planning.py` — Adapt to TaskDAGIR.
- `single_core_scheduling.py` / `dual_core_scheduling.py` — Merge into a unified `task_scheduling.py`.
- `descriptor_generation.py` — Rewrite to use new descriptor engine.
- Remove all other pipeline modules (evaluation, diagnosis, visualization, sweep, performance_estimation).

### 2.8 CLI Layer (ADAPT)

**Responsibility:** User-facing entrypoints and orchestration.

**Location:** `src/llm_sched/cli/main.py`

**What to change:**
- Remove commands for deleted phases (evaluation, diagnosis, visualization, sweep).
- Add commands for new phases (task-dag-build, descriptor-verify).
- Keep profile loading and run initialization.

### 2.9 Config & Architecture Layers (KEEP)

**Responsibility:** Target/scenario profile loading and hardware capability modeling.

**Location:** `src/llm_sched/config/`, `src/llm_sched/arch/`

**What to keep:**
- `config/loader.py`, `target_profile.py`, `scenario_profile.py` — Keep entirely.
- `arch/capabilities.py`, `constraints.py`, `query_api.py` — Keep entirely. The hardware abstraction is correct and independent of descriptor format.

---

## 3. Data Flow

### 3.1 Compile Flow (v2)

```
1. init-run
   → creates run directory with manifest.json

2. run-frontend-analysis
   → loads ONNX model
   → produces graph_ir.json → canonical_graph_ir.json
   → NEW: produces task_dag_ir.json
   → (no more nig_ir.json, bound_nig_ir.json)

3. run-memory-planning
   → consumes task_dag_ir.json
   → produces memory_plan.json

4. run-tile-planning
   → consumes task_dag_ir.json + memory_plan.json
   → produces tiling_plan.json

5. run-task-scheduling
   → consumes task_dag_ir.json + memory_plan.json + tiling_plan.json
   → produces schedule_ir.json
   → (single workflow for both single-core and dual-core)

6. run-descriptor-generation
   → consumes schedule_ir.json + task_dag_ir.json + memory_plan.json
   → produces descriptor_set.json (semantic view)
   → produces descriptor_bundle.bin (packed bitstreams)
   → produces verification_report.json
   → produces metrics_report.json
   → (no more performance_estimation, evaluation, diagnosis)
```

### 3.2 Artifact Index (manifest.json)

```json
{
  "graph_ir": "artifacts/graph_ir.json",
  "canonical_graph_ir": "artifacts/canonical_graph_ir.json",
  "task_dag_ir": "artifacts/task_dag_ir.json",
  "memory_plan": "artifacts/memory_plan.json",
  "tiling_plan": "artifacts/tiling_plan.json",
  "schedule_ir": "artifacts/schedule_ir.json",
  "descriptor_set": "artifacts/descriptor_set.json",
  "descriptor_bundle": "artifacts/descriptor_bundle.bin",
  "verification_report": "reports/verification_report.json",
  "metrics_report": "reports/metrics_report.json"
}
```

### 3.3 State Management

- Run state remains file-system based.
- Each phase reads from and writes JSON artifacts to a run-root directory.
- `manifest.json` tracks artifact_index.
- `run-summary.json` tracks completion status and diagnostics per phase.
- No in-memory shared state across phases; phases are independently invokable.
- **This pattern is correct and should be preserved.**

---

## 4. Suggested Build Order

The build order is driven by dependency chains: downstream components need upstream IR schemas to be stable.

### Phase 1: Foundation (Cleanup + Schema)

1. **CLEAN-01/02/03** — Delete old code, archive docs, update README
2. **Schema layer** — Implement `task_dag_ir.py`, new `descriptor_set_ir.py`, prune contracts
3. **Descriptor schema loader** — Load YAML specs into validated Python structures

**Rationale:** You cannot build the descriptor engine without knowing the IR it consumes. You cannot build the task scheduler without knowing the task DAG schema.

### Phase 2: Frontend Refactor

4. **Task DAG builder** — Replace NIG lowering with task-centric DAG extraction
5. **Frontend integration** — Wire task DAG builder into frontend analysis pipeline

**Rationale:** The task DAG is the pivot point. Everything downstream depends on it. The frontend canonicalization is already correct; only the lowering layer changes.

### Phase 3: Planning Rewrite

6. **Memory planner (task-centric)** — Rewrite to allocate per-task operands instead of per-node-stage
7. **Tile planner (adapted)** — Adapt existing tile planner to task DAG nodes
8. **Task scheduler** — Rewrite single/dual-core schedulers into unified task scheduler

**Rationale:** Memory planning must precede scheduling because scheduling needs to know buffer bindings. Tile planning is independent of memory but scheduling needs tile candidates.

### Phase 4: Descriptor Engine

9. **Semantic builder** — Map scheduled tasks to family-specific semantic descriptors
10. **Encoder** — Pack semantic descriptors into v0.10 bitstreams with CRC
11. **Parser** — Decode bitstreams back to semantic descriptors
12. **Verifier** — Implement 4-layer verification gate

**Rationale:** The encoder and parser are mechanical inverses; build them together. The verifier needs both. The semantic builder is the creative layer that maps task semantics to family fields.

### Phase 5: Integration & Metrics

13. **Pipeline workflows** — Wire all phases into run-root workflows
14. **Metrics collector** — Structural metrics and timeline output
15. **CLI** — Expose new commands, remove old ones
16. **End-to-end runner** — Update to orchestrate new phase sequence

**Rationale:** Integration must come after all components exist. Metrics are trivial once descriptors are generated.

### Phase 6: Verification Hardening

17. **Round-trip tests for all 11 families**
18. **Reserved-bit tests**
19. **Semantic range tests**
20. **Full-model smoke tests**

---

## 5. What to Keep vs Rewrite

| Component | Decision | Rationale |
|-----------|----------|-----------|
| ONNX importer | **Keep** | Validated, correct, no format change |
| Canonicalization | **Keep** | Extensive pattern fusion work; correct |
| GraphIR | **Keep** | Unchanged schema |
| NIG lowering | **Replace** | Node-centric stage decomposition is wrong abstraction for v0.10 |
| NIG IR | **Remove** | Replaced by TaskDAGIR |
| Memory planner | **Rewrite** | Must operate on task-centric DAG, not node-stage-centric NIG |
| Tile planner | **Adapt** | Candidate generation logic is correct; change input from NIG to TaskDAG |
| Single-core scheduler | **Rewrite** | Must schedule tasks not stages |
| Dual-core scheduler | **Rewrite** | Same reason; merge into unified scheduler |
| Descriptor builder | **Replace** | Models v0.9 512-bit fixed layout; v0.10 is variable-length flat structure |
| Descriptor packer | **Replace** | Same reason |
| Descriptor IR | **Replace** | v0.9 schema incompatible with v0.10 |
| Analysis layer | **Remove** | Diagnosis, visualization, evaluation out of scope |
| Pipeline workflows | **Rewrite** | Phase sequence changes; many phases deleted |
| CLI | **Adapt** | Remove deleted phase commands; add new ones |
| Config layer | **Keep** | Profile loading is correct and independent |
| Arch capabilities | **Keep** | Hardware abstraction is correct |
| Contracts layer | **Prune** | Remove diagnosis/visualization/evaluation contracts |
| Manifest / artifact layout | **Keep** | Run tracking pattern is correct |
| AuditRef traceability | **Keep** | Cross-layer debugging is essential |

---

## 6. Key Abstractions for v2

### 6.1 TaskDAGIR (new)

```python
class TaskNode(BaseModel):
    task_id: str
    task_type_id: int  # 1-11 per family_lut.yaml
    family: str  # "gemm", "sdpa", etc.
    inputs: list[str]
    outputs: list[str]
    resolved_shape: list[int]
    tile_shape: tuple[int, int, int] | None
    quant: QuantBinding
    attention: AttentionBinding | None
    depends_on: list[str]  # task_id dependencies
    audit_ref: AuditRef

class TaskDAGIR(BaseModel):
    ir_version: str
    graph_id: str
    tasks: list[TaskNode]
```

### 6.2 DescriptorSetIR (new)

```python
class SemanticDescriptor(BaseModel):
    descriptor_id: str
    task_id: str
    primary_header: PrimaryHeader
    family: FamilyRecord  # family-specific semantic view
    buffers: list[BufferRecord]
    loop: LoopRecord | None
    template: TemplateRecord | None
    crc16: int

class DescriptorSetIR(BaseModel):
    ir_version: str
    graph_id: str
    descriptors: list[SemanticDescriptor]
```

### 6.3 VerificationReport (new)

```python
class VerificationReport(BaseModel):
    graph_id: str
    total_descriptors: int
    structural_pass: int
    reserved_bit_pass: int
    semantic_pass: int
    round_trip_pass: int
    failures: list[VerificationFailure]
```

---

## 7. Scalability Considerations

| Concern | Approach |
|---------|----------|
| Model size (1B to 70B params) | Task count scales with layer count, not parameter count. Descriptor count is O(layers). Frontend and scheduler handle this naturally. |
| Descriptor set size | Each layer produces a bounded number of descriptors (typically 3-8). A 100-layer model produces ~300-800 descriptors. Memory footprint is trivial. |
| Verification time | Round-trip verification is O(descriptors). Parallelizable per descriptor. Expected <1s for full model. |
| YAML schema loading | Load once at module import time. Cached. Negligible overhead. |

---

## 8. Anti-Patterns to Avoid

### 8.1 Keeping the old stage-based abstraction

The existing code models each compute node as 3-4 stage blocks (dma_in, prepare, compute, store). v0.10 descriptors are **task-centric**: one descriptor per task. Attempting to map the old stage model onto v0.10 will produce incorrect descriptors with wrong buffer counts and missing family semantics.

**Instead:** Collapse stages into tasks at the DAG level. The scheduler orders tasks. The descriptor engine packs one descriptor per task.

### 8.2 Hard-coding family field layouts

The v0.10 format has family-specific field semantics, variable-length FAMILY records (2 or 3 words), and repurposed slots (e.g., `primary_surface_slot` means `primary_input_surface` for KVSTORE). Hard-coding these in if/else chains is error-prone and unmaintainable.

**Instead:** Drive all family-specific logic from the YAML schema files (`family_lut.yaml`, `field_tables.yaml`). The semantic builder should look up field mappings dynamically.

### 8.3 Reusing the old DescriptorIR / packing profile abstraction

The existing `DescriptorIR` models a 512-bit fixed-layout descriptor with `packing_profile`, `field_layout`, and `field_widths`. v0.10 uses a flat variable-length word stream with mechanically derivable record lengths.

**Instead:** Replace with a semantic-first model: build the semantic descriptor, then encode. Do not carry forward the packing profile concept.

### 8.4 Preserving the analysis/diagnosis pipeline "just in case"

The project requirements explicitly remove diagnosis, visualization, and evaluation. Keeping this code creates maintenance burden and confuses the architecture.

**Instead:** Delete it. Git history preserves it if needed later.

---

## 9. Sources

- `/home/ubuntu/llmSched/.planning/PROJECT.md` — Project requirements and constraints
- `/home/ubuntu/llmSched/.planning/codebase/ARCHITECTURE.md` — Existing architecture analysis
- `/home/ubuntu/llmSched/docs/descriptor/descriptor-handoff.md` — Controller parsing contract
- `/home/ubuntu/llmSched/docs/descriptor/family_lut.yaml` — Authoritative family schema
- `/home/ubuntu/llmSched/docs/descriptor/field_tables.yaml` — Authoritative field definitions
- `/home/ubuntu/llmSched/docs/descriptor/layout.yaml` — Authoritative layout rules
- `/home/ubuntu/llmSched/src/llm_sched/ir/descriptor_ir.py` — Existing v0.9 descriptor IR
- `/home/ubuntu/llmSched/src/llm_sched/ir/schedule_ir.py` — Existing schedule IR
- `/home/ubuntu/llmSched/src/llm_sched/ir/nig.py` — Existing NIG IR
- `/home/ubuntu/llmSched/src/llm_sched/planning/descriptor_builder.py` — Existing descriptor builder
- `/home/ubuntu/llmSched/src/llm_sched/planning/descriptor_packer.py` — Existing descriptor packer
- `/home/ubuntu/llmSched/src/llm_sched/planning/memory_planner.py` — Existing memory planner
- `/home/ubuntu/llmSched/src/llm_sched/planning/single_core_scheduler.py` — Existing scheduler
- `/home/ubuntu/llmSched/src/llm_sched/frontend/nig_lowering.py` — Existing NIG lowering
- `/home/ubuntu/llmSched/src/llm_sched/frontend/canonicalize.py` — Existing canonicalization
