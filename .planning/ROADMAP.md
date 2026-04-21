# Roadmap: llmSched v2 — v0.10 Descriptor Compiler

## Overview

Transform the existing llmSched codebase from a v0.9-era pipeline (with diagnosis, visualization, evaluation, and reporting) into a focused v0.10 descriptor compiler. The journey: clean house, build a task-centric ONNX frontend, rewrite scheduling around task DAGs, implement the v0.10 descriptor packer/parser for all 11 families, harden correctness with 4-layer verification, and emit structural performance metrics.

## Phases

- [ ] **Phase 1: Cleanup & Foundation** - Remove old code and docs, retain only execution-semantic pipeline
- [ ] **Phase 2: Task DAG Frontend** - Extract task-unit dependency DAG from ONNX models
- [ ] **Phase 3: Task-Centric Scheduling** - Schedule task DAGs with memory planning and execution ordering
- [ ] **Phase 4: Descriptor Packing** - Pack and parse v0.10 descriptors for all 11 families
- [ ] **Phase 5: Descriptor Verification** - Harden correctness with round-trip and 4-layer verification gate
- [ ] **Phase 6: Performance Metrics** - Emit structural metrics and per-layer timelines

## Phase Details

### Phase 1: Cleanup & Foundation
**Goal**: Clean codebase ready for v2 development; only execution-semantic pipeline remains
**Depends on**: Nothing (first phase)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04
**Success Criteria** (what must be TRUE):
  1. `src/` contains no old descriptor generation, workbench, diagnosis, visualization, or report-generation code
  2. `docs/development/` and `docs/architecture-diagnosis/` are archived or deleted
  3. README clearly states the project is undergoing complete refactoring and current outputs are not correct
  4. The only remaining pipeline in `src/` is ONNX → task DAG → scheduling → descriptor packing
**Plans**: TBD

### Phase 2: Task DAG Frontend
**Goal**: ONNX models can be transformed into task-unit dependency DAGs
**Depends on**: Phase 1
**Requirements**: FRONT-01, FRONT-02, FRONT-03
**Success Criteria** (what must be TRUE):
  1. Given an ONNX model, the frontend extracts model structure and maps it to a task-unit dependency DAG
  2. Graph nodes are identified by macro_op type (attention, GEMM, RMSNorm, GEGLU, element-wise, RoPE, KV load/store)
  3. Reshape, transpose, squeeze, unsqueeze, and gather ops are filtered out and not modeled as tasks
  4. The task DAG correctly represents data dependencies between task units
**Plans**: TBD

### Phase 3: Task-Centric Scheduling
**Goal**: Task DAGs can be scheduled with memory planning and execution ordering for dual-core NPU
**Depends on**: Phase 2
**Requirements**: SCHED-01, SCHED-02, SCHED-03
**Success Criteria** (what must be TRUE):
  1. Memory planning operates on the task-centric DAG with per-core independent VMEM allocation
  2. Scheduling produces a task-level execution order with all dependencies resolved for dual-core only
  3. Each core has independent VMEM; no shared VMEM space between cores
  4. Scheduled output includes per-task memory allocation, core assignment, and barrier semantics
**Plans**: TBD

### Phase 4: Descriptor Packing
**Goal**: v0.10 descriptors can be packed and parsed for all 11 families
**Depends on**: Phase 3
**Requirements**: DESC-01, DESC-02, DESC-03, DESC-04
**Success Criteria** (what must be TRUE):
  1. Descriptor structure follows v0.10 format: primary_header + FAMILY + BUFFER × n + LOOP + TEMPLATE
  2. Each task produces one descriptor, grouped by layer into descriptor sets
  3. Semantic fields encode to correct bitfield patterns with CRC-16/CCITT-FALSE integrity check
  4. Parser can decode bitfields back to semantic fields for all 11 families
  5. Variable-length records (2/3-word FAMILY, 1-2 word LOOP) are handled correctly per family
**Plans**: TBD

### Phase 5: Descriptor Verification
**Goal**: Descriptor correctness is verifiable through independent verification layers
**Depends on**: Phase 4
**Requirements**: DESC-05, DESC-06
**Success Criteria** (what must be TRUE):
  1. Pack → Parse → Pack produces identical bit patterns for every descriptor
  2. 4-layer verification gate passes: structural, reserved-bit, semantic, and round-trip
  3. Verification catches intentionally corrupted descriptors (negative testing)
  4. Golden fixtures generated from schema validate independently of implementation
**Plans**: TBD

### Phase 6: Performance Metrics
**Goal**: Compiler outputs structural performance metrics for every model
**Depends on**: Phase 5
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):
  1. Output includes model structure as ordered task list per layer
  2. Output includes per-layer descriptor count, total length in words, and bit-field utilization
  3. Output includes full-graph descriptor count, total length, and aggregate bit-field utilization
  4. Output includes per-layer execution timeline (start/end or relative ordering)
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Cleanup & Foundation | 0/TBD | Not started | - |
| 2. Task DAG Frontend | 0/TBD | Not started | - |
| 3. Task-Centric Scheduling | 0/TBD | Not started | - |
| 4. Descriptor Packing | 0/TBD | Not started | - |
| 5. Descriptor Verification | 0/TBD | Not started | - |
| 6. Performance Metrics | 0/TBD | Not started | - |
