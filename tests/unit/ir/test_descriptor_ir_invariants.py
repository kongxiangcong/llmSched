import pytest
from pydantic import ValidationError

from llm_sched.ir.validators import validate_descriptor_ir


def test_descriptor_ir_rejects_duplicate_descriptor_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_descriptor_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "desc-001",
                "descriptors": [
                    {
                        "descriptor_id": "desc.0",
                        "schedule_block_id": "sched.block.0",
                        "opcode": "RMSNORM_GEMM",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "compute"},
                        "packing_profile": {
                            "stage_family": "compute",
                            "opcode_family": "tensor_compute",
                            "layout_template": "tensor_compute_v1",
                            "field_groups": ["ctrl", "shape", "addr"],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["input", "output"],
                            "required_dma_fields": [],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "shape": 16,
                                "act_addr": 64,
                                "dst_addr_low": 32,
                            },
                        },
                        "shape_pack": {"m": 1, "n": 128, "k": 128},
                        "addr_fields": {"input": "VMEM:ping", "output": "VMEM:pong"},
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "ACT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                            {
                                "role": "output",
                                "address_space": "VMEM",
                                "region_name": "pong",
                                "offset_bytes": 0,
                                "symbol": "VMEM:pong",
                                "descriptor_field": "DST_ADDR",
                                "encoded_width_bits": 32,
                                "uses_addr_ext": False,
                            },
                        ],
                        "dma_fields": {},
                    },
                    {
                        "descriptor_id": "desc.0",
                        "schedule_block_id": "sched.block.1",
                        "opcode": "WDQ_GEMM",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "compute"},
                        "packing_profile": {
                            "stage_family": "compute",
                            "opcode_family": "tensor_compute",
                            "layout_template": "tensor_compute_v1",
                            "field_groups": ["ctrl", "shape", "addr"],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["input", "output"],
                            "required_dma_fields": [],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "shape": 16,
                                "act_addr": 64,
                                "dst_addr_low": 32,
                            },
                        },
                        "shape_pack": {"m": 1, "n": 128, "k": 128},
                        "addr_fields": {"input": "VMEM:ping", "output": "VMEM:pong"},
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "ACT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                            {
                                "role": "output",
                                "address_space": "VMEM",
                                "region_name": "pong",
                                "offset_bytes": 0,
                                "symbol": "VMEM:pong",
                                "descriptor_field": "DST_ADDR",
                                "encoded_width_bits": 32,
                                "uses_addr_ext": False,
                            },
                        ],
                        "dma_fields": {},
                    },
                ],
            }
        )

    assert "descriptor ids must be unique" in str(exc_info.value)


