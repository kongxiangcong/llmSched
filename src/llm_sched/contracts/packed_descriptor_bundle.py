"""Packed descriptor artifact contract for SPEC-12 binary-packer foundation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PackedFieldGroup = Literal["ctrl", "shape", "addr", "dma", "transfer"]


class PackedDescriptorFieldPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1)
    field_group: PackedFieldGroup
    word_index: int = Field(ge=0)
    bit_offset: int = Field(ge=0)
    bit_width: int = Field(gt=0)
    value_hex: str = Field(min_length=3, pattern=r"^0x[0-9a-f]+$")


class PackedDescriptorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descriptor_id: str = Field(min_length=1)
    schedule_block_id: str = Field(min_length=1)
    opcode: str = Field(min_length=1)
    core_id: int = Field(ge=0)
    stage: str = Field(min_length=1)
    layout_template: str = Field(min_length=1)
    encoding_bits: int = Field(default=512, gt=0)
    record_index: int = Field(ge=0)
    stream_offset_bytes: int = Field(ge=0)
    stream_size_bytes: int = Field(gt=0)
    word_order: Literal["lsw-first", "msw-first"]
    byte_order: Literal["little-endian", "big-endian"]
    word_hex: list[str] = Field(default_factory=list)
    packed_hex: str = Field(min_length=3, pattern=r"^0x[0-9a-f]+$")
    stream_hex: str = Field(min_length=3, pattern=r"^0x[0-9a-f]+$")
    field_placements: list[PackedDescriptorFieldPlacement] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "PackedDescriptorRecord":
        expected_words = self.encoding_bits // 64
        if expected_words <= 0 or self.encoding_bits % 64 != 0:
            raise ValueError("packed descriptor encoding_bits must be a positive multiple of 64")
        expected_stream_size_bytes = self.encoding_bits // 8
        if self.stream_size_bytes != expected_stream_size_bytes:
            raise ValueError("packed descriptor stream_size_bytes must match encoding_bits / 8")
        if len(self.word_hex) != expected_words:
            raise ValueError("packed descriptor word_hex must match encoding_bits / 64")
        for word in self.word_hex:
            if not isinstance(word, str) or not word.startswith("0x") or len(word) != 18:
                raise ValueError("packed descriptor words must be 64-bit hex strings")
        expected_packed_hex = "0x" + "".join(word[2:] for word in reversed(self.word_hex))
        if self.packed_hex != expected_packed_hex:
            raise ValueError("packed descriptor packed_hex must match concatenated word_hex payload")
        expected_stream_hex = _serialize_stream_hex(
            self.word_hex,
            word_order=self.word_order,
            byte_order=self.byte_order,
        )
        if self.stream_hex != expected_stream_hex:
            raise ValueError("packed descriptor stream_hex must match word_hex ordering policy")
        if len(self.stream_hex) != (self.stream_size_bytes * 2) + 2:
            raise ValueError("packed descriptor stream_hex must match stream_size_bytes")

        occupied_bits: set[int] = set()
        for placement in self.field_placements:
            if placement.word_index != placement.bit_offset // 64:
                raise ValueError("packed descriptor placement word_index must match bit_offset")
            if placement.bit_offset + placement.bit_width > self.encoding_bits:
                raise ValueError("packed descriptor placement exceeds encoding_bits")
            field_bits = range(placement.bit_offset, placement.bit_offset + placement.bit_width)
            if any(bit in occupied_bits for bit in field_bits):
                raise ValueError("packed descriptor field placements must not overlap")
            occupied_bits.update(field_bits)
        return self


class PackedDescriptorBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str = Field(min_length=1)
    encoding_bits: int = Field(default=512, gt=0)
    container_format: Literal["aligned-flat-v1"]
    record_alignment_bytes: int = Field(gt=0)
    stream_total_bytes: int = Field(ge=0)
    stream_hex: str = Field(min_length=2, pattern=r"^0x[0-9a-f]*$")
    descriptors: list[PackedDescriptorRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_descriptor_encoding(self) -> "PackedDescriptorBundle":
        if self.record_alignment_bytes % 8 != 0:
            raise ValueError("packed descriptor bundle record_alignment_bytes must be a multiple of 8")
        expected_record_size_bytes = self.encoding_bits // 8
        if self.encoding_bits % 8 != 0:
            raise ValueError("packed descriptor bundle encoding_bits must be a multiple of 8")
        if self.record_alignment_bytes < expected_record_size_bytes:
            raise ValueError("packed descriptor bundle record_alignment_bytes must be >= encoding_bits / 8")

        sorted_descriptors = sorted(self.descriptors, key=lambda descriptor: descriptor.record_index)
        expected_indices = list(range(len(sorted_descriptors)))
        actual_indices = [descriptor.record_index for descriptor in sorted_descriptors]
        if actual_indices != expected_indices:
            raise ValueError("packed descriptor bundle record_index values must be contiguous from 0")

        max_end = 0
        for descriptor in self.descriptors:
            if descriptor.encoding_bits != self.encoding_bits:
                raise ValueError("packed descriptor bundle encoding_bits must match descriptor payloads")
            if descriptor.stream_offset_bytes % self.record_alignment_bytes != 0:
                raise ValueError("packed descriptor stream_offset_bytes must align to record_alignment_bytes")
            if descriptor.stream_size_bytes != expected_record_size_bytes:
                raise ValueError("packed descriptor bundle stream_size_bytes must match encoding_bits / 8")
            max_end = max(max_end, descriptor.stream_offset_bytes + descriptor.stream_size_bytes)
        if max_end != self.stream_total_bytes:
            raise ValueError("packed descriptor bundle stream_total_bytes must match the last record end")
        expected_stream_hex = _assemble_bundle_stream_hex(sorted_descriptors, self.stream_total_bytes)
        if self.stream_hex != expected_stream_hex:
            raise ValueError("packed descriptor bundle stream_hex must match descriptor record order and offsets")
        return self


def serialize_stream_hex(
    word_hex: list[str],
    *,
    word_order: Literal["lsw-first", "msw-first"],
    byte_order: Literal["little-endian", "big-endian"],
) -> str:
    return _serialize_stream_hex(word_hex, word_order=word_order, byte_order=byte_order)


def assemble_bundle_stream_hex(
    descriptors: list[PackedDescriptorRecord],
    stream_total_bytes: int,
) -> str:
    return _assemble_bundle_stream_hex(descriptors, stream_total_bytes)


def _serialize_stream_hex(
    word_hex: list[str],
    *,
    word_order: Literal["lsw-first", "msw-first"],
    byte_order: Literal["little-endian", "big-endian"],
) -> str:
    ordered_words = word_hex if word_order == "lsw-first" else list(reversed(word_hex))
    stream_chunks = []
    for word in ordered_words:
        chunk = word[2:]
        if byte_order == "little-endian":
            chunk = chunk[::-1]
        stream_chunks.append(chunk)
    return "0x" + "".join(stream_chunks)


def _assemble_bundle_stream_hex(
    descriptors: list[PackedDescriptorRecord],
    stream_total_bytes: int,
) -> str:
    cursor = 0
    chunks: list[str] = []
    for descriptor in descriptors:
        if descriptor.stream_offset_bytes < cursor:
            raise ValueError("packed descriptor bundle stream offsets must be non-overlapping")
        gap_bytes = descriptor.stream_offset_bytes - cursor
        if gap_bytes > 0:
            chunks.append("00" * gap_bytes)
        chunks.append(descriptor.stream_hex[2:])
        cursor = descriptor.stream_offset_bytes + descriptor.stream_size_bytes
    if cursor < stream_total_bytes:
        chunks.append("00" * (stream_total_bytes - cursor))
    return "0x" + "".join(chunks)
