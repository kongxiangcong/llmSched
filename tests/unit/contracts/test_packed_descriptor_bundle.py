import pytest
from pydantic import ValidationError

from llm_sched.contracts.packed_descriptor_bundle import (
    PackedDescriptorBundle,
    PackedDescriptorFieldPlacement,
    PackedDescriptorRecord,
)


def test_packed_descriptor_bundle_accepts_eight_word_payloads() -> None:
    bundle = PackedDescriptorBundle(
        graph_id="graph-packed",
        encoding_bits=512,
        container_format="aligned-flat-v1",
        record_alignment_bytes=64,
        stream_total_bytes=64,
        stream_hex="0x" + "".join(f"{i:016x}"[::-1] for i in range(8)),
        descriptors=[
            PackedDescriptorRecord(
                descriptor_id="desc.0",
                schedule_block_id="sched.block.0",
                opcode="WDQ_GEMM",
                core_id=0,
                stage="compute",
                layout_template="wdq_compute_v1",
                record_index=0,
                stream_offset_bytes=0,
                stream_size_bytes=64,
                word_order="lsw-first",
                byte_order="little-endian",
                word_hex=[f"0x{i:016x}" for i in range(8)],
                packed_hex="0x" + "".join(f"{i:016x}" for i in range(7, -1, -1)),
                stream_hex="0x" + "".join(f"{i:016x}"[::-1] for i in range(8)),
                field_placements=[
                    PackedDescriptorFieldPlacement(
                        field_name="opcode",
                        field_group="ctrl",
                        word_index=0,
                        bit_offset=0,
                        bit_width=16,
                        value_hex="0x0011",
                    ),
                    PackedDescriptorFieldPlacement(
                        field_name="shape_m",
                        field_group="shape",
                        word_index=0,
                        bit_offset=32,
                        bit_width=16,
                        value_hex="0x0030",
                    ),
                ],
            )
        ],
    )

    assert bundle.encoding_bits == 512
    assert bundle.container_format == "aligned-flat-v1"
    assert bundle.record_alignment_bytes == 64
    assert bundle.stream_total_bytes == 64
    assert bundle.stream_hex.startswith("0x")
    assert len(bundle.descriptors[0].word_hex) == 8
    assert bundle.descriptors[0].packed_hex.startswith("0x")
    assert bundle.descriptors[0].stream_hex.startswith("0x")


def test_packed_descriptor_bundle_rejects_overlapping_field_placements() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PackedDescriptorBundle(
            graph_id="graph-packed",
            encoding_bits=512,
            container_format="aligned-flat-v1",
            record_alignment_bytes=64,
            stream_total_bytes=64,
            stream_hex="0x" + "".join(f"{i:016x}"[::-1] for i in range(8)),
            descriptors=[
                PackedDescriptorRecord(
                    descriptor_id="desc.0",
                    schedule_block_id="sched.block.0",
                    opcode="WDQ_GEMM",
                    core_id=0,
                    stage="compute",
                    layout_template="wdq_compute_v1",
                    record_index=0,
                    stream_offset_bytes=0,
                    stream_size_bytes=64,
                    word_order="lsw-first",
                    byte_order="little-endian",
                    word_hex=[f"0x{i:016x}" for i in range(8)],
                    packed_hex="0x" + "".join(f"{i:016x}" for i in range(7, -1, -1)),
                    stream_hex="0x" + "".join(f"{i:016x}"[::-1] for i in range(8)),
                    field_placements=[
                        PackedDescriptorFieldPlacement(
                            field_name="opcode",
                            field_group="ctrl",
                            word_index=0,
                            bit_offset=0,
                            bit_width=16,
                            value_hex="0x0011",
                        ),
                        PackedDescriptorFieldPlacement(
                            field_name="control",
                            field_group="ctrl",
                            word_index=0,
                            bit_offset=8,
                            bit_width=16,
                            value_hex="0x0003",
                        ),
                    ],
                )
            ],
        )

    assert "field placements must not overlap" in str(exc_info.value)


def test_packed_descriptor_bundle_rejects_stream_hex_that_mismatches_byte_order() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PackedDescriptorBundle(
            graph_id="graph-packed",
            encoding_bits=512,
            container_format="aligned-flat-v1",
            record_alignment_bytes=64,
            stream_total_bytes=64,
            stream_hex="0x" + "".join(f"{i:016x}" for i in range(8)),
            descriptors=[
                PackedDescriptorRecord(
                    descriptor_id="desc.0",
                    schedule_block_id="sched.block.0",
                    opcode="WDQ_GEMM",
                    core_id=0,
                    stage="compute",
                    layout_template="wdq_compute_v1",
                    record_index=0,
                    stream_offset_bytes=0,
                    stream_size_bytes=64,
                    word_order="lsw-first",
                    byte_order="little-endian",
                    word_hex=[f"0x{i:016x}" for i in range(8)],
                    packed_hex="0x" + "".join(f"{i:016x}" for i in range(7, -1, -1)),
                    stream_hex="0x" + "".join(f"{i:016x}" for i in range(8)),
                    field_placements=[
                        PackedDescriptorFieldPlacement(
                            field_name="opcode",
                            field_group="ctrl",
                            word_index=0,
                            bit_offset=0,
                            bit_width=16,
                            value_hex="0x0011",
                        )
                    ],
                )
            ],
        )

    assert "stream_hex must match word_hex" in str(exc_info.value)


def test_packed_descriptor_bundle_rejects_misaligned_record_offset() -> None:
    with pytest.raises(ValidationError) as exc_info:
        PackedDescriptorBundle(
            graph_id="graph-packed",
            encoding_bits=512,
            container_format="aligned-flat-v1",
            record_alignment_bytes=64,
            stream_total_bytes=128,
            stream_hex="0x" + ("0" * 256),
            descriptors=[
                PackedDescriptorRecord(
                    descriptor_id="desc.0",
                    schedule_block_id="sched.block.0",
                    opcode="WDQ_GEMM",
                    core_id=0,
                    stage="compute",
                    layout_template="wdq_compute_v1",
                    record_index=0,
                    stream_offset_bytes=32,
                    stream_size_bytes=64,
                    word_order="lsw-first",
                    byte_order="little-endian",
                    word_hex=[f"0x{i:016x}" for i in range(8)],
                    packed_hex="0x" + "".join(f"{i:016x}" for i in range(7, -1, -1)),
                    stream_hex="0x" + "".join(f"{i:016x}"[::-1] for i in range(8)),
                    field_placements=[
                        PackedDescriptorFieldPlacement(
                            field_name="opcode",
                            field_group="ctrl",
                            word_index=0,
                            bit_offset=0,
                            bit_width=16,
                            value_hex="0x0011",
                        )
                    ],
                )
            ],
        )

    assert "stream_offset_bytes must align" in str(exc_info.value)
