# A3 Encoding Layout — v0.10 Descriptor Format

**Status:** Draft for NPU Controller Delivery
**Descriptor Version:** 0x6
**Date:** 2026-04-21

## 1. Version and Format Baseline

descriptor_version=0x6 (v0.10). v0.9/v0.8/v0.7 are structural references only.

This version introduces five structural optimizations over v0.9:

- **O-01:** FAMILY variable-length layout with high-frequency fields packed into the first 128 bits; 30 bits reclaimed by merging `kv_operand_binding_mode`/`append_mode`/`position_mode` into a neutral `family_mode` slot, removing `group_size`/`dtype0`/`dtype1`/`dtype2`/`primary_input_surface`/`secondary_input_surface` (see §3.2 and `v0.10-optimization-design-note.md`).
- **O-02:** BUFFER body compacted from 5 words (320 bits) to 4 words (256 bits) by eliminating two reserved gaps (bits 285:256 and 223:192 in v0.9) and packing `span`/`base_binding_lo`/`base_binding_hi` contiguously.
- **O-03:** LOOP body compacted to 32-bit slots (matching TEMPLATE slot density), eliminating 32 reserved bits per slot. Loop body size now varies with `loop_rank`: 1 word (rank 1–2) or 2 words (rank 3).
- **O-04:** Primary header and TASK payload merged into a single 64-bit word; `total_record_count` and all 7 `per_record_length` fields removed — all record lengths are derivable from `task_type_id`, `buffer_count`, `loop_rank`, `template_slot_count`.
- **O-05:** Descriptor structure flattened: `primary_header` (64 bits) followed by RECORDs (FAMILY, BUFFER, LOOP, TEMPLATE). No primary/continuation distinction. Primary header renamed from generic header.

No Common Body Header. All records carry only their payload fields. The `primary_header` in word 0 provides version and dispatch.

## 2. Descriptor Structure

### Overall Layout

```
[primary_header (64 bits)] [FAMILY record] [BUFFER record × buffer_count] [LOOP record] [TEMPLATE record (conditional)]
```

The descriptor is a flat sequence of 64-bit words. No primary/continuation distinction exists. The `primary_header` occupies word 0; all subsequent words belong to RECORDs whose order is fixed and whose lengths are derivable from primary_header fields.

### Record Length Derivation Table

| Record | Length Rule | Derivation Key |
|--------|------------|----------------|
| FAMILY | 2 or 3 words | `task_type_id` lookup: 2 words for RMSNORM/ELEM_ADD/GEGLU; 3 words for all others |
| BUFFER | 4 words × buffer_count | `buffer_count` from primary_header |
| LOOP | ceil(loop_rank × 32 / 64) words | `loop_rank` from primary_header; rank 1–2 → 1 word, rank 3 → 2 words |
| TEMPLATE | ceil(template_slot_count × 32 / 64) words; absent if template_slot_count=0 | `template_slot_count` from primary_header |

### Total Descriptor Word Count Derivation

```
total_words = 1 (primary_header)
            + family_words(task_type_id)
            + 4 × buffer_count
            + loop_words(loop_rank)
            + template_words(template_slot_count)
```

No explicit total_record_count or per_record_length fields are needed.

## 3. Bitfield Tables

### 3.1 Primary Header (1 word = 64 bits)

| Field | Bits | Width | Value/Range | Description |
|-------|------|-------|-------------|-------------|
| descriptor_version | [63:60] | 4 | 0x6 | v0.10 format identifier |
| task_type_id | [59:54] | 6 | 0x01..0x0B | family dispatch index; also determines FAMILY record length |
| dep_mask | [53:46] | 8 | | per-descriptor dependency mask for multi-core synchronization; bit[i]=1 → wait for Core i |
| signal_mask | [45:38] | 8 | | per-descriptor signal mask; bit[i]=1 → signal Core i on completion |
| crc16 | [37:22] | 16 | | CRC-16/CCITT-FALSE over all words; zeroed during computation |
| buffer_count | [21:19] | 3 | 0..4 | number of BUFFER records |
| loop_rank | [18:17] | 2 | 1..3 | loop dimensionality; 0=reserved/invalid |
| template_slot_count | [16:14] | 3 | 0..7 | number of TEMPLATE action slots; 0=no TEMPLATE record |
| reserved | [13:0] | 14 | 0x0 | |

