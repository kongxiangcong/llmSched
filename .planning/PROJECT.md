# llmSched v2 — v0.10 Descriptor Compiler

## What This Is

A compiler that transforms ONNX LLM models into verified v0.10 descriptor sets for the `tars-npu-ctrl` NPU controller. It extracts a task-centric dependency DAG from the model graph, schedules tasks, packs descriptors per task family (11 families), and verifies round-trip correctness. Performance output is limited to structural metrics and per-layer timelines — no downstream evaluation, diagnosis, or visualization surfaces.

## Core Value

Given an ONNX model, produce a correct, verifiable v0.10 descriptor set that the NPU controller can parse and execute. Round-trip verification must pass for every descriptor.

## Requirements

### Validated

- ✓ ONNX model import and GraphIR generation — existing frontend
- ✓ Graph canonicalization and NIG lowering — existing frontend
- ✓ Memory planning (single/dual-core) — existing planning layer
- ✓ Tile planning — existing planning layer
- ✓ Single-core and dual-core scheduling — existing planning layer
- ✓ Old descriptor generation (v0.9 and earlier) — existing, to be removed
- ✓ Performance estimation (old model) — existing, to be removed
- ✓ Prefill/decode evaluation reports — existing, to be removed
- ✓ Diagnosis analysis, packaging, workbench — existing, to be removed
- ✓ Visualization builders and catalogs — existing, to be removed
- ✓ Sweep analysis and compare — existing, to be removed

### Active

- [ ] **CLEAN-01**: Remove all old descriptor generation, workbench, diagnosis, visualization, and report-generation implementations from `src/`
- [ ] **CLEAN-02**: Archive or delete `docs/development/` and `docs/architecture-diagnosis/` content
- [ ] **CLEAN-03**: Update README to state the project is undergoing complete refactoring and current outputs are not correct
- [ ] **CLEAN-04**: Retain only execution-semantic pipeline (ONNX → task DAG → scheduling → descriptor packing)
- [ ] **FRONT-01**: Refactor frontend to extract model structure and map it to a task-unit dependency DAG
- [ ] **FRONT-02**: Implement macro_op-based task identification from ONNX graph nodes
- [ ] **FRONT-03**: Filter out reshape, transpose, squeeze, unsqueeze, and gather ops — do not model them as tasks
- [ ] **SCHED-01**: Rewrite memory planning to operate on task-centric DAG (not node-centric NIG)
- [ ] **SCHED-02**: Rewrite scheduling to produce task-level execution order with dependency resolution
- [ ] **DESC-01**: Implement v0.10 descriptor structure: primary_header + FAMILY + BUFFER × n + LOOP + TEMPLATE
- [ ] **DESC-02**: Implement task-centered descriptor set packing (one descriptor per task, grouped by layer)
- [ ] **DESC-03**: Implement descriptor encoder (semantic → bitfield) with CRC-16/CCITT-FALSE
- [ ] **DESC-04**: Implement descriptor parser (bitfield → semantic) for all 11 families
- [ ] **DESC-05**: Implement round-trip gate: pack → parse → pack must produce identical bit pattern
- [ ] **DESC-06**: Implement 4 verification layers: structural, reserved-bit, semantic, round-trip
- [ ] **PERF-01**: Output model structure as a task-level computation chain (ordered task list per layer)
- [ ] **PERF-02**: Output per-layer descriptor count, total length in words, and bit-field utilization
- [ ] **PERF-03**: Output full-graph descriptor count, total length, and aggregate bit-field utilization
- [ ] **PERF-04**: Output per-layer execution timeline (start/end or relative ordering)

### Out of Scope

| Feature | Reason |
|---------|--------|
| Reshape/Transpose/Squeeze/Unsqueeze/Gather task modeling | Explicitly excluded per requirement; these are layout ops, not compute tasks |
| Old v0.9 descriptor format support | v0.10 is the only target format |
| Diagnosis reports and workbenches | Removed per requirement — only execution semantics remain |
| Visualization builders and catalogs | Removed per requirement |
| Prefill/decode evaluation reports (old model) | Removed per requirement |
| Sweep analysis and compare | Removed per requirement |
| Performance estimation (cycle-level) | Out of scope for v2; only structural descriptor metrics |
| Roofline analysis | Removed with evaluation layer |
| Multi-run catalog/compare | Removed with visualization layer |

## Context

The existing llmSched codebase (~47K lines of tests, ~19 pipeline modules) was built around an older descriptor contract (v0.9 and earlier). The new v0.10 descriptor format introduces:
- Flat descriptor structure (no primary/continuation distinction)
- Variable-length FAMILY record (2 or 3 words)
- Compacted BUFFER (4 words, down from 5)
- Compacted LOOP (1–2 words)
- Merged primary_header + TASK payload (1 word)
- Dispatch-first `family_mode` semantic resolution
- CRC-16/CCITT-FALSE integrity check

The controller (`tars-npu-ctrl`) expects to read `primary_header`, derive all record lengths mechanically, then parse FAMILY/BUFFER/LOOP/TEMPLATE in fixed order. The compiler must produce descriptors that pass this parser exactly.

Machine-readable schema files exist in `docs/descriptor/` (`family_lut.yaml`, `field_tables.yaml`, `layout.yaml`) and should be treated as authoritative alongside the markdown specs.

## Constraints

- **Tech stack**: Python 3.12+, Pydantic v2, Typer, ONNX. No new major dependencies.
- **Input format**: ONNX remains the sole input format.
- **Descriptor version**: 0x6 (v0.10) only. No backward compatibility.
- **Cleanup scope**: Old code deleted from `src/`, not just disabled. Git history may be rewritten or old modules removed in new commits.
- **Test strategy**: Old test suite will be largely invalidated. New tests must cover parser/packer round-trip for all 11 families.
- **Model scope**: Gemma3-like transformer workloads (attention, GEMM, RMSNorm, GEGLU, element-wise ops, RoPE, KV load/store).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep ONNX as input | User confirmed; existing ONNX importer is validated | — Pending |
| Delete old code from src/ (not archive) | User confirmed; clean slate for v2 | — Pending |
| v0.10 only, no v0.9 backward compat | New controller only speaks v0.10 | — Pending |
| No layout-op task modeling | reshape/transpose/etc. are transparent to NPU execution | — Pending |
| 4-layer verification gate | Structural + reserved-bit + semantic + round-trip per v0.10 spec | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-21 after initialization*
