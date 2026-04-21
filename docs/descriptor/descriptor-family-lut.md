# Per-Family Schema LUT Summary — v0.10

**Descriptor version:** 0x6 (v0.10)
**Scope:** FAMILY record only (PRIMARY_HEADER / BUFFER / LOOP / TEMPLATE schemas remain canonical in the encoding layout document).

FAMILY record is variable-length: words 0–1 (128 bits) always present; word 2 (64 bits) present only for families that need enumeration/surface fields. The `family_mode` field at word 2 [47:44] is a **neutral dispatch-first slot**. Its semantic alias is resolved only after `task_type_id` dispatch. Non-owning families must leave this slot at `0x0` (must_be_zero).

## GEMM

- **task_type_id:** 0x05
- **FAMILY words:** 3
- **Active fields (W0–1):** 6
- **Active fields (W2):** 5
- **must_be_zero positions:** 10

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | m | 16 |
| 111:96 | dim1_full_extent | n | 16 |
| 95:80 | dim2_full_extent | k | 16 |
| 79:72 | dim0_tile_extent | tile_m | 8 |
| 71:64 | dim1_tile_extent | tile_n | 8 |
| 63:56 | dim2_tile_extent | tile_k | 8 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 63:60 | engine_profile | engine_profile | 4 |
| 55:52 | cache_layout_class | act_dtype (repurposed from dtype0) | 4 |
| 51:48 | cache_axis_order | weight_dtype (repurposed from dtype1) | 4 |
| 47:44 | family_mode | accum_dtype (dispatched alias; repurposed from dtype2) | 4 |
| 43:41 | primary_surface_slot | primary_output_surface | 3 |

### Must-Be-Zero Positions (10)

- W0–1: extra_dim0 [55:40], extra_tile0 [39:32], extra_dim1 [31:16], scalar0 [15:0]
- W2: mask_cfg [59:56], secondary_surface_slot [40:38], reserved [37:0]

### Repurposing Notes

- `cache_layout_class`[55:52] = GEMM act_dtype (was v0.9 dtype0). Encoding values identical to v0.9 dtype enum.
- `cache_axis_order`[51:48] = GEMM weight_dtype (was v0.9 dtype1). Encoding values identical to v0.9 dtype enum.
- `family_mode`[47:44] = GEMM accum_dtype (was v0.9 dtype2). Encoding values identical to v0.9 dtype enum.

## SDPA

- **task_type_id:** 0x03
- **FAMILY words:** 3
- **Active fields (W0–1):** 10
- **Active fields (W2):** 3
- **must_be_zero positions:** 8

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | num_heads | 16 |
| 111:96 | dim1_full_extent | query_len | 16 |
| 95:80 | dim2_full_extent | kv_len | 16 |
| 79:72 | dim0_tile_extent | tile_query | 8 |
| 71:64 | dim1_tile_extent | dim1_tile_extent | 8 |
| 63:56 | dim2_tile_extent | tile_kv | 8 |
| 55:40 | extra_dim0 | head_dim | 16 |
| 39:32 | extra_tile0 | tile_head_dim | 8 |
| 31:16 | extra_dim1 | num_kv_heads | 16 |
| 15:0 | scalar0 | softmax_scale | 16 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 63:60 | engine_profile | engine_profile | 4 |
| 59:56 | mask_cfg | mask_cfg | 4 |
| 43:41 | primary_surface_slot | primary_output_surface | 3 |

### Must-Be-Zero Positions (8)

- W0–1: (none — all 10 fields active)
- W2: cache_layout_class [55:52], cache_axis_order [51:48], family_mode [47:44], secondary_surface_slot [40:38], reserved [37:0]

## SDPA_DECODE

- **task_type_id:** 0x04
- **FAMILY words:** 3
- **Active fields (W0–1):** 10
- **Active fields (W2):** 4
- **must_be_zero positions:** 7

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | num_heads | 16 |
| 111:96 | dim1_full_extent | query_len | 16 |
| 95:80 | dim2_full_extent | kv_len | 16 |
| 79:72 | dim0_tile_extent | tile_query | 8 |
| 71:64 | dim1_tile_extent | dim1_tile_extent | 8 |
| 63:56 | dim2_tile_extent | tile_kv | 8 |
| 55:40 | extra_dim0 | head_dim | 16 |
| 39:32 | extra_tile0 | tile_head_dim | 8 |
| 31:16 | extra_dim1 | num_kv_heads | 16 |
| 15:0 | scalar0 | softmax_scale | 16 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 63:60 | engine_profile | engine_profile | 4 |
| 59:56 | mask_cfg | mask_cfg | 4 |
| 47:44 | family_mode | kv_operand_binding_mode (dispatched alias; repurposed from v0.9 kv_operand_binding_mode) | 4 |
| 43:41 | primary_surface_slot | primary_output_surface | 3 |

