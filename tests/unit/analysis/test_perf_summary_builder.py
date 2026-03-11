from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
from llm_sched.ir.descriptor_ir import AddressField, DescriptorPackingProfile, TransferFields


def test_build_perf_summary_report_aggregates_totals_and_bottlenecks() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorRecord
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

    descriptor_ir = DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="spec13-summary",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.0",
                schedule_block_id="sched.block.0",
                opcode="WDQ_GEMM",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"macro_op": "WDQ_GEMM", "stage": "compute"},
                packing_profile=DescriptorPackingProfile(
                    stage_family="compute",
                    opcode_family="tensor_compute",
                    layout_template="wdq_compute_v1",
                    field_groups=["ctrl", "shape"],
                    required_ctrl_fields=["stage", "macro_op"],
                    required_shape_axes=["m", "n", "k"],
                    required_addr_roles=[],
                    required_dma_fields=[],
                    field_widths={"opcode": 16, "control": 16, "shape": 16},
                ),
                shape_pack={"m": 48, "n": 128, "k": 128},
                addr_fields={},
                address_fields=[],
                dma_fields={},
                audit_ref=AuditRef(schedule_block_ids=["sched.block.0"]),
            ),
            DescriptorRecord(
                descriptor_id="desc.1",
                schedule_block_id="sched.transfer.0",
                opcode="CORE_LINK_COPY",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"macro_op": "WDQ_GEMM", "stage": "transfer"},
                packing_profile=DescriptorPackingProfile(
                    stage_family="transfer",
                    opcode_family="core_link_transfer",
                    layout_template="core_link_transfer_v1",
                    field_groups=["ctrl", "shape", "addr", "dma", "transfer"],
                    required_ctrl_fields=["stage", "macro_op"],
                    required_shape_axes=["m", "n", "k"],
                    required_addr_roles=["src", "dst"],
                    required_dma_fields=["length", "channel", "priority"],
                    field_widths={
                        "opcode": 16,
                        "control": 16,
                        "shape": 16,
                        "src_addr": 64,
                        "dst_addr": 64,
                        "dma_length": 32,
                        "dma_channel": 8,
                        "dma_priority": 4,
                    },
                ),
                shape_pack={"m": 48, "n": 128, "k": 128},
                addr_fields={"src": "VMEM:ping", "dst": "VMEM:pong"},
                address_fields=[
                    AddressField(
                        role="src",
                        address_space="VMEM",
                        region_name="ping",
                        offset_bytes=0,
                        symbol="VMEM:ping",
                        descriptor_field="SRC_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                    AddressField(
                        role="dst",
                        address_space="VMEM",
                        region_name="pong",
                        offset_bytes=0,
                        symbol="VMEM:pong",
                        descriptor_field="DST_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                ],
                dma_fields={"length": 16384, "channel": 0, "priority": 1},
                transfer_fields=TransferFields(
                    kind="core_link",
                    src_core_id=0,
                    dst_core_id=1,
                    transfer_bytes=16384,
                ),
                audit_ref=AuditRef(schedule_block_ids=["sched.transfer.0"]),
            ),
        ],
    )
    analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="spec13-summary",
        records=[
            AnalysisRecord(
                record_id="analysis.record.0",
                subject_id="sched.block.0",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound"],
                audit_ref=AuditRef(schedule_block_ids=["sched.block.0"], descriptor_ids=["desc.0"]),
            ),
            AnalysisRecord(
                record_id="analysis.record.1",
                subject_id="sched.transfer.0",
                metrics={
                    "read_bytes": 8192.0,
                    "write_bytes": 8192.0,
                    "total_bytes": 16384.0,
                    "estimated_cycles": 26.0,
                    "sync_cycles": 18.0,
                    "bandwidth_pressure": 630.1538461538462,
                },
                tags=["descriptor-analysis", "sync-bound"],
                audit_ref=AuditRef(schedule_block_ids=["sched.transfer.0"], descriptor_ids=["desc.1"]),
            ),
            AnalysisRecord(
                record_id="analysis.record.2",
                subject_id="sched.block.unmapped",
                metrics={
                    "read_bytes": 0.0,
                    "write_bytes": 0.0,
                    "total_bytes": 0.0,
                    "estimated_cycles": 0.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 0.0,
                },
                tags=["descriptor-analysis", "isa-gap-bound"],
                audit_ref=AuditRef(schedule_block_ids=["sched.block.unmapped"]),
            ),
        ],
    )
    coverage = ISACoverageReport(
        graph_id="spec13-summary",
        schedule_kind="dual-core",
        mapped_descriptor_count=2,
        unmapped_block_count=1,
        opcode_counts={"WDQ_GEMM": 1, "CORE_LINK_COPY": 1},
        gap_counts={"opcode_not_supported": 1},
        issues=[],
    )
    schedule_ir = ScheduleIR(
        ir_version="phase-a.v1",
        graph_id="spec13-summary",
        core_mode="dual-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.block.0",
                core_id=0,
                node_id="nig.node.linear.0",
                macro_op="WDQ_GEMM",
                stage="compute",
                tiling_candidate_id="nig.node.linear.0.m48.n128.k128",
                resource_set=["WDQ", "MXU"],
                buffer_binding={"activation": "ping", "output": "pong"},
                barrier_in=[],
                barrier_out=[],
                depends_on=[],
                issue_slot=10,
                duration_slots=32,
                order_key=0,
                audit_ref=AuditRef(schedule_block_ids=["sched.block.0"]),
            ),
            ScheduleBlock(
                block_id="sched.transfer.0",
                core_id=0,
                peer_core_id=1,
                node_id="nig.node.linear.1",
                macro_op="WDQ_GEMM",
                stage="transfer",
                tiling_candidate_id="nig.node.linear.1.m48.n128.k128",
                resource_set=["Core Link"],
                buffer_binding={"src": "pong", "dst": "ping"},
                barrier_in=["sync.transfer.0.in"],
                barrier_out=["sync.transfer.0.out"],
                depends_on=["sched.block.0"],
                issue_slot=42,
                duration_slots=12,
                transfer_kind="core_link",
                transfer_bytes=16384,
                sync_cost_cycles=18,
                order_key=1,
                audit_ref=AuditRef(schedule_block_ids=["sched.transfer.0"]),
            ),
        ],
    )

    report = build_perf_summary_report(
        run_id="run-spec13-summary",
        descriptor_ir=descriptor_ir,
        analysis_ir=analysis_ir,
        coverage_report=coverage,
        schedule_ir=schedule_ir,
        memory_plan=_memory_plan_fixture(),
    )

    assert report.schedule_makespan_slots == 54
    assert report.per_core_makespan_slots == {"0": 54}
    assert report.per_core_busy_slots == {"0": 44}
    assert report.per_core_idle_slots == {"0": 10}
    assert report.schedule_transfer_slots == 12
    assert report.schedule_stage_slot_totals == {"compute": 32, "transfer": 12}
    assert report.data_movement_read_bytes_by_address_space == {"DDR": 8192.0, "VMEM": 8192.0}
    assert report.data_movement_write_bytes_by_address_space == {"VMEM": 8192.0}
    assert report.vmem_region_peak_bytes == {"ping": 20480, "pong": 12288, "weight": 16384}
    assert report.vmem_region_capacity_bytes == {"ping": 30720, "pong": 30720, "weight": 32768}
    assert report.vmem_region_peak_utilization == {"ping": 0.6667, "pong": 0.4, "weight": 0.5}
    assert report.totals == {
        "estimated_cycles": 74.0,
        "total_bytes": 49152.0,
        "read_bytes": 28672.0,
        "write_bytes": 20480.0,
        "sync_cycles": 18.0,
    }
    assert report.per_macro_cycles == {"WDQ_GEMM": 74.0}
    assert report.per_macro_bytes == {"WDQ_GEMM": 49152.0}
    assert report.bottleneck_counts == {
        "compute-bound": 1,
        "sync-bound": 1,
        "isa-gap-bound": 1,
    }
    assert report.isa_gap_counts == {"opcode_not_supported": 1}