### 3.2 FAMILY Record

Variable-length: 2 words (128 bits) or 3 words (192 bits) depending on `task_type_id`.

#### Word 0–1 (128 bits, always present)

High-frequency fields; utilization ≥ 5/11 families for each field.

| Field | Bits | Width | Description |
|-------|------|-------|-------------|
| dim0_full_extent | [127:112] | 16 | first shape dimension; semantic varies by family |
| dim1_full_extent | [111:96] | 16 | second shape dimension; semantic varies by family |
| dim2_full_extent | [95:80] | 16 | third shape dimension (reduction dim or 0); semantic varies by family |
| dim0_tile_extent | [79:72] | 8 | tile size for dim0; 0 if not tiled |
| dim1_tile_extent | [71:64] | 8 | tile size for dim1; 0 if not tiled |
| dim2_tile_extent | [63:56] | 8 | tile size for dim2; 0 if not tiled |
| extra_dim0 | [55:40] | 16 | extra dimension 0 (head_dim, hidden_dim, etc.) |
| extra_tile0 | [39:32] | 8 | tile size for extra_dim0; 0 if not tiled |
| extra_dim1 | [31:16] | 16 | extra dimension 1 (num_kv_heads, intermediate_dim, kv_len_after, etc.) |
| scalar0 | [15:0] | 16 | scalar value (softmax_scale, epsilon, group_size for WDQ_GEMM, etc.) |

#### Word 2 (64 bits, present only when task_type_id requires it)

Enumeration and surface fields. Present for all families except RMSNORM, ELEM_ADD, GEGLU.

| Field | Bits | Width | Description |
|-------|------|-------|-------------|
| engine_profile | [63:60] | 4 | engine profile enum per global enum freeze |
| mask_cfg | [59:56] | 4 | attention mask configuration (SDPA, SDPA_DECODE) |
| cache_layout_class | [55:52] | 4 | KV cache layout class (KVLOAD, KVSTORE); repurposed as act_dtype for GEMM |
| cache_axis_order | [51:48] | 4 | KV cache axis order (KVLOAD, KVSTORE); repurposed as weight_dtype for GEMM |
| family_mode | [47:44] | 4 | neutral dispatch-first mode slot; semantic resolved by `task_type_id` — see §3.3 |
| primary_surface_slot | [43:41] | 3 | shared surface slot; resolved by `task_type_id` dispatch — primary output for most families, primary input for KVSTORE |
| secondary_surface_slot | [40:38] | 3 | shared surface slot; resolved by `task_type_id` dispatch — secondary output for most families, secondary input for KVSTORE |
| reserved | [37:0] | 38 | must be zero |

#### 3.3 family_mode Semantic Mapping (Dispatch-First)

The `family_mode` field (4 bits, FAMILY word 2 [47:44]) is a **neutral wire-level slot**. Its semantic meaning is resolved only **after** `task_type_id` dispatch. This design removes family-biased naming from the wire format and makes the slot reusable across families without silent fallback.

