import pytest
from pydantic import ValidationError

from llm_sched.ir.validators import (
    validate_analysis_ir,
    validate_descriptor_ir,
    validate_graph_ir,
    validate_nig_ir,
    validate_schedule_ir,
)


def test_graph_ir_validator_accepts_minimal_document() -> None:
    graph = validate_graph_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "graph-001",
            "nodes": [
                {
                    "node_id": "graph.node.0",
                    "op_kind": "Input",
                    "inputs": [],
                    "outputs": ["tensor.input"],
                    "shape": [1, 128, 1152],
                    "dtype": "bf16",
                    "attrs": {},
                }
            ],
        }
    )

    assert graph.graph_id == "graph-001"
    assert graph.nodes[0].node_id == "graph.node.0"


def test_nig_validator_accepts_minimal_document() -> None:
    nig = validate_nig_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "nig-001",
            "nodes": [
                {
                    "node_id": "nig.node.0",
                    "macro_op": "RMSNORM_GEMM",
                    "inputs": ["tensor.input"],
                    "outputs": ["tensor.q"],
                    "layout": "HSD",
                    "memory_class": "activation",
                    "legal_opcodes": ["RMSNORM_GEMM"],
                    "quant": {
                        "weight_dtype": "int4",
                        "activation_dtype": "bf16",
                        "group_size": 128,
                    },
                }
            ],
        }
    )

    assert nig.nodes[0].macro_op == "RMSNORM_GEMM"


def test_schedule_ir_validator_rejects_cross_core_blocks_in_single_core_mode() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_schedule_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "sched-001",
                "core_mode": "single-core",
                "blocks": [
                    {
                        "block_id": "sched.block.0",
                        "core_id": 0,
                        "resource_set": ["DMA", "VPU"],
                        "buffer_binding": {"input": "ping"},
                        "barrier_in": [],
                        "barrier_out": [],
                        "order_key": 0,
                    },
                    {
                        "block_id": "sched.block.1",
                        "core_id": 1,
                        "resource_set": ["MXU"],
                        "buffer_binding": {"weight": "weight"},
                        "barrier_in": [],
                        "barrier_out": [],
                        "order_key": 1,
                    },
                ],
            }
        )

    assert "single-core schedule blocks must all target the same core" in str(exc_info.value)


def test_descriptor_ir_validator_accepts_minimal_document() -> None:
    descriptor = validate_descriptor_ir(
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
                    "ctrl_fields": {"fusion": True, "stage": "compute"},
                        "packing_profile": {
                            "stage_family": "compute",
                            "opcode_family": "tensor_compute",
                            "layout_template": "tensor_compute_v1",
                            "field_groups": ["ctrl", "shape", "addr"],
                            "required_ctrl_fields": ["stage"],
                            "required_shape_axes": ["m", "n", "k"],
                            "required_addr_roles": ["act", "weight", "dst"],
                            "required_dma_fields": [],
                            "field_widths": {
                                "opcode": 16,
                                "control": 16,
                                "shape": 16,
                                "act_addr": 64,
                                "weight_addr": 64,
                                "dst_addr_low": 32,
                            },
                        },
                    "shape_pack": {"m": 1, "n": 128, "k": 128},
                    "addr_fields": {"act": "VMEM:ping", "weight": "VMEM:weight", "dst": "VMEM:pong"},
                    "address_fields": [
                        {
                            "role": "act",
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
                            "address_space": "VMEM",
                                "region_name": "weight",
                                "offset_bytes": 0,
                                "symbol": "VMEM:weight",
                                "descriptor_field": "WEIGHT_ADDR",
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
                                "encoded_width_bits": 32,
                                "uses_addr_ext": False,
                            },
                    ],
                    "dma_fields": {"length": 8192, "channel": 0, "priority": 1},
                }
            ],
        }
    )

    assert descriptor.descriptors[0].opcode == "RMSNORM_GEMM"


def test_analysis_ir_validator_accepts_minimal_document() -> None:
    analysis = validate_analysis_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "analysis-001",
            "records": [
                {
                    "record_id": "analysis.record.0",
                    "subject_id": "desc.0",
                    "metrics": {"cycles": 259.0, "ddr_bytes": 8192.0},
                    "tags": ["prefill", "layer0"],
                }
            ],
        }
    )

    assert analysis.records[0].metrics["cycles"] == 259.0