def test_descriptor_ir_accepts_schedule_binding_and_transfer_fields() -> None:
    descriptor = validate_descriptor_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "desc-002",
            "descriptors": [
                {
                    "descriptor_id": "desc.transfer.0",
                    "schedule_block_id": "sched.transfer.0",
                    "opcode": "CORE_LINK_COPY",
                    "core_id": 0,
                    "encoding_bits": 512,
                    "ctrl_fields": {"stage": "transfer"},
                    "packing_profile": {
                        "stage_family": "transfer",
                        "opcode_family": "core_link_transfer",
                        "layout_template": "core_link_transfer_v1",
                        "field_groups": ["ctrl", "shape", "addr", "dma", "transfer"],
                        "required_ctrl_fields": ["stage"],
                        "required_shape_axes": ["m", "n", "k"],
                        "required_addr_roles": ["src", "dst"],
                        "required_dma_fields": ["length", "channel", "priority"],
                        "field_widths": {
                            "opcode": 16,
                            "src_addr": 64,
                            "dst_addr": 64,
                            "dma_length": 32,
                        },
                    },
                    "shape_pack": {"m": 1, "n": 128, "k": 128},
                    "addr_fields": {"src": "VMEM:ping", "dst": "VMEM:pong"},
                    "address_fields": [
                        {
                            "role": "src",
                            "address_space": "VMEM",
                            "region_name": "ping",
                            "offset_bytes": 0,
                            "symbol": "VMEM:ping",
                            "descriptor_field": "SRC_ADDR",
                            "encoded_width_bits": 64,
                            "uses_addr_ext": False,
                        },
                        {
                            "role": "dst",
                            "address_space": "VMEM",
                            "region_name": "pong",
                            "offset_bytes": 0,
                            "symbol": "VMEM:pong",
                            "descriptor_field": "DST_ADDR",
                            "encoded_width_bits": 64,
                            "uses_addr_ext": False,
                        },
                    ],
                    "dma_fields": {"length": 8192, "channel": 0, "priority": 1},
                    "transfer_fields": {
                        "kind": "core_link",
                        "src_core_id": 0,
                        "dst_core_id": 1,
                        "transfer_bytes": 8192,
                    },
                    "audit_ref": {"schedule_block_ids": ["sched.transfer.0"]},
                }
            ],
        }
    )

    record = descriptor.descriptors[0]
    assert record.schedule_block_id == "sched.transfer.0"
    assert record.encoding_bits == 512
    assert record.packing_profile.stage_family == "transfer"
    assert record.packing_profile.layout_template == "core_link_transfer_v1"
    assert record.packing_profile.field_widths["src_addr"] == 64
    assert record.address_fields[0].role == "src"
    assert record.address_fields[0].descriptor_field == "SRC_ADDR"
    assert record.address_fields[0].encoded_width_bits == 64
    assert record.transfer_fields is not None
    assert record.transfer_fields.kind == "core_link"
    assert record.transfer_fields.dst_core_id == 1


def test_descriptor_ir_rejects_duplicate_schedule_block_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_descriptor_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "desc-003",
                "descriptors": [
                    {
                        "descriptor_id": "desc.0",
                        "schedule_block_id": "sched.block.0",
                        "opcode": "WDQ_GEMM",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "compute"},
                        "packing_profile": {
                            "stage_family": "compute",
                            "opcode_family": "tensor_compute",
                            "layout_template": "tensor_compute_v1",
                            "field_groups": ["ctrl", "shape", "addr"],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["input", "output"],
                            "required_dma_fields": [],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "shape": 16,
                                "act_addr": 64,
                                "dst_addr_low": 32,
                            },
                        },
                        "shape_pack": {"m": 1, "n": 128, "k": 128},
                        "addr_fields": {"input": "VMEM:ping", "output": "VMEM:pong"},
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "ACT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                            {
                                "role": "output",
                                "address_space": "VMEM",
                                "region_name": "pong",
                                "offset_bytes": 0,
                                "symbol": "VMEM:pong",
                                "descriptor_field": "DST_ADDR",
                                "encoded_width_bits": 32,
                                "uses_addr_ext": False,
                            },
                        ],
                        "dma_fields": {},
                    },
                    {
                        "descriptor_id": "desc.1",
                        "schedule_block_id": "sched.block.0",
                        "opcode": "DMA_LOAD",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "dma_in"},
                        "packing_profile": {
                            "stage_family": "dma",
                            "opcode_family": "dma_load",
                            "layout_template": "dma_load_v1",
                            "field_groups": ["ctrl", "shape", "addr", "dma"],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["input"],
                            "required_dma_fields": ["length", "channel", "priority"],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "shape": 16,
                                "act_addr": 64,
                                "dma_length": 32,
                                "dma_channel": 8,
                                "dma_priority": 4,
                            },
                        },
                        "shape_pack": {"m": 1, "n": 128, "k": 128},
                        "addr_fields": {"input": "VMEM:ping"},
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "ACT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            }
                        ],
                        "dma_fields": {"length": 8192, "channel": 0, "priority": 1},
                    },
                ],
            }
        )

    assert "schedule block ids must be unique across descriptors" in str(exc_info.value)


