# Domain Pitfalls: NPU v0.10 Descriptor Compiler

**Domain:** Hardware descriptor bitfield packing, parsing, and verification for NPU controller
**Researched:** 2026-04-21
**Confidence:** HIGH — derived from authoritative spec, handoff doc, machine-readable schema, and known failure modes from v0.9→v0.10 migration.

---

## Critical Pitfalls

Mistakes that cause silent corruption, parser/controller mismatch, or round-trip failures.

### Pitfall 1: Fixed-Length FAMILY Assumption (3 Words for All Families)
**What goes wrong:** The encoder or parser treats every FAMILY record as 3 words (192 bits). For RMSNORM (0x01), ELEM_ADD (0x06), and GEGLU (0x07), FAMILY is only 2 words (128 bits). A 3-word parser reads the first word of the following BUFFER record as FAMILY word 2, corrupting all subsequent record boundaries. A 3-word encoder inserts 64 bits of garbage/zero between FAMILY and BUFFER, causing the controller to misparse BUFFER[0].

**Why it happens:** v0.9 used a fixed 4-word FAMILY. Developers migrating from v0.9 reflexively carry the fixed-length assumption. The variable-length rule is conditional on `task_type_id`, not on any field inside FAMILY itself, so it is easy to miss.

**Consequences:** All downstream records shift by one word. CRC may still pass if the encoder and parser share the same bug, but the controller (which follows the spec) will reject the descriptor. Round-trip tests that use the same buggy parser will falsely pass.

**Prevention:**
- Generate the FAMILY word-count table from `family_lut.yaml` at build/test time, do not hardcode.
- In the parser, derive `family_words` immediately after reading `task_type_id` from `primary_header`, before touching any FAMILY bits.
- In unit tests, assert exact word offsets for every record boundary for every family.

**Detection:**
- Structural verifier catches `total_words` mismatch.
- Round-trip test with a reference parser (not the same implementation) catches offset drift.
- Hand-crafted binary fixtures for 2-word families (RMSNORM, ELEM_ADD, GEGLU) with known byte patterns at BUFFER[0] word 0 will fail if the parser overreads FAMILY.

**Phase to address:** DESC-01 (structure), DESC-04 (parser), DESC-05 (round-trip gate).

---

### Pitfall 2: Dispatch-First Semantic Resolution Violation
**What goes wrong:** Code interprets `family_mode`, `primary_surface_slot`, or `secondary_surface_slot` before dispatching on `task_type_id`. For example, a generic FAMILY struct assigns the name `accum_dtype` to bits [47:44] for all families, causing SDPA to read a non-zero `family_mode` as a spurious `accum_dtype` instead of flagging it as a reserved-bit violation.

**Why it happens:** Natural instinct is to give every bitfield a fixed semantic name. The v0.10 spec intentionally uses neutral wire-level names (`family_mode`, `primary_surface_slot`) whose meaning is resolved only after `task_type_id` dispatch. This is an unusual pattern in hardware descriptor design.

**Consequences:**
- Non-owning families (SDPA, RMSNORM, WDQ_GEMM, ELEM_ADD, GEGLU, RMSNORM_GEMM) silently accept garbage in `family_mode`.
- KVSTORE surface slots are interpreted as outputs instead of inputs, breaking buffer binding.
- Semantic verifier passes invalid descriptors.

**Prevention:**
- Enforce a two-phase architecture: (1) `parse` recovers raw bitfields into neutral wire names; (2) `materialize` dispatches on `task_type_id` to produce family-specific semantic views. Do not conflate the two.
- In the semantic verifier, assert `must_be_zero` for every bit range listed in `family_lut.yaml` under `must_be_zero_positions` for the specific family.
- Use code generation from `family_lut.yaml` so that the per-family must-be-zero mask is mechanically derived, not hand-maintained.

**Detection:**
- Reserved-bit verifier catches non-zero bits in `family_mode` for non-owning families — but only if the mask is correct.
- A test that packs a descriptor with `family_mode=0xF` for RMSNORM and expects a reserved-bit violation will catch the bug.

**Phase to address:** DESC-04 (parser), DESC-06 (semantic verification).

---

### Pitfall 3: Wrong BUFFER Word Count (5 Words from v0.9 Habit)
**What goes wrong:** The encoder allocates 5 words per BUFFER record (v0.9 size) instead of 4. This shifts all LOOP/TEMPLATE offsets and wastes 64 bits per buffer. Conversely, a parser reading 5 words per BUFFER overreads into the next record.

**Why it happens:** v0.9 BUFFER was 5 words. The compaction to 4 words (O-02) is a single-line change in a table but a pervasive change in code. Any code that says `BUFFER_WORDS = 5` or `buffer_size = 5 * 64` is wrong.