### Must-Be-Zero Positions (7)

- W0–1: (none)
- W2: cache_layout_class [55:52], cache_axis_order [51:48], secondary_surface_slot [40:38], reserved [37:0]

### Repurposing Notes

- `family_mode`[47:44] = SDPA_DECODE kv_operand_binding_mode. Encoding values identical to v0.9.

## KVLOAD

- **task_type_id:** 0x09
- **FAMILY words:** 3
- **Active fields (W0–1):** 5
- **Active fields (W2):** 6
- **must_be_zero positions:** 7

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | kv_len | 16 |
| 111:96 | dim1_full_extent | num_kv_heads | 16 |
| 79:72 | dim0_tile_extent | tile_kv | 8 |
| 71:64 | dim1_tile_extent | dim1_tile_extent | 8 |
| 55:40 | extra_dim0 | head_dim | 16 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 63:60 | engine_profile | engine_profile | 4 |
| 55:52 | cache_layout_class | cache_layout_class | 4 |
| 51:48 | cache_axis_order | cache_axis_order | 4 |
| 47:44 | family_mode | source_binding_mode (dispatched alias; unchanged) | 4 |
| 43:41 | primary_surface_slot | primary_output_surface | 3 |
| 40:38 | secondary_surface_slot | secondary_output_surface | 3 |

### Must-Be-Zero Positions (7)

- W0–1: dim2_full_extent [95:80], dim2_tile_extent [63:56], extra_tile0 [39:32], extra_dim1 [31:16], scalar0 [15:0]
- W2: mask_cfg [59:56], reserved [37:0]

## KVSTORE

- **task_type_id:** 0x0A
- **FAMILY words:** 3
- **Active fields (W0–1):** 5
- **Active fields (W2):** 6
- **must_be_zero positions:** 7

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | kv_len_before | 16 |
| 111:96 | dim1_full_extent | num_kv_heads | 16 |
| 79:72 | dim0_tile_extent | tile_kv | 8 |
| 55:40 | extra_dim0 | head_dim | 16 |
| 31:16 | extra_dim1 | kv_len_after | 16 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 63:60 | engine_profile | engine_profile | 4 |
| 55:52 | cache_layout_class | cache_layout_class | 4 |
| 51:48 | cache_axis_order | cache_axis_order | 4 |
| 47:44 | family_mode | append_mode (dispatched alias; repurposed from v0.9 append_mode) | 4 |
| 43:41 | primary_surface_slot | primary_input_surface (dispatched alias; repurposed) | 3 |
| 40:38 | secondary_surface_slot | secondary_input_surface (dispatched alias; repurposed) | 3 |

### Must-Be-Zero Positions (7)

- W0–1: dim2_full_extent [95:80], dim1_tile_extent [71:64], dim2_tile_extent [63:56], extra_tile0 [39:32], scalar0 [15:0]
- W2: mask_cfg [59:56], reserved [37:0]

### Repurposing Notes

- `family_mode`[47:44] = KVSTORE append_mode. Encoding values identical to v0.9.
- `primary_surface_slot`[43:41] = KVSTORE primary_input_surface (was v0.9 primary_input_surface).
- `secondary_surface_slot`[40:38] = KVSTORE secondary_input_surface (was v0.9 secondary_input_surface).

## RMSNORM

- **task_type_id:** 0x01
- **FAMILY words:** 2
- **Active fields (W0–1):** 3
- **Active fields (W2):** —
- **must_be_zero positions:** 7

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | m | 16 |
| 55:40 | extra_dim0 | hidden_dim | 16 |
| 15:0 | scalar0 | epsilon | 16 |

### Must-Be-Zero Positions (7)

- W0–1: dim1_full_extent [111:96], dim2_full_extent [95:80], dim0_tile_extent [79:72], dim1_tile_extent [71:64], dim2_tile_extent [63:56], extra_tile0 [39:32], extra_dim1 [31:16]

## WDQ_GEMM

