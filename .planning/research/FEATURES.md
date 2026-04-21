# Feature Landscape: NPU Descriptor Compiler (v0.10)

**Domain:** Fixed-format hardware descriptor compiler for LLM inference on NPU
**Researched:** 2026-04-21
**Confidence:** HIGH (based on authoritative spec docs, existing codebase analysis, and PROJECT.md requirements)

---

## Table Stakes

Features users (the NPU controller team, integration engineers) expect. Missing = compiler is useless.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **ONNX model ingestion** | Sole input format per requirement; existing validated frontend | Low | Already validated in codebase (`frontend/onnx_importer.py`). Must be retained. |
| **Task DAG extraction from ONNX** | Controller executes tasks, not ONNX nodes; need semantic mapping | Medium | Existing NIG lowering does this. Must refactor from node-centric to task-centric. |
| **11-family descriptor packing** | Controller only speaks v0.10; every task must emit a valid descriptor | High | Core value of the compiler. Variable-length FAMILY (2/3 words), BUFFER (4 words), LOOP (1-2 words), TEMPLATE (0-4 words). |
| **CRC-16/CCITT-FALSE generation** | Wire-level integrity check required by controller parser | Low | Standard algorithm (poly 0x1021, init 0xFFFF). Must zero crc field during computation. |
| **Round-trip verification gate** | Pack -> Parse -> Pack must produce identical bit pattern | Medium | The spec defines this as the correctness contract. Any mismatch = VIOLATION. |
| **4-layer verification** | Structural + reserved-bit + semantic + round-trip per v0.10 spec | Medium | Structural: word counts match derivation. Reserved-bit: all reserved bits zero. Semantic: fields in range, task_type_id valid. Round-trip: bit-exact identity. |
| **Dispatch-first semantic resolution** | `family_mode`, surface slots, and repurposed fields have per-family meaning | Medium | Parser must NOT interpret `family_mode` until `task_type_id` is read. Non-owning families must leave slot at 0x0. |
| **Per-family must-be-zero enforcement** | 7-10 inactive field positions per family; any non-zero = VIOLATION | Medium | Documented exhaustively in `family_lut.yaml`. Compiler must zero all inactive fields. |
| **Memory planning (task-centric)** | BUFFER records need valid address_space, span, base_binding, strides | High | Existing memory planner is node-centric. Must rewrite to operate on task DAG. |
| **Scheduling (task-level ordering)** | Descriptors execute in order; dependencies resolve via dep_mask/signal_mask | High | Existing scheduler produces schedule blocks per node stage. Must map to task-level descriptor ordering with dependency resolution. |
| **Descriptor set output (grouped by layer)** | Controller consumes descriptor sets, not individual descriptors | Low | One descriptor per task, grouped by model layer. |

## Differentiators

Features that set a high-quality descriptor compiler apart. Not strictly required for correctness, but valued by the integration team.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Schema-driven code generation** | Machine-readable YAML specs (`family_lut.yaml`, `field_tables.yaml`, `layout.yaml`) drive encoder/decoder instead of hand-written per-family logic | Medium | Reduces bug surface when spec evolves. Existing codebase has no schema-driven generation. |
| **Deterministic/reproducible output** | Same ONNX + config always produces identical descriptor bitstream | Low | Critical for debugging hardware issues. Existing packer already aims for this. |
| **Bit-field utilization metrics** | Report how densely packed the descriptors are (active vs reserved bits) | Low | Helps hardware team assess format efficiency. Listed as PERF-03 requirement. |
| **Per-layer execution timeline** | Ordered task list per layer with relative timing | Low | Helps integration team understand execution flow. Listed as PERF-04 requirement. |
| **ISA coverage gap reporting** | When a model contains ops that cannot map to any of the 11 families, report exactly what is missing | Low | Existing `ISACoverageReport` does this. Should be retained. |
| **Multi-core dependency mask generation** | Automatic derivation of `dep_mask` and `signal_mask` for single-core vs dual-core schedules | Medium | Existing dual-core scheduler has barrier logic. Must map to per-descriptor bit masks. |
| **Template slot auto-generation** | Derive TEMPLATE action slots (load/compute/store) from task stage and resource set | Medium | Currently manual or absent in existing code. v0.10 requires TEMPLATE for many families. |
| **Loop record auto-generation** | Derive LOOP dimensions and tile sizes from tiling plan | Medium | Existing tile planner produces candidates. Must map to LOOP record slots. |
| **Validation at every IR layer** | GraphIR -> NIGIR -> ScheduleIR -> DescriptorIR each have Pydantic validators | Low | Already exists. Retain and extend for v0.10 constraints. |