def test_build_perf_summary_report_uses_union_busy_slots_instead_of_sum() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

    report = build_perf_summary_report(
        run_id="run-spec13-busy",
        descriptor_ir=DescriptorIR(ir_version="phase-a.v1", graph_id="spec13-busy", descriptors=[]),
        analysis_ir=AnalysisIR(ir_version="phase-a.v1", graph_id="spec13-busy", records=[]),
        coverage_report=ISACoverageReport(
            graph_id="spec13-busy",
            schedule_kind="dual-core",
            mapped_descriptor_count=0,
            unmapped_block_count=0,
            opcode_counts={},
            gap_counts={},
            issues=[],
        ),
        schedule_ir=ScheduleIR(
            ir_version="phase-a.v1",
            graph_id="spec13-busy",
            core_mode="dual-core",
            blocks=[
                ScheduleBlock(
                    block_id="sched.block.a",
                    core_id=0,
                    node_id="nig.node.a",
                    macro_op="WDQ_GEMM",
                    stage="compute",
                    tiling_candidate_id="cand.a",
                    resource_set=["WDQ", "MXU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=10,
                    duration_slots=20,
                    order_key=0,
                    audit_ref=AuditRef(schedule_block_ids=["sched.block.a"]),
                ),
                ScheduleBlock(
                    block_id="sched.block.b",
                    core_id=0,
                    node_id="nig.node.b",
                    macro_op="KVLOAD",
                    stage="dma_in",
                    tiling_candidate_id=None,
                    resource_set=["DMA"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=15,
                    duration_slots=10,
                    order_key=1,
                    audit_ref=AuditRef(schedule_block_ids=["sched.block.b"]),
                ),
                ScheduleBlock(
                    block_id="sched.block.c",
                    core_id=1,
                    node_id="nig.node.c",
                    macro_op="SHAPE_HELPER",
                    stage="prepare",
                    tiling_candidate_id=None,
                    resource_set=["VPU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=0,
                    duration_slots=8,
                    order_key=2,
                    audit_ref=AuditRef(schedule_block_ids=["sched.block.c"]),
                ),
            ],
        ),
        memory_plan=_memory_plan_fixture(),
    )

    assert report.schedule_makespan_slots == 30
    assert report.per_core_makespan_slots == {"0": 30, "1": 8}
    assert report.per_core_busy_slots == {"0": 20, "1": 8}
    assert report.per_core_idle_slots == {"0": 10, "1": 22}
    assert report.schedule_stage_slot_totals == {"compute": 20, "dma_in": 10, "prepare": 8}
    assert report.vmem_region_peak_bytes["ping"] == 20480


def _memory_plan_fixture():
    from llm_sched.contracts.memory_plan import MemoryPlanArtifact, RegionSummary

    return MemoryPlanArtifact(
        graph_id="spec13-summary",
        scenario_name="prefill-seq128",
        core_mode="dual-core",
        allocations=[],
        storage_bindings=[],
        region_summaries={
            "ping": RegionSummary(
                region_name="ping",
                capacity_bytes=30720,
                peak_bytes=20480,
                fits=True,
            ),
            "pong": RegionSummary(
                region_name="pong",
                capacity_bytes=30720,
                peak_bytes=12288,
                fits=True,
            ),
            "weight": RegionSummary(
                region_name="weight",
                capacity_bytes=32768,
                peak_bytes=16384,
                fits=True,
            ),
        },
        kv_formulas=[],
        diagnostics=[],
        address_diagnostics=[],
    )
