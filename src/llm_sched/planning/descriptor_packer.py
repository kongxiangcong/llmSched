"""Deterministic 512-bit descriptor packer foundation for SPEC-12."""

from __future__ import annotations

from typing import Iterable

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.packed_descriptor_bundle import (
    PackedDescriptorBundle,
    PackedDescriptorFieldPlacement,
    PackedDescriptorRecord,
    assemble_bundle_stream_hex,
    serialize_stream_hex,
)
from llm_sched.ir.descriptor_ir import AddressField, DescriptorIR, DescriptorRecord


_OPCODE_CODES = {
    "DMA_LOAD": 1,
    "DMA_STORE": 2,
    "VPU_PREPARE": 3,
    "DMA_TRANSFER": 4,
    "CORE_LINK_COPY": 5,
    "GEMM": 16,
    "WDQ_GEMM": 17,
    "RMSNORM": 18,
    "RMSNORM_GEMM": 19,
    "ROPE": 20,
    "SDPA": 21,
    "GEGLU": 22,
    "ELEM_ADD": 23,
    "KVSTORE": 24,
    "KVLOAD": 25,
    "SDPA_DECODE": 26,
}

_STAGE_CODES = {
    "compute": 1,
    "prepare": 2,
    "dma_in": 3,
    "store": 4,
    "transfer": 5,
}

_SCENARIO_CODES = {
    "prefill": 1,
    "decode": 2,
}

_TRANSFER_KIND_CODES = {
    "dma": 1,
    "core_link": 2,
}


def pack_descriptor_bundle(
    descriptor_ir: DescriptorIR,
    hardware: TargetProfile | ArchitectureCapabilities,
) -> PackedDescriptorBundle:
    capabilities = (
        hardware
        if isinstance(hardware, ArchitectureCapabilities)
        else ArchitectureCapabilities.from_target_profile(hardware)
    )
    payloads: list[PackedDescriptorRecord] = []
    record_alignment_bytes = capabilities.descriptor_encoding.record_alignment_bytes
    record_size_bytes = capabilities.descriptor_encoding.total_bits // 8
    next_offset_bytes = 0
    for record_index, descriptor in enumerate(descriptor_ir.descriptors):
        stream_offset_bytes = _align_up(next_offset_bytes, record_alignment_bytes)
        payloads.append(
            _pack_descriptor_record(
                descriptor,
                capabilities,
                record_index=record_index,
                stream_offset_bytes=stream_offset_bytes,
                stream_size_bytes=record_size_bytes,
            )
        )
        next_offset_bytes = stream_offset_bytes + record_size_bytes
    stream_total_bytes = next_offset_bytes
    return PackedDescriptorBundle(
        graph_id=descriptor_ir.graph_id,
        encoding_bits=capabilities.descriptor_encoding.total_bits,
        container_format=capabilities.descriptor_encoding.stream_container,
        record_alignment_bytes=record_alignment_bytes,
        stream_total_bytes=stream_total_bytes,
        stream_hex=assemble_bundle_stream_hex(payloads, stream_total_bytes),
        descriptors=payloads,
    )