| Family | Dispatched Alias | v0.9 Field(s) Replaced | Semantic in v0.10 | Encoding |
|--------|-----------------|----------------------|-------------------|----------|
| GEMM | `accum_dtype` | dtype2 (accum_dtype) | accum_dtype enum | Same values as v0.9 dtype2 enum |
| KVLOAD | `source_binding_mode` | source_binding_mode | KV cache source binding mode | Unchanged from v0.9 |
| SDPA_DECODE | `kv_operand_binding_mode` | kv_operand_binding_mode | KV operand binding mode | Same values as v0.9 kv_operand_binding_mode |
| KVSTORE | `append_mode` | append_mode | KV cache append mode | Same values as v0.9 append_mode |
| ROPE | `position_mode` | position_mode | RoPE position mode | Same values as v0.9 position_mode |
| SDPA | — | — | must_be_zero | 0x0 |
| RMSNORM | — | — | must_be_zero | 0x0 |
| WDQ_GEMM | — | — | must_be_zero | 0x0 |
| ELEM_ADD | — | — | must_be_zero | 0x0 |
| GEGLU | — | — | must_be_zero | 0x0 |
| RMSNORM_GEMM | — | — | must_be_zero | 0x0 |

**Dispatch-first rule:** The parser must not interpret `family_mode` until `task_type_id` has been read from `primary_header`. Any non-owning family that leaves `family_mode` non-zero is a VIOLATION.

#### 3.4 cache_layout_class / cache_axis_order Repurposing for GEMM

For `task_type_id = 0x05` (GEMM), the KV-cache-specific fields are repurposed:

| Field | GEMM Semantic | Encoding |
|-------|--------------|----------|
| cache_layout_class [55:52] | act_dtype (activation data type) | Same values as v0.9 dtype0 enum |
| cache_axis_order [51:48] | weight_dtype (weight data type) | Same values as v0.9 dtype1 enum |
| family_mode [47:44] | accum_dtype (accumulator data type) | Same values as v0.9 dtype2 enum |

For non-KV, non-GEMM families, these fields are must_be_zero.

#### 3.5 surface Slot Repurposing for KVSTORE (Dispatch-First)

The `primary_surface_slot` [43:41] and `secondary_surface_slot` [40:38] are **shared surface slots** whose semantic direction is resolved by `task_type_id` dispatch. For most families they are output surfaces; for KVSTORE they are input surfaces because KVSTORE writes to the KV cache rather than producing a new tensor output.

| Family | `primary_surface_slot` [43:41] | `secondary_surface_slot` [40:38] |
|--------|-------------------------------|--------------------------------|
| Most families | primary_output_surface | secondary_output_surface |
| KVSTORE (0x0A) | primary_input_surface | secondary_input_surface |

For KVSTORE, the directionality is determined by BUFFER `role` and `access_mode`, not by the wire slot name. The surface slots index which input surfaces supply the KV data to be stored.

#### 3.6 scalar0 Repurposing for WDQ_GEMM

For `task_type_id = 0x02` (WDQ_GEMM), the `scalar0` field (word 0–1 [15:0]) carries the quantization group_size (max 128), replacing the removed `group_size` field.

#### 3.7 Per-Family Word Count and Active Fields