**Consequences:** Descriptor size is wrong by `buffer_count` words. CRC covers the wrong length. Controller parser fails.

**Prevention:**
- Define `BUFFER_WORDS = 4` as a single constant in one module. No other module should have a literal `5` or `4` for buffer sizing.
- In the structural verifier, cross-check: `len(descriptor_words) == 1 + family_words + 4 * buffer_count + loop_words + template_words`.

**Detection:**
- Structural verifier fails on word-count mismatch.
- Round-trip test fails because re-packing produces a different length.

**Phase to address:** DESC-01 (structure), DESC-03 (encoder).

---

### Pitfall 4: LOOP Length Miscomputed for Rank 1 and 2
**What goes wrong:** The parser or encoder assumes LOOP is always 2 words (like v0.9). In v0.10, LOOP is 1 word for `loop_rank` 1 or 2, and 2 words only for `loop_rank` 3. A parser that always reads 2 words overreads into TEMPLATE or the next descriptor. An encoder that always writes 2 words inserts 64 reserved bits that should not exist.

**Why it happens:** v0.9 LOOP was fixed at 3 words. v0.10 compacts it to 1–2 words (O-03). The rank-dependent rule is subtle: `ceil(loop_rank * 32 / 64)` gives 1 word for ranks 1–2, 2 words for rank 3.

**Consequences:** Record boundary shift. TEMPLATE parsing fails. If `template_slot_count == 0`, the overread may reach into the next descriptor in a descriptor set.

**Prevention:**
- Derive LOOP words from `loop_rank` using the exact formula from `layout.yaml`: `loop_words = 1 if loop_rank <= 2 else 2`.
- Unit-test all three ranks with hand-crafted descriptors where TEMPLATE[0] (or next descriptor word 0) has a known sentinel value.

**Detection:**
- Structural verifier checks LOOP word count against `loop_rank`.
- Round-trip test with rank-1 and rank-2 descriptors.

**Phase to address:** DESC-01 (structure), DESC-04 (parser).

---

### Pitfall 5: CRC-16 Computed Over Wrong Scope or With Wrong Byte Order
**What goes wrong:** The CRC-16/CCITT-FALSE is computed with the `crc16` field still containing its final value (not zeroed), or over little-endian word serialization, or over a subset of words. The controller computes CRC over all words MSB-first with `crc16` zeroed during computation.

**Why it happens:** CRC libraries often default to little-endian or expect a contiguous byte buffer. The spec requires big-endian word serialization and zeroing the CRC field in-place. This is easy to get wrong in Python where `struct.pack` defaults to native endianness.

**Consequences:** Descriptor is structurally valid but rejected by controller CRC check. Round-trip may pass if the same buggy CRC logic is used for pack and parse, but controller rejects.

**Prevention:**
- Implement CRC as a standalone, tested function: `crc16_ccitt_false(words: list[int]) -> int`.
- Explicitly zero bits [37:22] of word 0 before CRC computation.
- Serialize each 64-bit word as 8 big-endian bytes (`struct.pack('>Q', word)`).
- Verify against the known check value `0x29B1` using the test vector from the spec.
- Do not use a generic CRC library without confirming its parameters match exactly: poly=0x1021, init=0xFFFF, xorout=0x0000, no reflection.

**Detection:**
- A test that packs a descriptor, manually computes expected CRC with a reference implementation, and asserts equality.
- A test that corrupts one bit and asserts CRC mismatch.

**Phase to address:** DESC-03 (encoder), DESC-06 (verification).

---

### Pitfall 6: Reserved Bits Not Zeroed or Not Verified
**What goes wrong:** The encoder leaves garbage in reserved bitfields (e.g., `reserved[37:0]` in BUFFER, `reserved[13:0]` in primary_header, unused fields in FAMILY word 2 for 2-word families). The parser does not check them. The controller may use reserved bits in future versions and will reject non-zero values.

**Why it happens:** Python bit-shifting makes it easy to OR in values without masking. Pydantic models do not enforce bit-width constraints at the wire level. Reserved bits are "invisible" in semantic models.

**Consequences:** Descriptors pass internal tests but fail on future hardware or stricter controller versions. Round-trip tests may pass because the same garbage is preserved.

**Prevention:**
- In the encoder, mask every field before OR-ing it into its word: `word |= (value & mask) << shift`.
- In the reserved-bit verifier, for every record, compute the expected-zero mask from `field_tables.yaml` and assert `(word & zero_mask) == 0`.
- Generate the zero-mask tables from `field_tables.yaml` and `family_lut.yaml` at build time.

**Detection:**
- Reserved-bit verifier (layer 2) catches any non-zero reserved bit.
- Fuzz tests that randomize all fields and assert reserved-bit violations for out-of-range values.

**Phase to address:** DESC-03 (encoder), DESC-06 (reserved-bit verification).

---