def test_descriptor_ir_rejects_compute_descriptor_without_shape_pack() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_descriptor_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "desc-004",
                "descriptors": [
                    {
                        "descriptor_id": "desc.compute.0",
                        "schedule_block_id": "sched.compute.0",
                        "opcode": "WDQ_GEMM",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "compute"},
                        "packing_profile": {
                            "stage_family": "compute",
                            "opcode_family": "tensor_compute",
                            "layout_template": "tensor_compute_v1",
                            "field_groups": ["ctrl", "shape", "addr"],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["input", "output"],
                            "required_dma_fields": [],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "shape": 16,
                                "act_addr": 64,
                                "dst_addr_low": 32,
                            },
                        },
                        "shape_pack": {},
                        "addr_fields": {"input": "VMEM:ping", "output": "VMEM:pong"},
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "ACT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                            {
                                "role": "output",
                                "address_space": "VMEM",
                                "region_name": "pong",
                                "offset_bytes": 0,
                                "symbol": "VMEM:pong",
                                "descriptor_field": "DST_ADDR",
                                "encoded_width_bits": 32,
                                "uses_addr_ext": False,
                            },
                        ],
                        "dma_fields": {},
                    }
                ],
            }
        )

    assert "compute descriptors must include non-empty shape_pack" in str(exc_info.value)


def test_descriptor_ir_rejects_dma_descriptor_without_positive_length() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_descriptor_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "desc-005",
                "descriptors": [
                    {
                        "descriptor_id": "desc.dma.0",
                        "schedule_block_id": "sched.dma.0",
                        "opcode": "DMA_LOAD",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "dma_in"},
                        "packing_profile": {
                            "stage_family": "dma",
                            "opcode_family": "dma_load",
                            "layout_template": "dma_load_v1",
                            "field_groups": ["ctrl", "shape", "addr", "dma"],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["input"],
                            "required_dma_fields": ["length", "channel", "priority"],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "shape": 16,
                                "act_addr": 64,
                                "dma_length": 32,
                                "dma_channel": 8,
                                "dma_priority": 4,
                            },
                        },
                        "shape_pack": {"m": 1, "n": 128, "k": 128},
                        "addr_fields": {"input": "VMEM:ping"},
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "ACT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            }
                        ],
                        "dma_fields": {"length": 0, "channel": 0, "priority": 1},
                    }
                ],
            }
        )

    assert "DMA descriptors must include positive dma_fields.length" in str(exc_info.value)


def test_descriptor_ir_rejects_opcode_family_layout_template_mismatch() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_descriptor_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "desc-005b",
                "descriptors": [
                    {
                        "descriptor_id": "desc.transfer.0",
                        "schedule_block_id": "sched.transfer.0",
                        "opcode": "CORE_LINK_COPY",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "transfer"},
                        "packing_profile": {
                            "stage_family": "transfer",
                            "opcode_family": "core_link_transfer",
                            "layout_template": "dma_transfer_v1",
                            "field_groups": ["ctrl", "shape", "addr", "dma", "transfer"],
                            "field_layout": [
                                "opcode",
                                "control",
                                "order_key",
                                "shape_m",
                                "shape_n",
                                "shape_k",
                                "src_addr",
                                "dst_addr",
                                "dma_length",
                                "dma_channel",
                                "dma_priority",
                                "transfer_kind",
                                "transfer_src_core_id",
                                "transfer_dst_core_id",
                                "transfer_bytes",
                            ],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["src", "dst"],
                            "required_dma_fields": ["length", "channel", "priority"],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "order_key": 16,
                                "shape_m": 16,
                                "shape_n": 16,
                                "shape_k": 16,
                                "src_addr": 64,
                                "dst_addr": 64,
                                "dma_length": 32,
                                "dma_channel": 8,
                                "dma_priority": 8,
                                "transfer_kind": 8,
                                "transfer_src_core_id": 8,
                                "transfer_dst_core_id": 8,
                                "transfer_bytes": 32,
                            },
                        },
                        "shape_pack": {"m": 1, "n": 128, "k": 128},
                        "addr_fields": {"src": "VMEM:ping", "dst": "VMEM:pong"},
                        "address_fields": [
                            {
                                "role": "src",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "SRC_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                            {
                                "role": "dst",
                                "address_space": "VMEM",
                                "region_name": "pong",
                                "offset_bytes": 0,
                                "symbol": "VMEM:pong",
                                "descriptor_field": "DST_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                        ],
                        "dma_fields": {"length": 8192, "channel": 0, "priority": 1},
                        "transfer_fields": {
                            "kind": "core_link",
                            "src_core_id": 0,
                            "dst_core_id": 1,
                            "transfer_bytes": 8192,
                        },
                    }
                ],
            }
        )

    assert "layout_template must match opcode_family" in str(exc_info.value)