| Family | task_type_id | FAMILY Words | Active Fields in W0–1 | Active Fields in W2 |
|--------|-------------|-------------|----------------------|-------------------|
| GEMM | 0x05 | 3 | dim0_full_extent, dim1_full_extent, dim2_full_extent, dim0_tile_extent, dim1_tile_extent, dim2_tile_extent | cache_layout_class(act_dtype), cache_axis_order(weight_dtype), family_mode(accum_dtype), engine_profile, primary_surface_slot |
| SDPA | 0x03 | 3 | dim0_full_extent, dim1_full_extent, dim2_full_extent, dim0_tile_extent, dim1_tile_extent, dim2_tile_extent, extra_dim0, extra_tile0, extra_dim1, scalar0 | engine_profile, mask_cfg, primary_surface_slot |
| SDPA_DECODE | 0x04 | 3 | dim0_full_extent, dim1_full_extent, dim2_full_extent, dim0_tile_extent, dim1_tile_extent, dim2_tile_extent, extra_dim0, extra_tile0, extra_dim1, scalar0 | engine_profile, mask_cfg, family_mode(kv_operand), primary_surface_slot |
| KVLOAD | 0x09 | 3 | dim0_full_extent, dim1_full_extent, dim0_tile_extent, dim1_tile_extent, extra_dim0 | engine_profile, cache_layout_class, cache_axis_order, family_mode, primary_surface_slot, secondary_surface_slot |
| KVSTORE | 0x0A | 3 | dim0_full_extent, dim1_full_extent, dim0_tile_extent, extra_dim0, extra_dim1 | engine_profile, cache_layout_class, cache_axis_order, family_mode(append), primary_surface_slot(input), secondary_surface_slot(input) |
| RMSNORM | 0x01 | 2 | dim0_full_extent, extra_dim0, scalar0 | — |
| WDQ_GEMM | 0x02 | 3 | dim0_full_extent, dim1_full_extent, dim2_full_extent, dim0_tile_extent, dim1_tile_extent, dim2_tile_extent, scalar0(group_size) | engine_profile, primary_surface_slot |
| ELEM_ADD | 0x06 | 2 | dim0_full_extent, extra_dim0 | — |
| GEGLU | 0x07 | 2 | dim0_full_extent, extra_dim0, extra_dim1 | — |
| ROPE | 0x08 | 3 | dim0_full_extent, dim1_full_extent, extra_dim0, extra_dim1 | family_mode(position) |
| RMSNORM_GEMM | 0x0B | 3 | dim0_full_extent, dim1_full_extent, dim2_full_extent, dim0_tile_extent, dim1_tile_extent, dim2_tile_extent | engine_profile, primary_surface_slot |

### 3.8 BUFFER Record

Total: 256 bits = 4 words

Compacted from v0.9 5-word layout by removing two reserved gaps (bits 285:256 and 223:192) and packing `span`, `base_binding_lo`, `base_binding_hi` contiguously.

| Field | Bits | Width | Description |
|-------|------|-------|-------------|
| role | [255:252] | 4 | operand role enum (input=0x1, weight=0x2, output=0x3, scale=0x4, etc.) |
| address_space | [251:248] | 4 | address space enum (VMEM_ABSOLUTE=0x1, DDR=0x2) |
| access_mode | [247:245] | 3 | access mode (READ=0x1, WRITE=0x2, READ_WRITE=0x3) |
| layout_class | [244:241] | 4 | memory layout class (DENSE_ROW_MAJOR=0x1, DENSE_COL_MAJOR=0x2, STRIDED=0x3, TILED=0x4) |
| dim_count | [240:238] | 3 | number of active stride dimensions (max 3) |
| span | [237:222] | 16 | total size in bytes (max ~65535) |
| base_binding_lo | [221:190] | 32 | low 32 bits of base address; clean word-half for 32-bit hardware access |
| base_binding_hi | [189:158] | 32 | high 32 bits of base address; DDR addresses use both lo/hi; VMEM: must be zero |
| dim_0_extent | [157:142] | 16 | dimension 0 extent |
| dim_0_stride_lo | [141:126] | 16 | low 16 bits of dimension 0 stride in bytes |
| dim_0_stride_hi | [125:118] | 8 | high 8 bits of dim 0 stride; effective stride = stride_hi<<16 \| stride_lo |
| dim_1_extent | [117:102] | 16 | dimension 1 extent |
| dim_1_stride_lo | [101:86] | 16 | low 16 bits of dimension 1 stride in bytes |
| dim_1_stride_hi | [85:78] | 8 | high 8 bits of dim 1 stride; effective stride = stride_hi<<16 \| stride_lo |
| dim_2_extent | [77:62] | 16 | dimension 2 extent |
| dim_2_stride_lo | [61:46] | 16 | low 16 bits of dimension 2 stride in bytes |
| dim_2_stride_hi | [45:38] | 8 | high 8 bits of dim 2 stride; effective stride = stride_hi<<16 \| stride_lo |
| reserved | [37:0] | 38 | must be zero |

Active bits: 218. Reserved bits: 38.

### 3.9 LOOP Record