### Pitfall 7: TEMPLATE Absent vs. Zero-Word Confusion
**What goes wrong:** When `template_slot_count == 0`, the TEMPLATE record is entirely absent (0 words). Code may instead emit a 1-word record of zeros, or a parser may expect at least 1 word and read garbage.

**Why it happens:** Other records (FAMILY, BUFFER, LOOP) always have non-zero length. TEMPLATE is the only optional record. Optional absence is easy to miss in loop-based parsing logic.

**Consequences:** Descriptor is 1 word too long. Total word count mismatch. Controller parser may read into next descriptor.

**Prevention:**
- In the encoder, guard TEMPLATE emission with `if template_slot_count > 0:`.
- In the parser, guard TEMPLATE reading with the same condition.
- In the structural verifier, assert `template_words == 0` when `template_slot_count == 0`.

**Detection:**
- Structural verifier.
- Round-trip test for a descriptor with `template_slot_count == 0`.

**Phase to address:** DESC-01 (structure), DESC-03 (encoder), DESC-04 (parser).

---

### Pitfall 8: Surface Slot Directionality Bug in KVSTORE
**What goes wrong:** For KVSTORE, `primary_surface_slot` and `secondary_surface_slot` are input surfaces (they index which input surfaces supply KV data to be stored), not outputs. Code that treats them as outputs will bind the wrong buffers.

**Why it happens:** The wire names are `primary_surface_slot` and `secondary_surface_slot`, which sound like outputs. The spec explicitly says their direction is resolved by `task_type_id` dispatch: outputs for most families, inputs for KVSTORE. This is a semantic trap.

**Consequences:** KVSTORE descriptor points to output surfaces that do not exist, causing DMA or VPU faults at runtime.

**Prevention:**
- In the materializer (not parser), after dispatching on `task_type_id == KVSTORE`, rename the slots to `primary_input_surface` and `secondary_input_surface` in the semantic view.
- In the semantic verifier, assert that KVSTORE descriptors have `primary_surface_slot` and `secondary_surface_slot` pointing to buffers with `role == input` and `access_mode` compatible with read.

**Detection:**
- Semantic verifier checks buffer role consistency.
- Integration test with a full model that includes KVSTORE and validates buffer binding.

**Phase to address:** DESC-04 (parser materialization), DESC-06 (semantic verification), SCHED-01 (memory planning).

---

### Pitfall 9: LOOP Slot Packing Order for Rank 3
**What goes wrong:** For `loop_rank == 3`, LOOP occupies 2 words. Slot 0 is in bits [63:32] of word 0, slot 1 in bits [31:0] of word 0, and slot 2 in bits [31:0] of word 1. Bits [63:32] of word 1 are reserved (must be zero). A parser that puts slot 2 in bits [63:32] of word 1 is wrong.

**Why it happens:** The packing is dense in the first word (2 slots) but only half-used in the second word (1 slot in the lower half). This asymmetry is unusual.

**Consequences:** Loop dimensions are swapped or corrupted. Tile iteration produces wrong coordinates.

**Prevention:**
- Implement LOOP packing/unpacking with explicit per-rank layouts, not a generic loop.
- Unit-test rank-3 LOOP with distinct sentinel values for each slot and assert exact bit positions.

**Detection:**
- Round-trip test with rank-3 and distinct slot values.
- Bit-level fixture test that asserts exact word values for a known LOOP record.

**Phase to address:** DESC-03 (encoder), DESC-04 (parser).

---

### Pitfall 10: Shared Bug Between Encoder and Parser Masking Defects
**What goes wrong:** The round-trip test (`pack → parse → pack`) uses the same encoder and parser implementation. If both share the same bug (e.g., both treat FAMILY as 3 words, both compute CRC incorrectly), the round-trip passes but the descriptor is invalid per spec.

**Why it happens:** Round-trip is necessary but not sufficient. It only proves self-consistency, not spec compliance.

**Consequences:** False confidence. Descriptors ship to controller and fail.

**Prevention:**
- Round-trip must be one of four verification layers, not the only gate.
- Maintain a separate reference parser (or golden binary fixtures) generated independently from the spec, not from the implementation.
- Use the machine-readable schema (`family_lut.yaml`, `field_tables.yaml`, `layout.yaml`) to generate test fixtures and expected bit patterns mechanically.
- Cross-validate against a second implementation if possible (e.g., a simple C parser for the controller).

**Detection:**
- Structural, reserved-bit, and semantic verifiers catch bugs that round-trip misses.
- Independent golden fixtures catch shared encoder/parser bugs.

**Phase to address:** DESC-05 (round-trip), DESC-06 (all 4 layers).

---

## Moderate Pitfalls

