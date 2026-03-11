from pathlib import Path

from llm_sched.ir.analysis_ir import AnalysisIR
from llm_sched.ir.descriptor_ir import DescriptorIR
from llm_sched.ir.graph_ir import GraphIR
from llm_sched.ir.io import dump_ir_document, load_ir_document
from llm_sched.ir.nig import NIGIR
from llm_sched.ir.schedule_ir import ScheduleIR
from llm_sched.ir.validators import (
    validate_analysis_ir,
    validate_descriptor_ir,
    validate_graph_ir,
    validate_nig_ir,
    validate_schedule_ir,
)


def test_all_ir_layers_round_trip_through_json(tmp_path: Path) -> None:
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
                    "source_ref": ["onnx::Input_0"],
                    "audit_ref": {"graph_node_ids": ["graph.node.0"]},
                }
            ],
        }
    )
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
                    "shape": [1, 128, 1152],
                    "layout": "HSD",
                    "memory_class": "activation",
                    "legal_opcodes": ["RMSNORM_GEMM"],
                    "quant": {
                        "weight_dtype": "int4",
                        "activation_dtype": "bf16",
                        "group_size": 128,
                    },
                    "attrs": {"weight_dtype": "int4", "group_size": 128},
                    "source_ref": ["graph.node.0"],
                    "audit_ref": {"graph_node_ids": ["graph.node.0"]},
                }
            ],
        }
    )
    schedule = validate_schedule_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "sched-001",
            "core_mode": "dual-core",
            "blocks": [
                {
                    "block_id": "sched.block.0",
                    "core_id": 0,
                    "node_id": "nig.node.0",
                    "macro_op": "RMSNORM_GEMM",
                    "stage": "compute",
                    "tiling_candidate_id": "nig.node.0.m48.n128.k128",
                    "resource_set": ["DMA"],
                    "buffer_binding": {"input": "ping"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "depends_on": [],
                    "issue_slot": 0,
                    "duration_slots": 1,
                    "order_key": 0,
                    "audit_ref": {"nig_node_ids": ["nig.node.0"]},
                },
                {
                    "block_id": "sched.transfer.0",
                    "core_id": 0,
                    "peer_core_id": 1,
                    "node_id": "nig.node.0",
                    "macro_op": "RMSNORM_GEMM",
                    "stage": "transfer",
                    "tiling_candidate_id": "nig.node.0.m48.n128.k128",
                    "resource_set": ["Core Link"],
                    "buffer_binding": {"output": "pong"},
                    "barrier_in": ["sync.transfer.0.in"],
                    "barrier_out": ["sync.transfer.0.out"],
                    "depends_on": ["sched.block.0"],
                    "issue_slot": 1,
                    "duration_slots": 1,
                    "transfer_kind": "core_link",
                    "transfer_bytes": 4096,
                    "sync_cost_cycles": 18,
                    "order_key": 1,
                    "audit_ref": {"nig_node_ids": ["nig.node.0"]},
                }
            ],
        }
    )
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
                    "transfer_fields": None,
                    "source_ref": ["onnx::MatMul_0"],
                    "audit_ref": {"schedule_block_ids": ["sched.block.0"]},
                }
            ],
        }
    )
    analysis = validate_analysis_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "analysis-001",
            "records": [
                {
                    "record_id": "analysis.record.0",
                    "subject_id": "desc.0",
                    "metrics": {"cycles": 259.0},
                    "tags": ["prefill"],
                    "audit_ref": {"descriptor_ids": ["desc.0"]},
                }
            ],
        }
    )

    cases = [
        (graph, GraphIR, tmp_path / "graph_ir.json"),
        (nig, NIGIR, tmp_path / "nig_ir.json"),
        (schedule, ScheduleIR, tmp_path / "schedule_ir.json"),
        (descriptor, DescriptorIR, tmp_path / "descriptor_ir.json"),
        (analysis, AnalysisIR, tmp_path / "analysis_ir.json"),
    ]

    for document, model_type, path in cases:
        dump_ir_document(document, path)
        restored = load_ir_document(path, model_type)
        assert restored == document
