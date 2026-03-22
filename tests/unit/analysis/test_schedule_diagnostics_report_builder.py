from llm_sched.ir.descriptor_ir import AddressField, DescriptorIR, DescriptorPackingProfile, DescriptorRecord
from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR


def test_build_schedule_diagnostics_report_derives_timeline_idle_stalls_critical_path_and_contention() -> None:
    from llm_sched.analysis.schedule_diagnostics_report_builder import (
        build_schedule_diagnostics_report,
    )

    report = build_schedule_diagnostics_report(
        run_id="run-diagnosis-001",
        scenario_name="prefill_seq128",
        schedule_ir=_schedule_ir(),
        descriptor_ir=_descriptor_ir(),
    )

    assert report.graph_id == "graph::gemma3-prefill"
    assert [(block.block_id, block.start_slot, block.end_slot) for block in report.blocks] == [
        ("sched.block.q_proj.dma_in", 0, 3),
        ("sched.block.k_proj.dma_in", 0, 2),
        ("sched.block.k_proj.compute", 2, 5),
        ("sched.block.q_proj.compute", 4, 8),
    ]
    assert [(lane.core_id, lane.occupied_slots, lane.makespan_slots) for lane in report.core_lanes] == [
        (0, 7, 8),
        (1, 5, 8),
    ]
    assert [(span.core_id, span.start_slot, span.end_slot, span.reason) for span in report.idle_spans] == [
        (0, 3, 4, "dependency_wait"),
    ]
    assert [(event.block_id, event.start_slot, event.end_slot, event.reason) for event in report.stall_events] == [
        ("sched.block.q_proj.compute", 3, 4, "dependency_wait"),
    ]
    assert report.critical_path_blocks == [
        "sched.block.k_proj.dma_in",
        "sched.block.k_proj.compute",
        "sched.block.q_proj.compute",
    ]
    assert report.resource_contention_summary.makespan_slots == 8
    assert report.resource_contention_summary.contention_slots == 2
    assert report.resource_contention_summary.contended_resources == {"DMA": 2}
    assert report.resource_contention_summary.top_contention_block_ids == [
        "sched.block.k_proj.dma_in",
        "sched.block.q_proj.dma_in",
    ]


