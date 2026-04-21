# Research Summary: llmSched v2 — v0.10 Descriptor Compiler

**Synthesized:** 2026-04-21
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Key Findings

### Stack
- **No new dependencies needed.** Python standard library (`int` bit ops, `struct`, `binascii.crc_hqx`) handles all bitfield packing, parsing, and CRC-16/CCITT-FALSE. Verified check value `0x29B1`.
- **Pydantic v2** is the right tool for hardware schemas: `Field(ge=, le=)` for width constraints, discriminated unions for family dispatch, `ConfigDict(strict=True, frozen=True)` for immutability.
- **`graphlib.TopologicalSorter`** (Python 3.9+) handles task DAG ordering without networkx.
- **ONNX 1.20+** is current and stable for graph traversal.
- **PyYAML + `lru_cache`** for loading `docs/descriptor/*.yaml` schema files at import time.

### Table Stakes
1. **Correct v0.10 descriptor packing** for all 11 families with variable-length FAMILY (2/3 words), 4-word BUFFER, 1-2 word LOOP, optional TEMPLATE.
2. **Round-trip verification** — Pack → Parse → Pack must produce identical bit patterns. This is the correctness contract.
3. **Dispatch-first semantic resolution** — `family_mode`, surface slots, and repurposed fields must not be interpreted until `task_type_id` is known.
4. **Task-centric dependency DAG** from ONNX — macro_op identification, layout-op filtering, task-level scheduling.
5. **4-layer verification gate** — structural, reserved-bit, semantic, round-trip.

### Differentiators
1. **Schema-driven generation** from `family_lut.yaml`, `field_tables.yaml`, `layout.yaml` — auto-generate encoder/decoder tables to prevent drift.
2. **Independent golden fixtures** for verification, generated from schema rather than implementation.
3. **Unified task scheduler** replacing separate single/dual-core schedulers.

### Anti-Features
1. Hard-coded family field layouts (use YAML schemas instead).
2. Shared encoder/parser without independent verification layers.
3. Keeping v0.9 descriptor support (v0.10 only).
4. Downstream evaluation, diagnosis, visualization surfaces.

### Architecture
- **Keep:** ONNX frontend canonicalization, Pydantic IR patterns, manifest-based artifact tracking, profile-driven parametrization.
- **Rewrite:** NIG lowering → Task DAG builder, memory planner + scheduler (task-centric), descriptor engine (v0.10).
- **Delete:** All old descriptor generation, performance estimation, evaluation, visualization, diagnosis, sweep.
- **Build order:** Foundation (cleanup + schemas) → Frontend (Task DAG) → Planning (task-centric) → Descriptor Engine → Integration + Metrics → Verification Hardening.

### Watch Out For
1. **Fixed-length FAMILY assumption** — RMSNORM/ELEM_ADD/GEGLU are 2 words; others are 3.
2. **CRC-16 endianness** — big-endian word serialization; Python defaults to native-endian.
3. **Shared encoder/parser bugs** — round-trip alone masks defects; need 4 independent layers.
4. **Reserved-bit drift** — must generate zero-bit masks from YAML schema, not hardcode.
5. **LOOP rank-3 packing order** — slot 0 in word 0 [63:32], slot 1 in word 0 [31:0], slot 2 in word 1 [31:0]; upper half of word 1 is reserved.
6. **Dual-core dep_mask/signal_mask** — mapping from scheduler barrier semantics to per-descriptor bit masks needs design work.

### Open Questions
- How will TEMPLATE slots be generated from task stage semantics? Needs controller team clarification.
- Dual-core scheduling: how do barrier_in/barrier_out map to dep_mask/signal_mask at task level?
- Golden fixture generation strategy for round-trip tests.

---
*Research completed: 2026-04-21*
