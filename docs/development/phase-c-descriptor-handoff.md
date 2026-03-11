# Phase C Descriptor Handoff

## 2026-03-11 Address Storage Metadata Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-descriptor-address-storage-reuse.md`
- structured `address_fields` now carry optional `storage_binding_id` and `backing_store`
- descriptor generation now copies these fields directly from `memory_plan.allocations[*]` when the address role is allocation-backed
- focused descriptor-builder regression now proves compute descriptors preserve staged-weight versus VMEM-local output provenance without reopening raw planner tables

## 2026-03-07 Checkpoint

- `SPEC-12` has started with a stable first-pass `DescriptorIR`.
- `run-descriptor-generation` is now the standalone run-root workflow and CLI command for descriptor and ISA coverage artifacts.
- Gemma3 `single-core/dual-core x prefill/decode` smoke now produces deterministic descriptor artifacts and coverage reports.

## 1. What Is Stable Now

The current `SPEC-12` foundation consumes:
- `bound_nig_ir.json`
- `artifacts/memory_plan.json`
- `artifacts/schedule_ir.json` or `artifacts/dual_core_schedule_ir.json`
- target profile
- scenario profile

It produces:
- `artifacts/descriptor_ir.json`
- `artifacts/packed_descriptor_bundle.json`
- `reports/isa_coverage_report.json`
- `manifest.artifact_index["descriptor_ir"]`
- `manifest.artifact_index["packed_descriptor_bundle"]`
- `manifest.artifact_index["isa_coverage_report"]`
- completed or failed `run-summary.json` updates through the descriptor-generation workflow

This foundation is intentionally deterministic. It now performs target-aware 512-bit payload packing and emits both a descriptor-view payload and a driver-stream view, but it still stops short of a firmware container or transport-specific record format.

## 2. Stable Contract

The current `DescriptorIR` now carries:
- `descriptor_id`
- `schedule_block_id`
- `opcode`
- `core_id`
- `encoding_bits`
- `ctrl_fields`
- `packing_profile`
- `shape_pack`
- `addr_fields`
- `address_fields`
- `dma_fields`
- `transfer_fields`
- `source_ref`
- `audit_ref`

Current invariants:
- `descriptor_id` must be unique
- `schedule_block_id` must be unique across descriptors
- transfer descriptors must carry `kind`, `src_core_id`, `dst_core_id`, and `transfer_bytes`
- descriptor-level `audit_ref.schedule_block_ids` must preserve schedule traceability

The current `ISACoverageReport` now carries:
- `mapped_descriptor_count`
- `unmapped_block_count`
- `opcode_counts`
- `gap_counts`
- per-block `issues`

The current packed payload artifact now carries:
- one packed record per mapped descriptor
- `8 x 64-bit` descriptor words
- one concatenated `packed_hex` payload
- one target-facing `stream_hex` payload
- explicit `word_order` and `byte_order`
- per-field bit placements for control / shape / address / DMA / transfer groups

Current descriptor completeness guarantees:
- every descriptor carries explicit `ctrl_fields["stage"]`
- every descriptor carries explicit `packing_profile`
- `packing_profile.stage_family` must match the descriptor stage family
- `packing_profile.required_*` fields must be satisfiable from the descriptor payload
- compute and prepare descriptors carry non-empty `shape_pack`
- DMA-family descriptors carry non-empty `addr_fields`
- symbolic `addr_fields` and structured `address_fields` must agree on role coverage and symbols
- allocation-backed `address_fields` preserve `storage_binding_id/backing_store` when that provenance exists in `MemoryPlanArtifact`
- DMA-family descriptors carry positive `dma_fields.length`
- transfer descriptors carry explicit `transfer_fields`

## 3. Current Mapping Policy

The first-pass descriptor builder currently maps:
- compute blocks: `macro_op -> opcode`
- `dma_in`: `DMA_LOAD`
- `store`: `DMA_STORE`
- `prepare`: `VPU_PREPARE`
- `transfer` with `core_link`: `CORE_LINK_COPY`
- `transfer` with `dma`: `DMA_TRANSFER`

Current shape policy:
- prefer parsing `m/n/k` from `tiling_candidate_id`
- fall back to bound-NIG resolved shape when tile metadata is absent

Current address policy:
- reuse `buffer_binding` as symbolic address fields
- normalize VMEM names as `VMEM:<region>`
- also emit structured `address_fields` with `role/address_space/region_name/offset_bytes/symbol` plus `storage_binding_id/backing_store` when the field comes from a planned allocation
- keep both symbolic and structured forms deterministic until later descriptor packing work freezes real field formats

Current packing-profile policy:
- every descriptor now carries a stage-aware `packing_profile`
- compute descriptors use `"<opcode>_compute"` opcode families
- prepare descriptors use `vpu_prepare`
- DMA load/store descriptors use `dma_load` / `dma_store`
- transfer descriptors use `core_link_transfer` or `dma_transfer`
- the profile now stays symbolic at the `DescriptorIR` layer but is detailed enough for deterministic field placement
- every descriptor now also carries a `layout_template` and deterministic field-level `field_widths`
- every descriptor now also carries an explicit `field_layout`
- every structured address field now carries `descriptor_field`, `encoded_width_bits`, and `uses_addr_ext`
- compute / DMA / transfer profiles now expose per-axis and per-transfer widths such as `shape_m`, `shape_n`, `shape_k`, `order_key`, and `transfer_bytes`