## Anti-Features

Features to explicitly NOT build. These existed in v0.9 codebase and are being removed.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Old v0.9 descriptor format support** | New controller only speaks v0.10 | Single code path for v0.10 only. Delete v0.9 packer logic. |
| **Diagnosis reports and workbenches** | Out of scope per requirement | Only execution semantics remain. Delete all diagnosis/analysis/report builders. |
| **Visualization builders and catalogs** | Out of scope per requirement | Delete visualization pipeline entirely. |
| **Prefill/decode evaluation reports (cycle-level)** | Out of scope per requirement | Only structural descriptor metrics (count, length, utilization). No cycle estimation. |
| **Sweep analysis and compare** | Out of scope per requirement | Delete sweep pipeline. |
| **Roofline analysis** | Removed with evaluation layer | Do not implement. |
| **Reshape/Transpose/Squeeze/Unsqueeze/Gather task modeling** | Explicitly excluded; these are layout ops, not compute tasks | Filter them during ONNX -> task DAG extraction. Do not emit descriptors for them. |
| **Performance estimation (cycle-level)** | Out of scope for v2 | Only output structural metrics: descriptor count, total length, bit-field utilization. |
| **Multi-run catalog/compare** | Removed with visualization layer | Do not implement. |
| **Primary/continuation descriptor distinction** | v0.10 uses flat structure | Flatten everything. No continuation records. |
| **Explicit total_record_count / per_record_length fields** | v0.10 derives all lengths mechanically | Do not emit these fields. Derive lengths from task_type_id, buffer_count, loop_rank, template_slot_count. |

## Feature Dependencies

```
ONNX ingestion
    -> Graph canonicalization
        -> Task DAG extraction (macro_op identification)
            -> Memory planning (task-centric)
                -> Tile planning
                    -> Scheduling (single-core / dual-core)
                        -> Descriptor packing (v0.10)
                            -> CRC-16 generation
                            -> Round-trip verification
                                -> 4-layer verification gate

Schema-driven generation (optional differentiator)
    -> Family LUT YAML parsing
        -> Auto-generated encoder/decoder per family
            -> Must-be-zero enforcement
            -> Dispatch-first semantic resolution
```

## MVP Recommendation

Prioritize (in order):

1. **ONNX ingestion + task DAG extraction** — Foundation everything else builds on.
2. **11-family v0.10 descriptor packing** — The core deliverable. Must handle all variable-length records correctly.
3. **CRC-16 + round-trip gate** — The correctness contract. Without this, descriptors cannot be trusted.
4. **4-layer verification** — Catches bugs early; required by spec.
5. **Memory planning (task-centric)** — BUFFER records need valid addresses.
6. **Scheduling (task-level)** — Determines descriptor ordering and dependency masks.

Defer:
- **Schema-driven code generation**: Nice to have, but hand-written per-family logic is acceptable for 11 families. Can be retrofitted later.
- **Bit-field utilization metrics**: Easy to add once packing works. Listed as PERF requirement but not blocking.
- **Template slot auto-generation**: Many families do not require TEMPLATE (template_slot_count=0). Can start with manual or empty TEMPLATE.

## Sources

- `/home/ubuntu/llmSched/.planning/PROJECT.md` — Requirements and scope definitions
- `/home/ubuntu/llmSched/docs/descriptor/descriptor-encoding-layout.md` — v0.10 format specification (authoritative)
- `/home/ubuntu/llmSched/docs/descriptor/descriptor-family-lut.md` — Per-family field mappings (authoritative)
- `/home/ubuntu/llmSched/docs/descriptor/layout.yaml` — Machine-readable layout schema
- `/home/ubuntu/llmSched/docs/descriptor/family_lut.yaml` — Machine-readable family schema
- `/home/ubuntu/llmSched/docs/descriptor/field_tables.yaml` — Machine-readable field tables
- `/home/ubuntu/llmSched/src/llm_sched/planning/descriptor_packer.py` — Existing v0.9 packer (to be removed)
- `/home/ubuntu/llmSched/src/llm_sched/planning/descriptor_builder.py` — Existing descriptor builder (to be refactored)
- `/home/ubuntu/llmSched/src/llm_sched/ir/descriptor_ir.py` — Existing DescriptorIR schema
- `/home/ubuntu/llmSched/tests/unit/planning/test_descriptor_packer.py` — Existing packer tests