def test_descriptor_ir_rejects_missing_packing_profile() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_descriptor_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "desc-006",
                "descriptors": [
                    {
                        "descriptor_id": "desc.compute.0",
                        "schedule_block_id": "sched.compute.0",
                        "opcode": "WDQ_GEMM",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "compute"},
                        "shape_pack": {"m": 1, "n": 128, "k": 128},
                        "addr_fields": {"input": "VMEM:ping", "output": "VMEM:pong"},
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                            },
                            {
                                "role": "output",
                                "address_space": "VMEM",
                                "region_name": "pong",
                                "offset_bytes": 0,
                                "symbol": "VMEM:pong",
                            },
                        ],
                        "dma_fields": {},
                    }
                ],
            }
        )

    assert "packing_profile" in str(exc_info.value)


def test_descriptor_ir_rejects_wdq_layout_without_group_size_slot() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_descriptor_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "desc-007",
                "descriptors": [
                    {
                        "descriptor_id": "desc.compute.0",
                        "schedule_block_id": "sched.compute.0",
                        "opcode": "WDQ_GEMM",
                        "core_id": 0,
                        "encoding_bits": 512,
                        "ctrl_fields": {"stage": "compute", "order_key": 0, "scenario_mode": "prefill", "group_size": 128},
                        "packing_profile": {
                            "stage_family": "compute",
                            "opcode_family": "wdq_gemm_compute",
                            "layout_template": "wdq_compute_v1",
                            "field_groups": ["ctrl", "shape", "addr"],
                            "field_layout": [
                                "opcode",
                                "control",
                                "order_key",
                                "shape_m",
                                "shape_n",
                                "shape_k",
                                "act_addr",
                                "weight_addr",
                                "dst_addr_low",
                            ],
                            "required_ctrl_fields": ["stage", "order_key", "scenario_mode", "group_size"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["input", "weight", "output"],
                            "required_dma_fields": [],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "order_key": 16,
                                "group_size": 16,
                                "shape_m": 16,
                                "shape_n": 16,
                                "shape_k": 16,
                                "act_addr": 64,
                                "weight_addr": 64,
                                "dst_addr_low": 32,
                            },
                        },
                        "shape_pack": {"m": 48, "n": 128, "k": 128},
                        "addr_fields": {
                            "input": "VMEM:ping",
                            "weight": "DDR@0",
                            "output": "VMEM:pong",
                        },
                        "address_fields": [
                            {
                                "role": "input",
                                "address_space": "VMEM",
                                "region_name": "ping",
                                "offset_bytes": 0,
                                "symbol": "VMEM:ping",
                                "descriptor_field": "ACT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                            {
                                "role": "weight",
                                "address_space": "DDR",
                                "region_name": None,
                                "offset_bytes": 0,
                                "symbol": "DDR@0",
                                "descriptor_field": "WEIGHT_ADDR",
                                "encoded_width_bits": 64,
                                "uses_addr_ext": False,
                            },
                            {
                                "role": "output",
                                "address_space": "VMEM",
                                "region_name": "pong",
                                "offset_bytes": 0,
                                "symbol": "VMEM:pong",
                                "descriptor_field": "DST_ADDR",
                                "encoded_width_bits": 32,
                                "uses_addr_ext": False,
                            },
                        ],
                        "dma_fields": {},
                    }
                ],
            }
        )

    assert "wdq_compute_v1" in str(exc_info.value)