Variable-length: 1 or 2 words depending on `loop_rank`. Each slot occupies exactly 32 bits (matching TEMPLATE slot density).

| loop_rank | Slot Count | Total Bits | Words |
|-----------|-----------|------------|-------|
| 1 | 1 | 32 | 1 |
| 2 | 2 | 64 | 1 |
| 3 | 3 | 96 | 2 |

Per slot (32 bits):

| Field | Bits (within slot) | Width | Description |
|-------|--------------------|-------|-------------|
| dim_extent | [31:12] | 20 | loop dimension full extent |
| tile_extent | [11:4] | 8 | loop dimension tile size |
| axis_encoding | [3:0] | 4 | loop dimension axis enum |

Word-level layout (for loop_rank=3, 2 words):

**Word 0:**
- Slot 0: bits [63:32] — dim_extent[63:44], tile_extent[43:36], axis_encoding[35:32]
- Slot 1: bits [31:0] — dim_extent[31:12], tile_extent[11:4], axis_encoding[3:0]

**Word 1:**
- Slot 2: bits [31:0] — dim_extent[31:12], tile_extent[11:4], axis_encoding[3:0]
- Reserved: bits [63:32] — must be zero

### 3.10 TEMPLATE Record

Variable-length: ceil(template_slot_count × 32 / 64) words; absent if template_slot_count=0. Identical slot format to v0.9.

Per slot (32 bits):

| Field | Bits (within slot) | Width | Description |
|-------|--------------------|-------|-------------|
| kind | [31:30] | 2 | action_kind enum (nop=0x0, load=0x1, compute=0x2, store=0x3) |
| engine | [29:26] | 4 | engine_class enum (DMA=0x1, MXU=0x2, VPU=0x3, scalar/WDQ=0x4) |
| src_surface | [25:23] | 3 | source surface index |
| dst_surface | [22:20] | 3 | destination surface index |
| apply_scope | [19:17] | 3 | slot_apply_scope enum |
| dma_channel_hint | [16:14] | 3 | DMA channel hint (0=auto, 1–6=specific) |
| dma_burst_type | [13:12] | 2 | DMA burst type (0=default, 1=linear, 2=tiled) |
| fence_after | [11] | 1 | fence/barrier after slot completes |

| template_slot_count | Words |
|--------------------|-------|
| 1, 2 | 1 |
| 3, 4 | 2 |
| 5, 6 | 3 |
| 7 | 4 |

## 4. Fit Proof Summary

### GEMM (worst-case primary header + FAMILY)

primary_header=1 word + FAMILY=3 words = 4 words (256 bits). Well within any cache-line bound.

### Full Descriptor Size Comparison (typical: buffer_count=3, loop_rank=3, template_slot_count=4)

| Component | v0.9 Words | v0.10 Words | Savings |
|-----------|-----------|-------------|---------|
| Header + TASK | 2 | 1 (merged) | 1 |
| FAMILY | 4 (fixed) | 3 (variable) | 1 |
| BUFFER ×3 | 5×3=15 | 4×3=12 | 3 |
| LOOP | 3 (fixed) | 2 (variable) | 1 |
| TEMPLATE | 4 (slot_count=4 → 2 words) | 2 | 0 |
| **Total** | **28** | **20** | **8 (29%)** |

### FAMILY Bit Budget

- Word 0–1 active: ranges 10 fields across 128 bits, all with ≥2 family utilization
- Word 2 active: 7 fields = 26 bits; 38 bits reserved for expansion
- v0.9 FAMILY: 192 active bits in 256-bit fixed grid = 75% utilization
- v0.10 FAMILY (3-word): 128+26=154 active bits in 192 bits = 80% utilization
- v0.10 FAMILY (2-word): ranges 2–3 active fields in 128 bits; minimal fields avoid wasting word 2 entirely

## 5. Task Type ID Enumeration