def _schedule_ir() -> ScheduleIR:
    return ScheduleIR.model_validate(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "graph::gemma3-prefill",
            "core_mode": "dual-core",
            "blocks": [
                {
                    "block_id": "sched.block.q_proj.dma_in",
                    "core_id": 0,
                    "peer_core_id": None,
                    "node_id": "nig.node.q_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "stage": "dma_in",
                    "tiling_candidate_id": "cand.q_proj.0",
                    "resource_set": ["DMA"],
                    "buffer_binding": {"src": "DDR", "dst": "ping"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "depends_on": [],
                    "issue_slot": 0,
                    "duration_slots": 3,
                    "transfer_kind": None,
                    "transfer_bytes": 0,
                    "sync_cost_cycles": 0,
                    "order_key": 0,
                    "audit_ref": {},
                },
                {
                    "block_id": "sched.block.k_proj.dma_in",
                    "core_id": 1,
                    "peer_core_id": None,
                    "node_id": "nig.node.k_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "stage": "dma_in",
                    "tiling_candidate_id": "cand.k_proj.0",
                    "resource_set": ["DMA"],
                    "buffer_binding": {"src": "DDR", "dst": "pong"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "depends_on": [],
                    "issue_slot": 0,
                    "duration_slots": 2,
                    "transfer_kind": None,
                    "transfer_bytes": 0,
                    "sync_cost_cycles": 0,
                    "order_key": 1,
                    "audit_ref": {},
                },
                {
                    "block_id": "sched.block.k_proj.compute",
                    "core_id": 1,
                    "peer_core_id": None,
                    "node_id": "nig.node.k_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "stage": "compute",
                    "tiling_candidate_id": "cand.k_proj.0",
                    "resource_set": ["MXU"],
                    "buffer_binding": {"src": "pong", "dst": "pong"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "depends_on": ["sched.block.k_proj.dma_in"],
                    "issue_slot": 2,
                    "duration_slots": 3,
                    "transfer_kind": None,
                    "transfer_bytes": 0,
                    "sync_cost_cycles": 0,
                    "order_key": 2,
                    "audit_ref": {},
                },
                {
                    "block_id": "sched.block.q_proj.compute",
                    "core_id": 0,
                    "peer_core_id": None,
                    "node_id": "nig.node.q_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "stage": "compute",
                    "tiling_candidate_id": "cand.q_proj.0",
                    "resource_set": ["MXU"],
                    "buffer_binding": {"src": "ping", "dst": "ping"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "depends_on": ["sched.block.q_proj.dma_in", "sched.block.k_proj.compute"],
                    "issue_slot": 4,
                    "duration_slots": 4,
                    "transfer_kind": None,
                    "transfer_bytes": 0,
                    "sync_cost_cycles": 0,
                    "order_key": 3,
                    "audit_ref": {},
                },
            ],
        }
    )


def _descriptor_ir() -> DescriptorIR:
    packing_profile = DescriptorPackingProfile(
        stage_family="dma",
        opcode_family="dma_load",
        layout_template="dma_load_v1",
        field_groups=["ctrl", "addr", "dma"],
        required_ctrl_fields=["stage", "macro_op"],
        required_addr_roles=["src", "dst"],
        required_dma_fields=["length", "channel", "priority"],
        field_widths={
            "opcode": 16,
            "control": 16,
            "order_key": 16,
            "src_addr": 64,
            "dst_addr": 64,
            "dma_length": 32,
            "dma_channel": 8,
            "dma_priority": 8,
        },
    )
    compute_profile = DescriptorPackingProfile(
        stage_family="compute",
        opcode_family="tensor_compute",
        layout_template="wdq_compute_v1",
        field_groups=["ctrl", "shape"],
        required_ctrl_fields=["stage", "macro_op"],
        required_shape_axes=["m", "n", "k"],
        field_widths={
            "opcode": 16,
            "control": 16,
            "order_key": 16,
            "group_size": 16,
            "shape_m": 16,
            "shape_n": 16,
            "shape_k": 16,
        },
    )
    return DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="graph::gemma3-prefill",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.q_proj.dma_in",
                schedule_block_id="sched.block.q_proj.dma_in",
                opcode="DMA_LOAD",
                core_id=0,
                ctrl_fields={"stage": "dma_in", "macro_op": "WDQ_GEMM", "duration_slots": 3},
                packing_profile=packing_profile,
                addr_fields={"src": "DDR:weights", "dst": "VMEM:ping"},
                address_fields=[
                    AddressField(
                        role="src",
                        address_space="DDR",
                        symbol="DDR:weights",
                        descriptor_field="SRC_ADDR",
                        encoded_width_bits=64,
                    ),
                    AddressField(
                        role="dst",
                        address_space="VMEM",
                        region_name="ping",
                        symbol="VMEM:ping",
                        descriptor_field="DST_ADDR",
                        encoded_width_bits=64,
                    ),
                ],
                dma_fields={"length": 4096, "channel": 0, "priority": 1},
            ),
            DescriptorRecord(
                descriptor_id="desc.k_proj.dma_in",
                schedule_block_id="sched.block.k_proj.dma_in",
                opcode="DMA_LOAD",
                core_id=1,
                ctrl_fields={"stage": "dma_in", "macro_op": "WDQ_GEMM", "duration_slots": 2},
                packing_profile=packing_profile,
                addr_fields={"src": "DDR:weights", "dst": "VMEM:pong"},
                address_fields=[
                    AddressField(
                        role="src",
                        address_space="DDR",
                        symbol="DDR:weights",
                        descriptor_field="SRC_ADDR",
                        encoded_width_bits=64,
                    ),
                    AddressField(
                        role="dst",
                        address_space="VMEM",
                        region_name="pong",
                        symbol="VMEM:pong",
                        descriptor_field="DST_ADDR",
                        encoded_width_bits=64,
                    ),
                ],
                dma_fields={"length": 4096, "channel": 0, "priority": 1},
            ),
            DescriptorRecord(
                descriptor_id="desc.k_proj.compute",
                schedule_block_id="sched.block.k_proj.compute",
                opcode="WDQ_GEMM",
                core_id=1,
                ctrl_fields={"stage": "compute", "macro_op": "WDQ_GEMM", "duration_slots": 3},
                packing_profile=compute_profile,
                shape_pack={"m": 1, "n": 128, "k": 128},
            ),
            DescriptorRecord(
                descriptor_id="desc.q_proj.compute",
                schedule_block_id="sched.block.q_proj.compute",
                opcode="WDQ_GEMM",
                core_id=0,
                ctrl_fields={"stage": "compute", "macro_op": "WDQ_GEMM", "duration_slots": 4},
                packing_profile=compute_profile,
                shape_pack={"m": 1, "n": 128, "k": 128},
            ),
        ],
    )
