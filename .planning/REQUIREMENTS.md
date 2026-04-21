# Requirements: llmSched v2 — v0.10 Descriptor Compiler

**Defined:** 2026-04-21
**Core Value:** Given an ONNX model, produce a correct, verifiable v0.10 descriptor set that the NPU controller can parse and execute

## v1 Requirements

### Cleanup

- [ ] **CLEAN-01**: Remove all old descriptor generation, workbench, diagnosis, visualization, and report-generation implementations from `src/`
- [ ] **CLEAN-02**: Archive or delete `docs/development/` and `docs/architecture-diagnosis/` content
- [ ] **CLEAN-03**: Update README to state the project is undergoing complete refactoring and current outputs are not correct
- [ ] **CLEAN-04**: Retain only execution-semantic pipeline (ONNX → task DAG → scheduling → descriptor packing)

### Frontend

- [ ] **FRONT-01**: Refactor frontend to extract model structure and map it to a task-unit dependency DAG
- [ ] **FRONT-02**: Implement macro_op-based task identification from ONNX graph nodes
- [ ] **FRONT-03**: Filter out reshape, transpose, squeeze, unsqueeze, and gather ops — do not model them as tasks

### Scheduling

- [ ] **SCHED-01**: Rewrite memory planning to operate on task-centric DAG (not node-centric NIG)
- [ ] **SCHED-02**: Rewrite scheduling to produce task-level execution order with dependency resolution

### Descriptor

- [ ] **DESC-01**: Implement v0.10 descriptor structure: primary_header + FAMILY + BUFFER × n + LOOP + TEMPLATE
- [ ] **DESC-02**: Implement task-centered descriptor set packing (one descriptor per task, grouped by layer)
- [ ] **DESC-03**: Implement descriptor encoder (semantic → bitfield) with CRC-16/CCITT-FALSE
- [ ] **DESC-04**: Implement descriptor parser (bitfield → semantic) for all 11 families
- [ ] **DESC-05**: Implement round-trip gate: pack → parse → pack must produce identical bit pattern
- [ ] **DESC-06**: Implement 4 verification layers: structural, reserved-bit, semantic, round-trip

### Performance Output

- [ ] **PERF-01**: Output model structure as a task-level computation chain (ordered task list per layer)
- [ ] **PERF-02**: Output per-layer descriptor count, total length in words, and bit-field utilization
- [ ] **PERF-03**: Output full-graph descriptor count, total length, and aggregate bit-field utilization
- [ ] **PERF-04**: Output per-layer execution timeline (start/end or relative ordering)

## v2 Requirements

### Evaluation

- **EVAL-01**: Cycle-accurate performance estimation (new model)
- **EVAL-02**: Prefill/decode evaluation reports

### Visualization

- **VIS-01**: Static workbench builder
- **VIS-02**: Cross-run catalog

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reshape/Transpose/Squeeze/Unsqueeze/Gather task modeling | Explicitly excluded; layout ops are transparent to NPU |
| Old v0.9 descriptor format support | v0.10 is the only target format |
| Diagnosis reports and workbenches | Removed per requirement |
| Visualization builders and catalogs | Removed per requirement |
| Prefill/decode evaluation reports (old model) | Removed per requirement |
| Sweep analysis and compare | Removed per requirement |
| Roofline analysis | Removed with evaluation layer |
| Multi-run catalog/compare | Removed with visualization layer |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLEAN-01 | Phase 1 | Pending |
| CLEAN-02 | Phase 1 | Pending |
| CLEAN-03 | Phase 1 | Pending |
| CLEAN-04 | Phase 1 | Pending |
| FRONT-01 | Phase 2 | Pending |
| FRONT-02 | Phase 2 | Pending |
| FRONT-03 | Phase 2 | Pending |
| SCHED-01 | Phase 3 | Pending |
| SCHED-02 | Phase 3 | Pending |
| DESC-01 | Phase 4 | Pending |
| DESC-02 | Phase 4 | Pending |
| DESC-03 | Phase 4 | Pending |
| DESC-04 | Phase 4 | Pending |
| DESC-05 | Phase 4 | Pending |
| DESC-06 | Phase 4 | Pending |
| PERF-01 | Phase 5 | Pending |
| PERF-02 | Phase 5 | Pending |
| PERF-03 | Phase 5 | Pending |
| PERF-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-21*
*Last updated: 2026-04-21 after initial definition*