Current target-facing encoding policy:
- target profiles now expose a default `descriptor_encoding` contract
- target profiles now also expose `word_order` and `byte_order` defaults for descriptor streaming
- builder specializes descriptor field widths against that contract instead of using scattered magic numbers
- compute descriptors now map logical roles into target-facing fields such as `WEIGHT_ADDR`, `ACT_ADDR`, `SCALE_ADDR`, `ZP_ADDR`, and `DST_ADDR`
- transfer descriptors now map logical roles into `SRC_ADDR` and `DST_ADDR`
- VMEM local offsets are validated against the declared encoded field width
- DDR low-width address fields must explicitly opt into `ADDR_EXT_HI` relocation via `uses_addr_ext`

Current packed-payload policy:
- `run-descriptor-generation` now also emits `packed_descriptor_bundle.json`
- payload packing is deterministic within a fixed 512-bit descriptor view
- every packed descriptor exports `8 x 64-bit` words plus a concatenated `packed_hex`
- every packed descriptor now also exports a target-facing `stream_hex` derived from `word_order` and `byte_order`
- packed payloads preserve field-level traceability through explicit bit-placement metadata
- this is still an architecture-evaluation artifact, not yet a promise that the final firmware container or transport ABI is frozen

Current DMA field policy:
- `dma_in` and `store` derive positive `length` fields from memory-plan allocations
- `transfer` uses `transfer_bytes` directly
- all DMA-family descriptors keep deterministic `channel=0` and `priority=1` until later packing work freezes final policies

Current ISA gap policy:
- compute opcode misses are reported as `compute_opcode_not_supported`
- prepare-stage hardware misses are reported as `prepare_vpu_not_available`
- DMA stage misses are reported as `dma_stage_not_available`
- transfer transport misses are reported as `transfer_core_link_not_available` or `transfer_dma_not_available`

Unsupported schedule blocks are not dropped silently. They go to `isa_coverage_report` as explicit gaps.

## 4. What SPEC-13 Can Assume

Performance estimation may now assume:
- schedule-to-descriptor traceability is explicit
- single-core and dual-core runs both produce a stable descriptor artifact
- unsupported schedule blocks are surfaced as ISA gaps instead of disappearing
- descriptor records already expose stage, shape, symbolic address bindings, and transfer metadata

`SPEC-13` should not need to rediscover:
- which schedule block produced a descriptor
- whether a cross-core handoff used `DMA` or `Core Link`
- whether a block failed due to an ISA gap versus a planner omission

## 5. What Is Still Missing

The remaining gap is now an accepted stop-line, not a broad missing-foundation list:
- richer opcode-family specialization and firmware-facing record/container policy are now post-`M2` unless a concrete downstream consumer requires them
- per-record workbench drilldown is not required for the current `M2` stop-line
- the accepted `M2` bar is stable packed-stream artifacts plus summary-grade packed consumer proof and workbench visibility

What is no longer missing:
- target-facing descriptor encoding defaults in `TargetProfile`
- deterministic layout-template selection per stage/opcode family
- explicit address-field metadata suitable for later binary packing
- explicit coverage gaps when descriptor address encoding does not fit the target contract
- deterministic packed 512-bit payload emission for mapped descriptors
- target-facing stream serialization metadata and deterministic `stream_hex` emission
- explicit field-order metadata that keeps builder and packer aligned

These are `SPEC-12` acceptance-boundary items or `SPEC-13` work, not reasons to reopen the scheduler contracts.

## 6. Recommended Next Step

Next work should keep `SPEC-12` in stop-line mode:
1. Keep `DescriptorIR`, `packed_descriptor_bundle.json`, and `isa_coverage_report.json` stable as the accepted Phase C contract.
2. Treat packed summary consumer proof plus workbench summary visibility as sufficient for `M2`.
3. Only extend per-record drilldown, firmware-facing container policy, or heavier opcode specialization when a concrete downstream consumer requires it.

## 2026-03-08 Container ABI Checkpoint

- `SPEC-12` remains `in_progress`, but the packed descriptor artifact is now stable enough to be consumed as an aligned stream contract, not just as isolated per-record payloads.
- New closure evidence:
  - target profiles now carry `descriptor_encoding.stream_container`
  - target profiles now carry `descriptor_encoding.record_alignment_bytes`
  - packed descriptor bundles now carry bundle-level stream metadata:
    - `container_format`
    - `record_alignment_bytes`
    - `stream_total_bytes`
    - `stream_hex`
  - every packed descriptor record now carries transport-facing position metadata:
    - `record_index`
    - `stream_offset_bytes`
    - `stream_size_bytes`
  - `DescriptorPackingProfile` now validates stronger layout-template semantics for:
  - `wdq_compute_v1`
  - `rmsnorm_gemm_compute_v1`
  - `dma_load_v1`
  - `dma_store_v1`
  - `core_link_transfer_v1`
  - `dma_transfer_v1`
    - `vpu_prepare_v1`
- What is no longer missing:
  - explicit byte-order policy
  - explicit record ordering
  - explicit aligned stream assembly
  - explicit bundle-level stream payload
- Remaining `SPEC-12` gap:
  - richer opcode-family specialization beyond the current layout-template rules
  - proof that later Phase C / Phase D consumers can use the packed stream as a first-class contract without reconstructing symbolic placement assumptions