### Pitfall 11: `scalar0` Repurposing for WDQ_GEMM Overlooked
**What goes wrong:** For WDQ_GEMM, `scalar0` (word 0–1 bits [15:0]) carries `group_size` (max 128), not a generic scalar. Code that applies a generic scalar validation (e.g., allowing full 16-bit range) may accept invalid group sizes.

**Prevention:** In the semantic verifier, apply family-specific range checks. For WDQ_GEMM, assert `1 <= group_size <= 128`.

**Phase to address:** DESC-06 (semantic verification).

---

### Pitfall 12: `dim_count` vs. Actual Stride Dimensions Mismatch in BUFFER
**What goes wrong:** BUFFER `dim_count` says how many stride dimensions are active, but the actual `dim_0_extent`, `dim_1_extent`, `dim_2_extent` fields may be non-zero even for inactive dimensions. The semantic verifier should check consistency.

**Prevention:** Assert that for `dim_count < 3`, the unused extent/stride fields are zero or appropriately ignored by the controller. Document the controller's behavior clearly.

**Phase to address:** DESC-06 (semantic verification).

---

### Pitfall 13: Base Address Split Across `base_binding_lo`/`base_binding_hi` Mishandled
**What goes wrong:** VMEM addresses must have `base_binding_hi == 0`. DDR addresses use both. Code that always ORs both halves will produce invalid VMEM descriptors. Code that ignores `base_binding_hi` will truncate DDR addresses.

**Prevention:** In the semantic verifier, assert `base_binding_hi == 0` when `address_space == VMEM_ABSOLUTE`.

**Phase to address:** DESC-06 (semantic verification), SCHED-01 (memory planning).

---

### Pitfall 14: `family_lut.yaml` and Code Drift
**What goes wrong:** The machine-readable schema (`family_lut.yaml`) is authoritative, but the implementation hardcodes family definitions. When the schema is updated, the code becomes stale.

**Prevention:** Generate encoder tables, parser dispatch tables, and verifier masks directly from `family_lut.yaml` and `field_tables.yaml` at build time. Treat schema changes as code changes.

**Phase to address:** DESC-01 (structure), DESC-03 (encoder), DESC-04 (parser).

---

## Minor Pitfalls

### Pitfall 15: `descriptor_version` Not Checked First
**What goes wrong:** Parser attempts to interpret a non-v0.10 descriptor using v0.10 rules, producing nonsensical field values.

**Prevention:** Parser step 0: assert `descriptor_version == 0x6`. Reject immediately if not.

**Phase to address:** DESC-04 (parser).

---

### Pitfall 16: `task_type_id` Out of Range
**What goes wrong:** `task_type_id` is 6 bits (values 0x01–0x0B). A value of 0x00 or 0x0C+ has no defined family. Parser may index out of bounds.

**Prevention:** Validate `task_type_id` against the enum in `field_tables.yaml` before any dispatch.

**Phase to address:** DESC-04 (parser), DESC-06 (semantic verification).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| DESC-01: v0.10 structure design | FAMILY length table hardcoded instead of schema-driven | Generate from `family_lut.yaml` |
| DESC-02: Task-centered packing | BUFFER count mismatch with planned buffers | Cross-check against memory planner output |
| DESC-03: Encoder | Reserved bits not masked; CRC wrong endianness | Mask all fields; test CRC against `0x29B1` vector |
| DESC-04: Parser | Dispatch-first violation; fixed-length assumptions | Two-phase parse+materialize; schema-driven record lengths |
| DESC-05: Round-trip | Shared encoder/parser bug masks defect | Use independent golden fixtures |
| DESC-06: 4-layer verification | Semantic verifier does not check must-be-zero per family | Generate must-be-zero masks from `family_lut.yaml` |
| SCHED-01: Memory planning | VMEM hi bits non-zero; DDR addresses truncated | Enforce address-space rules in planner |
| SCHED-02: Scheduling | `loop_rank` or `template_slot_count` inconsistent with task family | Validate against family schema before packing |
| FRONT-01: Task DAG | Layout ops (reshape, transpose) accidentally modeled as tasks | Explicit filter list per requirement |

---

## Sources

- `docs/descriptor/descriptor-encoding-layout.md` — v0.10 encoding spec (O-01 through O-05, record length derivation, bitfield tables)
- `docs/descriptor/descriptor-handoff.md` — Controller handoff with "最容易出错的 8 个点"
- `docs/descriptor/family_lut.yaml` — Machine-readable family schema with active fields and must-be-zero positions
- `docs/descriptor/field_tables.yaml` — Machine-readable field definitions for PRIMARY_HEADER, FAMILY, BUFFER, LOOP, TEMPLATE
- `docs/descriptor/layout.yaml` — Machine-readable structure, parser steps, CRC spec, record length derivation
- `.planning/codebase/CONCERNS.md` — Existing codebase fragility (no schema versioning, broad exception handling, duplicated constants)