def _pack_descriptor_record(
    descriptor: DescriptorRecord,
    capabilities: ArchitectureCapabilities,
    *,
    record_index: int,
    stream_offset_bytes: int,
    stream_size_bytes: int,
) -> PackedDescriptorRecord:
    entry_map = _packing_entry_map(descriptor, capabilities)
    entries = list(_ordered_entries(descriptor, entry_map))
    expected_bits = descriptor.encoding_bits
    cursor = 0
    words = [0] * (expected_bits // 64)
    placements: list[PackedDescriptorFieldPlacement] = []

    for field_name, field_group, bit_width, value in entries:
        if cursor + bit_width > expected_bits:
            raise ValueError(
                f"descriptor {descriptor.descriptor_id} packed fields exceed encoding_bits"
            )
        _write_bits(words, cursor, bit_width, value)
        placements.append(
            PackedDescriptorFieldPlacement(
                field_name=field_name,
                field_group=field_group,
                word_index=cursor // 64,
                bit_offset=cursor,
                bit_width=bit_width,
                value_hex=_value_hex(value, bit_width),
            )
        )
        cursor += bit_width

    word_hex = [f"0x{word:016x}" for word in words]
    packed_hex = "0x" + "".join(word[2:] for word in reversed(word_hex))
    stream_hex = serialize_stream_hex(
        word_hex,
        word_order=capabilities.descriptor_encoding.word_order,
        byte_order=capabilities.descriptor_encoding.byte_order,
    )
    return PackedDescriptorRecord(
        descriptor_id=descriptor.descriptor_id,
        schedule_block_id=descriptor.schedule_block_id,
        opcode=descriptor.opcode,
        core_id=descriptor.core_id,
        stage=str(descriptor.ctrl_fields["stage"]),
        layout_template=descriptor.packing_profile.layout_template,
        encoding_bits=descriptor.encoding_bits,
        record_index=record_index,
        stream_offset_bytes=stream_offset_bytes,
        stream_size_bytes=stream_size_bytes,
        word_order=capabilities.descriptor_encoding.word_order,
        byte_order=capabilities.descriptor_encoding.byte_order,
        word_hex=word_hex,
        packed_hex=packed_hex,
        stream_hex=stream_hex,
        field_placements=placements,
    )


def _packing_entry_map(
    descriptor: DescriptorRecord,
    capabilities: ArchitectureCapabilities,
) -> dict[str, tuple[str, int, int]]:
    field_widths = descriptor.packing_profile.field_widths
    entries: dict[str, tuple[str, int, int]] = {}
    for group in descriptor.packing_profile.field_groups:
        if group == "ctrl":
            entries["opcode"] = ("ctrl", field_widths["opcode"], _opcode_code(descriptor.opcode))
            entries["control"] = ("ctrl", field_widths["control"], _control_word(descriptor))
            if "order_key" in field_widths:
                entries["order_key"] = (
                    "ctrl",
                    field_widths["order_key"],
                    int(descriptor.ctrl_fields.get("order_key", 0)),
                )
            if "group_size" in field_widths:
                entries["group_size"] = (
                    "ctrl",
                    field_widths["group_size"],
                    int(descriptor.ctrl_fields.get("group_size", 0)),
                )
        elif group == "shape":
            for axis in ("m", "n", "k"):
                key = f"shape_{axis}"
                if key in field_widths:
                    entries[key] = ("shape", field_widths[key], int(descriptor.shape_pack.get(axis, 0)))
        elif group == "addr":
            for field in descriptor.address_fields:
                low_key = _address_field_width_key(field)
                low_value, high_value = _address_words(field, capabilities)
                entries[low_key] = ("addr", field_widths[low_key], low_value)
                high_key = _address_field_hi_key(field)
                if high_key in field_widths:
                    entries[high_key] = ("addr", field_widths[high_key], high_value)
        elif group == "dma":
            for name in ("dma_length", "dma_channel", "dma_priority"):
                if name in field_widths:
                    source_name = name.removeprefix("dma_")
                    entries[name] = ("dma", field_widths[name], int(descriptor.dma_fields.get(source_name, 0)))
        elif group == "transfer" and descriptor.transfer_fields is not None:
            if "transfer_kind" in field_widths:
                entries["transfer_kind"] = (
                    "transfer",
                    field_widths["transfer_kind"],
                    _TRANSFER_KIND_CODES.get(descriptor.transfer_fields.kind, 0),
                )
            if "transfer_src_core_id" in field_widths:
                entries["transfer_src_core_id"] = (
                    "transfer",
                    field_widths["transfer_src_core_id"],
                    descriptor.transfer_fields.src_core_id,
                )
            if "transfer_dst_core_id" in field_widths:
                entries["transfer_dst_core_id"] = (
                    "transfer",
                    field_widths["transfer_dst_core_id"],
                    descriptor.transfer_fields.dst_core_id,
                )
            if "transfer_bytes" in field_widths:
                entries["transfer_bytes"] = (
                    "transfer",
                    field_widths["transfer_bytes"],
                    descriptor.transfer_fields.transfer_bytes,
                )
    return entries


def _ordered_entries(
    descriptor: DescriptorRecord,
    entry_map: dict[str, tuple[str, int, int]],
) -> Iterable[tuple[str, str, int, int]]:
    field_layout = descriptor.packing_profile.field_layout
    ordered_names = field_layout if field_layout else list(entry_map)
    for field_name in ordered_names:
        if field_name not in entry_map:
            raise ValueError(
                f"descriptor {descriptor.descriptor_id} field_layout references unknown field {field_name}"
            )
        field_group, bit_width, value = entry_map[field_name]
        yield field_name, field_group, bit_width, value


def _opcode_code(opcode: str) -> int:
    return _OPCODE_CODES.get(opcode, 255)


def _control_word(descriptor: DescriptorRecord) -> int:
    stage = str(descriptor.ctrl_fields.get("stage", "compute"))
    scenario = str(descriptor.ctrl_fields.get("scenario_mode", "prefill"))
    peer_core_id = int(descriptor.ctrl_fields.get("peer_core_id", 0))
    control = _STAGE_CODES.get(stage, 0)
    control |= _SCENARIO_CODES.get(scenario, 0) << 4
    control |= int(descriptor.core_id) << 8
    control |= peer_core_id << 10
    if descriptor.transfer_fields is not None:
        control |= 1 << 14
    return control


def _address_field_width_key(field: AddressField) -> str:
    key = field.descriptor_field.lower()
    if field.encoded_width_bits < 64:
        return f"{key}_low"
    return key


def _address_field_hi_key(field: AddressField) -> str:
    key = field.descriptor_field.lower()
    if key.endswith("_low"):
        key = key[: -len("_low")]
    return f"{key}_hi"


def _address_words(
    field: AddressField,
    capabilities: ArchitectureCapabilities,
) -> tuple[int, int]:
    full_value = _absolute_address_value(field, capabilities)
    low_mask = _mask(field.encoded_width_bits)
    low_value = full_value & low_mask
    high_value = full_value >> field.encoded_width_bits if field.uses_addr_ext else 0
    return low_value, high_value


def _absolute_address_value(
    field: AddressField,
    capabilities: ArchitectureCapabilities,
) -> int:
    if field.address_space == "DDR":
        return field.offset_bytes
    return _vmem_region_base_bytes(field.region_name, capabilities) + field.offset_bytes


def _vmem_region_base_bytes(
    region_name: str | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    if region_name is None:
        return 0
    offset_bytes = 0
    for name, size_kb in capabilities.vmem.regions.items():
        if name == region_name:
            return offset_bytes
        offset_bytes += int(size_kb) * 1024
    raise ValueError(f"unknown VMEM region {region_name} in packed descriptor builder")


def _write_bits(words: list[int], bit_offset: int, bit_width: int, value: int) -> None:
    masked_value = value & _mask(bit_width)
    remaining = bit_width
    cursor = bit_offset
    while remaining > 0:
        word_index = cursor // 64
        word_offset = cursor % 64
        writable = min(remaining, 64 - word_offset)
        chunk_mask = _mask(writable)
        chunk = masked_value & chunk_mask
        words[word_index] |= chunk << word_offset
        masked_value >>= writable
        cursor += writable
        remaining -= writable


def _mask(bit_width: int) -> int:
    if bit_width >= 63:
        return (1 << bit_width) - 1
    return (1 << bit_width) - 1


def _value_hex(value: int, bit_width: int) -> str:
    hex_width = max(1, (bit_width + 3) // 4)
    return f"0x{value & _mask(bit_width):0{hex_width}x}"


def _align_up(value: int, alignment: int) -> int:
    remainder = value % alignment
    if remainder == 0:
        return value
    return value + (alignment - remainder)