- **task_type_id:** 0x02
- **FAMILY words:** 3
- **Active fields (W0–1):** 7
- **Active fields (W2):** 2
- **must_be_zero positions:** 8

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | m | 16 |
| 111:96 | dim1_full_extent | n | 16 |
| 95:80 | dim2_full_extent | k | 16 |
| 79:72 | dim0_tile_extent | tile_m | 8 |
| 71:64 | dim1_tile_extent | tile_n | 8 |
| 63:56 | dim2_tile_extent | dim2_tile_extent | 8 |
| 15:0 | scalar0 | group_size (repurposed from v0.9 group_size field; max 128) | 16 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 63:60 | engine_profile | engine_profile | 4 |
| 43:41 | primary_surface_slot | primary_output_surface | 3 |

### Must-Be-Zero Positions (8)

- W0–1: extra_dim0 [55:40], extra_tile0 [39:32], extra_dim1 [31:16]
- W2: mask_cfg [59:56], cache_layout_class [55:52], cache_axis_order [51:48], family_mode [47:44], secondary_surface_slot [40:38], reserved [37:0]

### Repurposing Notes

- `scalar0`[15:0] = WDQ_GEMM group_size (was v0.9 group_size[83:76], 8 bits). Now 16-bit to match scalar0 width; upper bits must_be_zero for group_size ≤ 128.

## ELEM_ADD

- **task_type_id:** 0x06
- **FAMILY words:** 2
- **Active fields (W0–1):** 2
- **Active fields (W2):** —
- **must_be_zero positions:** 8

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | m | 16 |
| 55:40 | extra_dim0 | hidden_dim | 16 |

### Must-Be-Zero Positions (8)

- W0–1: dim1_full_extent [111:96], dim2_full_extent [95:80], dim0_tile_extent [79:72], dim1_tile_extent [71:64], dim2_tile_extent [63:56], extra_tile0 [39:32], extra_dim1 [31:16], scalar0 [15:0]

## GEGLU

- **task_type_id:** 0x07
- **FAMILY words:** 2
- **Active fields (W0–1):** 3
- **Active fields (W2):** —
- **must_be_zero positions:** 7

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | m | 16 |
| 55:40 | extra_dim0 | hidden_dim | 16 |
| 31:16 | extra_dim1 | intermediate_dim | 16 |

### Must-Be-Zero Positions (7)

- W0–1: dim1_full_extent [111:96], dim2_full_extent [95:80], dim0_tile_extent [79:72], dim1_tile_extent [71:64], dim2_tile_extent [63:56], extra_tile0 [39:32], scalar0 [15:0]

## ROPE

- **task_type_id:** 0x08
- **FAMILY words:** 3
- **Active fields (W0–1):** 4
- **Active fields (W2):** 1
- **must_be_zero positions:** 9

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | seq_len | 16 |
| 111:96 | dim1_full_extent | dim1_full_extent | 16 |
| 55:40 | extra_dim0 | head_dim | 16 |
| 31:16 | extra_dim1 | num_heads | 16 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 47:44 | family_mode | position_mode (dispatched alias; repurposed from v0.9 position_mode) | 4 |

### Must-Be-Zero Positions (9)

- W0–1: dim2_full_extent [95:80], dim0_tile_extent [79:72], dim1_tile_extent [71:64], dim2_tile_extent [63:56], extra_tile0 [39:32], scalar0 [15:0]
- W2: engine_profile [63:60], mask_cfg [59:56], cache_layout_class [55:52], cache_axis_order [51:48], reserved [37:0]

### Repurposing Notes

- `family_mode`[47:44] = ROPE position_mode. Encoding values identical to v0.9.

## RMSNORM_GEMM

- **task_type_id:** 0x0B
- **FAMILY words:** 3
- **Active fields (W0–1):** 6
- **Active fields (W2):** 2
- **must_be_zero positions:** 8

### Active Fields

#### Word 0–1

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 127:112 | dim0_full_extent | m | 16 |
| 111:96 | dim1_full_extent | n | 16 |
| 95:80 | dim2_full_extent | hidden_k | 16 |
| 79:72 | dim0_tile_extent | tile_m | 8 |
| 71:64 | dim1_tile_extent | tile_n | 8 |
| 63:56 | dim2_tile_extent | tile_k | 8 |

#### Word 2

| Bits | Field | Semantic | Width |
|------|-------|----------|-------|
| 63:60 | engine_profile | engine_profile | 4 |
| 43:41 | primary_surface_slot | primary_output_surface | 3 |

### Must-Be-Zero Positions (8)

- W0–1: extra_dim0 [55:40], extra_tile0 [39:32], extra_dim1 [31:16], scalar0 [15:0]
- W2: mask_cfg [59:56], cache_layout_class [55:52], cache_axis_order [51:48], family_mode [47:44], secondary_surface_slot [40:38], reserved [37:0]