| Family | task_type_id (hex) | Note |
|--------|--------------------|------|
| RMSNORM | 0x01 | FAMILY=2 words |
| WDQ_GEMM | 0x02 | FAMILY=3 words |
| SDPA | 0x03 | FAMILY=3 words |
| SDPA_DECODE | 0x04 | FAMILY=3 words |
| GEMM | 0x05 | FAMILY=3 words |
| ELEM_ADD | 0x06 | FAMILY=2 words |
| GEGLU | 0x07 | FAMILY=2 words |
| ROPE | 0x08 | FAMILY=3 words |
| KVLOAD | 0x09 | FAMILY=3 words |
| KVSTORE | 0x0A | FAMILY=3 words |
| RMSNORM_GEMM | 0x0B | FAMILY=3 words |

## 6. Parser / Packer / Verifier Rules

### Parser

1. Read primary_header (word 0) → extract descriptor_version, task_type_id, buffer_count, loop_rank, template_slot_count.
2. Derive FAMILY word count from task_type_id lookup (§5).
3. Read FAMILY record (family_words words).
4. Read BUFFER records: buffer_count × 4 words each.
5. Read LOOP record: ceil(loop_rank × 32 / 64) words.
6. If template_slot_count > 0: read TEMPLATE record: ceil(template_slot_count × 32 / 64) words.
7. Validate CRC-16/CCITT-FALSE over all words.

### Packer

1. Compute all field values from semantic and execution trace inputs.
2. Compute CRC-16/CCITT-FALSE over all words (crc16 field zeroed during computation, then replaced).
3. Pack primary_header (word 0).
4. Pack FAMILY record, BUFFER records, LOOP record, TEMPLATE record in order.

#### CRC-16 Specification

- **Algorithm:** CRC-16/CCITT-FALSE
- **Polynomial:** 0x1021
- **Init:** 0xFFFF
- **XorOut:** 0x0000
- **Reflection:** none
- **Check value:** 0x29B1
- **Covered scope:** all words in descriptor; crc field zeroed (0x0000) during computation
- **Byte order:** words serialized MSB-first (big-endian) for CRC computation

### Verifier

4 verification layers:

1. **Structural:** Word count consistent with derived lengths. FAMILY word count matches task_type_id. Buffer/loop/template word counts match their respective count fields.
2. **Reserved-bit:** All reserved bits are zero; VIOLATION on any non-zero reserved bit.
3. **Semantic:** All A1 family fields present and within range. task_type_id is valid. FAMILY word count matches task_type_id. Unused enum/surface fields in word 2 are must_be_zero per family.
4. **Round-trip:** Pack → Parse → Pack produces identical bit pattern. Any mismatch = VIOLATION.

## 7. Worked Examples Reference

Worked examples will be regenerated from v0.9 examples applying the optimization rules.

| Family | Record Type | PRIMARY_HEADER + FAMILY | BUFFER | LOOP | TEMPLATE |
|--------|------------|------------------------|--------|------|----------|
| GEMM | 3-buf | 1+3=4 | 4×3=12 | 2 | — |
| SDPA | 4-buf | 1+3=4 | 4×4=16 | 2 | 2 |
| SDPA_DECODE | 4-buf | 1+3=4 | 4×4=16 | 2 | 2 |
| KVLOAD | 4-buf | 1+3=4 | 4×4=16 | 2 | 2 |
| KVSTORE | 3-buf | 1+3=4 | 4×3=12 | 2 | 2 |
| RMSNORM | 1-buf | 1+2=3 | 4×1=4 | 1 | — |
| WDQ_GEMM | 3-buf | 1+3=4 | 4×3=12 | 2 | 2 |
| ELEM_ADD | 2-buf | 1+2=3 | 4×2=8 | 1 | — |
| GEGLU | 2-buf | 1+2=3 | 4×2=8 | 1 | — |
| ROPE | 2-buf | 1+3=4 | 4×2=8 | 1 | — |
| RMSNORM_GEMM | 3-buf | 1+3=4 | 4×3=12 | 2 | 2 |
