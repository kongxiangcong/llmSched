from llm_sched.config.scenario_profile import LayerScope, ReportingConfig, ScenarioProfile
from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
from llm_sched.ir.descriptor_ir import AddressField, DescriptorPackingProfile, TransferFields
import pytest


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
                    "fitted_work_cycles": 64.0,
                    "schedule_floor_cycles": 32.0,
                    "external_bandwidth_floor_cycles": 64.0,
                    "fit_floor_gap_cycles": 16.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
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
                    "fitted_work_cycles": 26.0,
                    "schedule_floor_cycles": 12.0,
                    "external_bandwidth_floor_cycles": 0.0,
                    "fit_floor_gap_cycles": 0.0,
                    "sync_cycles": 18.0,
                    "bandwidth_pressure": 630.1538461538462,
                },
                tags=["descriptor-analysis", "sync-bound", "fit-floor:estimated"],
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
                    "fitted_work_cycles": 0.0,
                    "schedule_floor_cycles": 0.0,
                    "external_bandwidth_floor_cycles": 0.0,
                    "fit_floor_gap_cycles": 0.0,
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
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.0"],
                    source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
                ),
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
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.transfer.0"],
                    source_ids=["onnx::/model/layers.1/self_attn/q_proj/MatMul_output_0"],
                ),
            ),
        ],
    )

    report = build_perf_summary_report(
        run_id="run-spec13-summary",
        descriptor_ir=descriptor_ir,
        analysis_ir=analysis_ir,
        coverage_report=coverage,
        scenario=_prefill_scenario_fixture(),
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
    assert report.vmem_region_peak_bytes_by_memory_class == {
        "ping": {"ACTIVATION": 20480},
        "pong": {"ACTIVATION": 12288},
        "weight": {"WEIGHT": 16384},
    }
    assert report.bandwidth_pressure_summary.peak_bandwidth_pressure == 32768.0 / 48.0
    assert report.bandwidth_pressure_summary.peak_pressure_subject_id == "sched.block.0"
    assert report.bandwidth_pressure_summary.dominant_write_address_space == "VMEM"
    assert report.bandwidth_pressure_summary.dominant_read_backing_store == "ddr-backed-staged"
    assert report.bandwidth_pressure_summary.dominant_write_backing_store == "vmem-local"
    assert report.bandwidth_pressure_summary.dominant_read_memory_class == "WEIGHT"
    assert report.bandwidth_pressure_summary.dominant_write_memory_class == "ACTIVATION"
    assert report.vmem_pressure_summary.hottest_region == "ping"
    assert report.vmem_pressure_summary.hottest_region_peak_bytes == 20480
    assert report.vmem_pressure_summary.hottest_region_capacity_bytes == 30720
    assert report.vmem_pressure_summary.hottest_region_utilization == 0.6667
    assert report.vmem_pressure_summary.hottest_region_dominant_memory_class == "ACTIVATION"
    assert report.vmem_pressure_summary.hottest_region_dominant_backing_store == "vmem-local"
    assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(16.0)
    assert report.fit_gap_summary.total_fit_gap_ratio == pytest.approx(16.0 / 74.0)
    assert report.fit_gap_summary.critical_path_gap_cycles == pytest.approx(54.0 - 74.0)
    assert report.fit_gap_summary.critical_path_ratio_vs_estimated == pytest.approx(54.0 / 74.0)
    assert report.fit_gap_summary.dominant_fit_gap_phase == "projection"
    assert report.fit_gap_summary.dominant_fit_gap_macro == "WDQ_GEMM"
    assert report.critical_path_fit_gap_summary.critical_path_minus_estimated_cycles == pytest.approx(
        54.0 - 74.0
    )
    assert report.critical_path_fit_gap_summary.critical_path_minus_fitted_cycles == pytest.approx(
        54.0 - 90.0
    )
    assert report.critical_path_fit_gap_summary.dominant_phase_vs_estimated == "projection"
    assert report.critical_path_fit_gap_summary.dominant_phase_vs_fitted == "projection"
    assert report.critical_path_fit_gap_summary.dominant_macro_vs_estimated == "WDQ_GEMM"
    assert report.critical_path_fit_gap_summary.dominant_macro_vs_fitted == "WDQ_GEMM"
    assert report.fit_floor_source_summary.schedule_floor_gap_cycles == pytest.approx(0.0)
    assert report.fit_floor_source_summary.external_bandwidth_gap_cycles == pytest.approx(16.0)
    assert report.fit_floor_source_summary.estimated_dominant_subject_count == 1
    assert report.fit_floor_source_summary.schedule_floor_dominant_subject_count == 0
    assert report.fit_floor_source_summary.external_bandwidth_dominant_subject_count == 1
    assert report.fit_floor_source_summary.dominant_floor_source == "external_bandwidth"
    assert report.fit_floor_source_summary.dominant_floor_phase == "projection"
    assert report.fit_floor_source_summary.dominant_floor_macro == "WDQ_GEMM"
    assert report.vmem_region_capacity_bytes == {"ping": 30720, "pong": 30720, "weight": 32768}
    assert report.vmem_region_peak_utilization == {"ping": 0.6667, "pong": 0.4, "weight": 0.5}
    assert report.totals == {
        "estimated_cycles": 74.0,
        "fitted_work_cycles": 90.0,
        "critical_path_cycles": 54.0,
        "total_bytes": 49152.0,
        "read_bytes": 28672.0,
        "write_bytes": 20480.0,
        "sync_cycles": 18.0,
    }
    assert report.phase_attribution["projection"].estimated_cycles == 48.0
    assert report.phase_attribution["projection"].fitted_work_cycles == 64.0
    assert report.phase_attribution["projection"].compute_cycles == 48.0
    assert report.phase_attribution["projection"].memory_cycles == 0.0
    assert report.phase_attribution["projection"].sync_cycles == 0.0
    assert report.phase_attribution["projection"].schedule_compression_cycles == 16.0
    assert report.phase_attribution["projection"].schedule_compression_ratio == 16.0 / 48.0
    assert report.phase_attribution["projection"].schedule_overhang_cycles == 0.0
    assert report.phase_attribution["projection"].total_bytes == 32768.0
    assert report.phase_attribution["projection"].cycles_per_token == 48.0 / 128.0
    assert report.phase_attribution["projection"].bytes_per_token == 32768.0 / 128.0
    assert report.phase_attribution["projection"].occupied_slots == 32.0
    assert report.phase_attribution["projection"].occupied_slots_per_token == 32.0 / 128.0
    assert report.phase_attribution["projection"].per_core_occupied_slots == {"0": 32.0, "1": 0.0}
    assert report.phase_attribution["projection"].per_core_span_slots == {"0": 32.0, "1": 0.0}
    assert report.phase_attribution["projection"].occupied_slot_imbalance_slots == 32.0
    assert report.phase_attribution["projection"].occupied_slot_balance_ratio == 0.0
    assert report.phase_attribution["projection"].span_imbalance_slots == 32.0
    assert report.phase_attribution["projection"].span_balance_ratio == 0.0
    assert report.phase_attribution["projection"].read_bytes_by_address_space == {"DDR": 8192.0}
    assert report.phase_attribution["projection"].write_bytes_by_address_space == {}
    assert report.phase_attribution["projection"].read_bytes_by_backing_store == {
        "ddr-backed-staged": 8192.0
    }
    assert report.phase_attribution["projection"].write_bytes_by_backing_store == {}
    assert report.phase_attribution["projection"].read_bytes_by_memory_class == {"WEIGHT": 8192.0}
    assert report.phase_attribution["projection"].write_bytes_by_memory_class == {}
    assert report.phase_attribution["sync"].estimated_cycles == 18.0
    assert report.phase_attribution["sync"].fitted_work_cycles == 18.0
    assert report.phase_attribution["sync"].compute_cycles == 0.0
    assert report.phase_attribution["sync"].memory_cycles == 0.0
    assert report.phase_attribution["sync"].sync_cycles == 18.0
    assert report.phase_attribution["sync"].schedule_compression_cycles == 0.0
    assert report.phase_attribution["sync"].schedule_compression_ratio == 0.0
    assert report.phase_attribution["sync"].schedule_overhang_cycles == 0.0
    assert report.phase_attribution["sync"].total_bytes == 0.0
    assert report.phase_attribution["sync"].cycles_per_token == 18.0 / 128.0
    assert report.phase_attribution["sync"].occupied_slots == 0.0
    assert report.phase_attribution["sync"].per_core_occupied_slots == {"0": 0.0, "1": 0.0}
    assert report.phase_attribution["sync"].per_core_span_slots == {"0": 0.0, "1": 0.0}
    assert report.phase_attribution["sync"].occupied_slot_imbalance_slots == 0.0
    assert report.phase_attribution["sync"].occupied_slot_balance_ratio == 0.0
    assert report.phase_attribution["sync"].span_imbalance_slots == 0.0
    assert report.phase_attribution["sync"].span_balance_ratio == 0.0
    assert report.phase_attribution["sync"].read_bytes_by_address_space == {}
    assert report.phase_attribution["sync"].write_bytes_by_address_space == {}
    assert report.phase_attribution["sync"].read_bytes_by_backing_store == {}
    assert report.phase_attribution["sync"].write_bytes_by_backing_store == {}
    assert report.phase_attribution["sync"].read_bytes_by_memory_class == {}
    assert report.phase_attribution["sync"].write_bytes_by_memory_class == {}
    assert report.phase_attribution["kv_io"].estimated_cycles == 0.0
    assert report.phase_attribution["attention"].estimated_cycles == 0.0
    assert report.phase_attribution["other"].estimated_cycles == 8.0
    assert report.phase_attribution["other"].fitted_work_cycles == 8.0
    assert report.phase_attribution["other"].compute_cycles == 0.0
    assert report.phase_attribution["other"].memory_cycles == 8.0
    assert report.phase_attribution["other"].sync_cycles == 0.0
    assert report.phase_attribution["other"].schedule_compression_cycles == 0.0
    assert report.phase_attribution["other"].schedule_compression_ratio == 0.0
    assert report.phase_attribution["other"].schedule_overhang_cycles == 4.0
    assert report.phase_attribution["other"].total_bytes == 16384.0
    assert report.phase_attribution["other"].bytes_per_token == 16384.0 / 128.0
    assert report.phase_attribution["other"].occupied_slots == 12.0
    assert report.phase_attribution["other"].per_core_occupied_slots == {"0": 12.0, "1": 0.0}
    assert report.phase_attribution["other"].per_core_span_slots == {"0": 12.0, "1": 0.0}
    assert report.phase_attribution["other"].occupied_slot_imbalance_slots == 12.0
    assert report.phase_attribution["other"].occupied_slot_balance_ratio == 0.0
    assert report.phase_attribution["other"].span_imbalance_slots == 12.0
    assert report.phase_attribution["other"].span_balance_ratio == 0.0
    assert report.phase_attribution["other"].read_bytes_by_address_space == {"VMEM": 8192.0}
    assert report.phase_attribution["other"].write_bytes_by_address_space == {"VMEM": 8192.0}
    assert report.phase_attribution["other"].read_bytes_by_backing_store == {"vmem-local": 8192.0}
    assert report.phase_attribution["other"].write_bytes_by_backing_store == {"vmem-local": 8192.0}
    assert report.phase_attribution["other"].read_bytes_by_memory_class == {"ACTIVATION": 8192.0}
    assert report.phase_attribution["other"].write_bytes_by_memory_class == {"ACTIVATION": 8192.0}
    assert report.per_macro_cycles == {"WDQ_GEMM": 74.0}
    assert report.per_macro_fitted_work_cycles == {"WDQ_GEMM": 90.0}
    assert report.per_macro_bytes == {"WDQ_GEMM": 49152.0}
    assert report.per_node_cycles == {
        "nig.node.linear.0": 48.0,
        "nig.node.linear.1": 26.0,
    }
    assert report.per_node_fitted_work_cycles == {
        "nig.node.linear.0": 64.0,
        "nig.node.linear.1": 26.0,
    }
    assert report.per_node_bytes == {
        "nig.node.linear.0": 32768.0,
        "nig.node.linear.1": 16384.0,
    }
    assert report.per_layer_cycles == {
        "0": 48.0,
        "1": 26.0,
    }
    assert report.per_layer_fitted_work_cycles == {
        "0": 64.0,
        "1": 26.0,
    }
    assert report.per_layer_bytes == {
        "0": 32768.0,
        "1": 16384.0,
    }
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
    assert report.totals["critical_path_cycles"] == 30.0
    assert report.vmem_region_peak_bytes["ping"] == 20480


def test_build_perf_summary_report_uses_union_semantics_for_phase_occupied_slots() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

    report = build_perf_summary_report(
        run_id="run-spec13-phase-occupied",
        descriptor_ir=DescriptorIR(ir_version="phase-a.v1", graph_id="spec13-phase-occupied", descriptors=[]),
        analysis_ir=AnalysisIR(ir_version="phase-a.v1", graph_id="spec13-phase-occupied", records=[]),
        coverage_report=ISACoverageReport(
            graph_id="spec13-phase-occupied",
            schedule_kind="single-core",
            mapped_descriptor_count=0,
            unmapped_block_count=0,
            opcode_counts={},
            gap_counts={},
            issues=[],
        ),
        scenario=_prefill_scenario_fixture(),
        schedule_ir=ScheduleIR(
            ir_version="phase-a.v1",
            graph_id="spec13-phase-occupied",
            core_mode="single-core",
            blocks=[
                ScheduleBlock(
                    block_id="sched.proj.a",
                    core_id=0,
                    node_id="nig.node.proj.a",
                    macro_op="WDQ_GEMM",
                    stage="compute",
                    tiling_candidate_id="cand.proj.a",
                    resource_set=["WDQ", "MXU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=10,
                    duration_slots=20,
                    order_key=0,
                    audit_ref=AuditRef(schedule_block_ids=["sched.proj.a"]),
                ),
                ScheduleBlock(
                    block_id="sched.proj.b",
                    core_id=0,
                    node_id="nig.node.proj.b",
                    macro_op="WDQ_GEMM",
                    stage="prepare",
                    tiling_candidate_id="cand.proj.b",
                    resource_set=["VPU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=15,
                    duration_slots=10,
                    order_key=1,
                    audit_ref=AuditRef(schedule_block_ids=["sched.proj.b"]),
                ),
            ],
        ),
        memory_plan=_memory_plan_fixture(),
    )

    assert report.phase_attribution["projection"].occupied_slots == 20.0
    assert report.phase_attribution["projection"].occupied_slots_per_token == 20.0 / 128.0
    assert report.phase_attribution["projection"].per_core_occupied_slots == {"0": 20.0}
    assert report.phase_attribution["projection"].per_core_span_slots == {"0": 20.0}
    assert report.phase_attribution["projection"].occupied_slot_imbalance_slots == 0.0
    assert report.phase_attribution["projection"].occupied_slot_balance_ratio == 1.0
    assert report.phase_attribution["projection"].span_imbalance_slots == 0.0
    assert report.phase_attribution["projection"].span_balance_ratio == 1.0
    assert report.phase_attribution["other"].occupied_slots == 0.0


def test_build_perf_summary_report_derives_per_core_phase_balance() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

    report = build_perf_summary_report(
        run_id="run-spec13-phase-balance",
        descriptor_ir=DescriptorIR(ir_version="phase-a.v1", graph_id="spec13-phase-balance", descriptors=[]),
        analysis_ir=AnalysisIR(ir_version="phase-a.v1", graph_id="spec13-phase-balance", records=[]),
        coverage_report=ISACoverageReport(
            graph_id="spec13-phase-balance",
            schedule_kind="dual-core",
            mapped_descriptor_count=0,
            unmapped_block_count=0,
            opcode_counts={},
            gap_counts={},
            issues=[],
        ),
        scenario=_prefill_scenario_fixture(),
        schedule_ir=ScheduleIR(
            ir_version="phase-a.v1",
            graph_id="spec13-phase-balance",
            core_mode="dual-core",
            blocks=[
                ScheduleBlock(
                    block_id="sched.proj.core0.a",
                    core_id=0,
                    node_id="nig.node.proj.core0.a",
                    macro_op="WDQ_GEMM",
                    stage="compute",
                    tiling_candidate_id="cand.proj.core0.a",
                    resource_set=["WDQ", "MXU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=10,
                    duration_slots=10,
                    order_key=0,
                    audit_ref=AuditRef(schedule_block_ids=["sched.proj.core0.a"]),
                ),
                ScheduleBlock(
                    block_id="sched.proj.core0.b",
                    core_id=0,
                    node_id="nig.node.proj.core0.b",
                    macro_op="WDQ_GEMM",
                    stage="prepare",
                    tiling_candidate_id="cand.proj.core0.b",
                    resource_set=["VPU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=25,
                    duration_slots=10,
                    order_key=1,
                    audit_ref=AuditRef(schedule_block_ids=["sched.proj.core0.b"]),
                ),
                ScheduleBlock(
                    block_id="sched.proj.core1.a",
                    core_id=1,
                    node_id="nig.node.proj.core1.a",
                    macro_op="WDQ_GEMM",
                    stage="compute",
                    tiling_candidate_id="cand.proj.core1.a",
                    resource_set=["WDQ", "MXU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=12,
                    duration_slots=8,
                    order_key=2,
                    audit_ref=AuditRef(schedule_block_ids=["sched.proj.core1.a"]),
                ),
            ],
        ),
        memory_plan=_memory_plan_fixture(),
    )

    assert report.phase_attribution["projection"].occupied_slots == 28.0
    assert report.phase_attribution["projection"].per_core_occupied_slots == {"0": 20.0, "1": 8.0}
    assert report.phase_attribution["projection"].per_core_span_slots == {"0": 25.0, "1": 8.0}
    assert report.phase_attribution["projection"].occupied_slot_imbalance_slots == 12.0
    assert report.phase_attribution["projection"].occupied_slot_balance_ratio == 8.0 / 20.0
    assert report.phase_attribution["projection"].span_imbalance_slots == 17.0
    assert report.phase_attribution["projection"].span_balance_ratio == 8.0 / 25.0


def test_build_perf_summary_report_propagates_peak_bytes_by_backing_store() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.descriptor_ir import DescriptorIR

    report = build_perf_summary_report(
        run_id="run-spec13-backing-store",
        descriptor_ir=DescriptorIR(ir_version="phase-a.v1", graph_id="spec13-summary", descriptors=[]),
        analysis_ir=AnalysisIR(ir_version="phase-a.v1", graph_id="spec13-summary", records=[]),
        coverage_report=ISACoverageReport(
            graph_id="spec13-summary",
            schedule_kind="single-core",
            mapped_descriptor_count=0,
            unmapped_block_count=0,
            opcode_counts={},
            gap_counts={},
            issues=[],
        ),
        memory_plan=_memory_plan_fixture(),
    )

    assert report.vmem_region_peak_bytes_by_backing_store == {
        "ping": {"vmem-local": 20480, "ddr-backed-staged": 0, "ddr-persistent": 0},
        "pong": {"vmem-local": 12288, "ddr-backed-staged": 0, "ddr-persistent": 0},
        "weight": {"vmem-local": 0, "ddr-backed-staged": 16384, "ddr-persistent": 0},
    }
    assert report.vmem_region_peak_bytes_by_memory_class == {
        "ping": {"ACTIVATION": 20480},
        "pong": {"ACTIVATION": 12288},
        "weight": {"WEIGHT": 16384},
    }


def test_build_perf_summary_report_aggregates_multiple_blocks_into_node_totals() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorPackingProfile, DescriptorRecord
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

    descriptor_ir = DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="spec13-node-aggregate",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.a",
                schedule_block_id="sched.block.a",
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
                shape_pack={"m": 32, "n": 64, "k": 64},
                addr_fields={},
                address_fields=[],
                dma_fields={},
                audit_ref=AuditRef(schedule_block_ids=["sched.block.a"]),
            ),
            DescriptorRecord(
                descriptor_id="desc.b",
                schedule_block_id="sched.block.b",
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
                shape_pack={"m": 32, "n": 64, "k": 64},
                addr_fields={},
                address_fields=[],
                dma_fields={},
                audit_ref=AuditRef(schedule_block_ids=["sched.block.b"]),
            ),
        ],
    )

    report = build_perf_summary_report(
        run_id="run-spec13-node-aggregate",
        descriptor_ir=descriptor_ir,
        analysis_ir=AnalysisIR(
            ir_version="phase-a.v1",
            graph_id="spec13-node-aggregate",
            records=[
                AnalysisRecord(
                    record_id="analysis.record.a",
                    subject_id="sched.block.a",
                    metrics={
                        "read_bytes": 1024.0,
                        "write_bytes": 512.0,
                        "total_bytes": 1536.0,
                        "estimated_cycles": 20.0,
                        "sync_cycles": 0.0,
                        "bandwidth_pressure": 51.2,
                    },
                    tags=["descriptor-analysis", "compute-bound"],
                    audit_ref=AuditRef(schedule_block_ids=["sched.block.a"], descriptor_ids=["desc.a"]),
                ),
                AnalysisRecord(
                    record_id="analysis.record.b",
                    subject_id="sched.block.b",
                    metrics={
                        "read_bytes": 2048.0,
                        "write_bytes": 1024.0,
                        "total_bytes": 3072.0,
                        "estimated_cycles": 28.0,
                        "sync_cycles": 0.0,
                        "bandwidth_pressure": 73.1,
                    },
                    tags=["descriptor-analysis", "compute-bound"],
                    audit_ref=AuditRef(schedule_block_ids=["sched.block.b"], descriptor_ids=["desc.b"]),
                ),
            ],
        ),
        coverage_report=ISACoverageReport(
            graph_id="spec13-node-aggregate",
            schedule_kind="single-core",
            mapped_descriptor_count=2,
            unmapped_block_count=0,
            opcode_counts={"WDQ_GEMM": 2},
            gap_counts={},
            issues=[],
        ),
        schedule_ir=ScheduleIR(
            ir_version="phase-a.v1",
            graph_id="spec13-node-aggregate",
            core_mode="single-core",
            blocks=[
                ScheduleBlock(
                    block_id="sched.block.a",
                    core_id=0,
                    node_id="nig.node.shared",
                    macro_op="WDQ_GEMM",
                    stage="compute",
                    tiling_candidate_id="cand.a",
                    resource_set=["WDQ", "MXU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=[],
                    issue_slot=0,
                    duration_slots=20,
                    order_key=0,
                    audit_ref=AuditRef(
                        schedule_block_ids=["sched.block.a"],
                        source_ids=["onnx::/model/layers.3/mlp/gemm"],
                    ),
                ),
                ScheduleBlock(
                    block_id="sched.block.b",
                    core_id=0,
                    node_id="nig.node.shared",
                    macro_op="WDQ_GEMM",
                    stage="compute",
                    tiling_candidate_id="cand.b",
                    resource_set=["WDQ", "MXU"],
                    buffer_binding={},
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=["sched.block.a"],
                    issue_slot=20,
                    duration_slots=28,
                    order_key=1,
                    audit_ref=AuditRef(
                        schedule_block_ids=["sched.block.b"],
                        source_ids=["onnx::/model/layers.3/mlp/rmsnorm_gemm"],
                    ),
                ),
            ],
        ),
        memory_plan=_memory_plan_fixture(),
    )

    assert report.per_node_cycles == {"nig.node.shared": 48.0}
    assert report.per_node_bytes == {"nig.node.shared": 4608.0}
    assert report.per_layer_cycles == {"3": 48.0}
    assert report.per_layer_bytes == {"3": 4608.0}
    assert report.totals["critical_path_cycles"] == 48.0


def test_build_perf_summary_report_preserves_residual_external_stall_fit_gap() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorRecord

    descriptor_ir = DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="spec13-residual-stall",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.compute.0",
                schedule_block_id="sched.block.compute.0",
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
                audit_ref=AuditRef(schedule_block_ids=["sched.block.compute.0"]),
            )
        ],
    )
    analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="spec13-residual-stall",
        records=[
            AnalysisRecord(
                record_id="analysis.record.compute.0",
                subject_id="sched.block.compute.0",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 112.0,
                    "schedule_floor_cycles": 64.0,
                    "external_read_floor_cycles": 96.0,
                    "external_write_floor_cycles": 0.0,
                    "external_bandwidth_floor_cycles": 96.0,
                    "fit_floor_gap_cycles": 64.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.compute.0"],
                    descriptor_ids=["desc.compute.0"],
                ),
            )
        ],
    )
    coverage = ISACoverageReport(
        graph_id="spec13-residual-stall",
        schedule_kind="single-core",
        mapped_descriptor_count=1,
        unmapped_block_count=0,
        opcode_counts={"WDQ_GEMM": 1},
        gap_counts={},
        issues=[],
    )

    report = build_perf_summary_report(
        run_id="run-spec13-residual-stall",
        descriptor_ir=descriptor_ir,
        analysis_ir=analysis_ir,
        coverage_report=coverage,
        scenario=_prefill_scenario_fixture(),
    )

    assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(64.0)
    assert report.fit_floor_source_summary.external_bandwidth_gap_cycles == pytest.approx(64.0)
    assert report.fit_floor_source_summary.dominant_floor_source == "external_bandwidth"
    assert report.fit_floor_direction_summary.external_read_gap_cycles == pytest.approx(96.0)
    assert report.fit_floor_direction_summary.external_write_gap_cycles == pytest.approx(0.0)
    assert report.fit_floor_direction_summary.dominant_external_direction == "read"
    assert report.fit_floor_direction_summary.dominant_external_phase == "projection"
    assert report.fit_floor_direction_summary.dominant_external_macro == "WDQ_GEMM"
    assert report.totals["estimated_cycles"] == pytest.approx(48.0)
    assert report.totals["fitted_work_cycles"] == pytest.approx(112.0)
    assert report.phase_attribution["projection"].fitted_work_cycles == pytest.approx(112.0)


def test_build_perf_summary_report_preserves_bidirectional_shared_dma_fit_gap() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorRecord

    descriptor_ir = DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="spec13-bidirectional-stall",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.compute.0",
                schedule_block_id="sched.block.compute.0",
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
                audit_ref=AuditRef(schedule_block_ids=["sched.block.compute.0"]),
            )
        ],
    )
    analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="spec13-bidirectional-stall",
        records=[
            AnalysisRecord(
                record_id="analysis.record.compute.0",
                subject_id="sched.block.compute.0",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 128.0,
                    "schedule_floor_cycles": 64.0,
                    "external_read_floor_cycles": 96.0,
                    "external_write_floor_cycles": 32.0,
                    "external_bandwidth_floor_cycles": 128.0,
                    "fit_floor_gap_cycles": 80.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.compute.0"],
                    descriptor_ids=["desc.compute.0"],
                ),
            )
        ],
    )
    coverage = ISACoverageReport(
        graph_id="spec13-bidirectional-stall",
        schedule_kind="single-core",
        mapped_descriptor_count=1,
        unmapped_block_count=0,
        opcode_counts={"WDQ_GEMM": 1},
        gap_counts={},
        issues=[],
    )

    report = build_perf_summary_report(
        run_id="run-spec13-bidirectional-stall",
        descriptor_ir=descriptor_ir,
        analysis_ir=analysis_ir,
        coverage_report=coverage,
        scenario=_prefill_scenario_fixture(),
    )

    assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(80.0)
    assert report.fit_floor_source_summary.external_bandwidth_gap_cycles == pytest.approx(80.0)
    assert report.fit_floor_source_summary.dominant_floor_source == "external_bandwidth"
    assert report.fit_floor_direction_summary.external_read_gap_cycles == pytest.approx(96.0)
    assert report.fit_floor_direction_summary.external_write_gap_cycles == pytest.approx(32.0)
    assert report.fit_floor_direction_summary.dominant_external_direction == "read"
    assert report.fit_floor_direction_summary.dominant_external_phase == "projection"
    assert report.fit_floor_direction_summary.dominant_external_macro == "WDQ_GEMM"
    assert report.totals["estimated_cycles"] == pytest.approx(48.0)
    assert report.totals["fitted_work_cycles"] == pytest.approx(128.0)
    assert report.phase_attribution["projection"].fitted_work_cycles == pytest.approx(128.0)


def test_build_perf_summary_report_preserves_external_write_drain_fit_gap() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorRecord

    descriptor_ir = DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="spec13-write-drain",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.compute.0",
                schedule_block_id="sched.block.compute.0",
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
                audit_ref=AuditRef(schedule_block_ids=["sched.block.compute.0"]),
            )
        ],
    )
    analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="spec13-write-drain",
        records=[
            AnalysisRecord(
                record_id="analysis.record.compute.0",
                subject_id="sched.block.compute.0",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 80.0,
                    "schedule_floor_cycles": 48.0,
                    "external_read_floor_cycles": 0.0,
                    "external_write_floor_cycles": 32.0,
                    "external_bandwidth_floor_cycles": 32.0,
                    "fit_floor_gap_cycles": 32.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.compute.0"],
                    descriptor_ids=["desc.compute.0"],
                ),
            )
        ],
    )
    coverage = ISACoverageReport(
        graph_id="spec13-write-drain",
        schedule_kind="single-core",
        mapped_descriptor_count=1,
        unmapped_block_count=0,
        opcode_counts={"WDQ_GEMM": 1},
        gap_counts={},
        issues=[],
    )

    report = build_perf_summary_report(
        run_id="run-spec13-write-drain",
        descriptor_ir=descriptor_ir,
        analysis_ir=analysis_ir,
        coverage_report=coverage,
        scenario=_prefill_scenario_fixture(),
    )

    assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(32.0)
    assert report.fit_floor_source_summary.external_bandwidth_gap_cycles == pytest.approx(32.0)
    assert report.fit_floor_direction_summary.external_read_gap_cycles == pytest.approx(0.0)
    assert report.fit_floor_direction_summary.external_write_gap_cycles == pytest.approx(32.0)
    assert report.fit_floor_direction_summary.dominant_external_direction == "write"
    assert report.totals["estimated_cycles"] == pytest.approx(48.0)
    assert report.totals["fitted_work_cycles"] == pytest.approx(80.0)
    assert report.phase_attribution["projection"].fitted_work_cycles == pytest.approx(80.0)


def test_build_perf_summary_report_preserves_schedule_slack_absorbed_write_drain() -> None:
    from llm_sched.analysis.descriptor_estimator import build_perf_summary_report
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorRecord

    descriptor_ir = DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="spec13-write-slack",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.compute.0",
                schedule_block_id="sched.block.compute.0",
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
                audit_ref=AuditRef(schedule_block_ids=["sched.block.compute.0"]),
            )
        ],
    )
    analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="spec13-write-slack",
        records=[
            AnalysisRecord(
                record_id="analysis.record.compute.0",
                subject_id="sched.block.compute.0",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 80.0,
                    "schedule_floor_cycles": 64.0,
                    "external_read_floor_cycles": 0.0,
                    "external_write_floor_cycles": 32.0,
                    "external_bandwidth_floor_cycles": 32.0,
                    "fit_floor_gap_cycles": 32.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.compute.0"],
                    descriptor_ids=["desc.compute.0"],
                ),
            )
        ],
    )
    coverage = ISACoverageReport(
        graph_id="spec13-write-slack",
        schedule_kind="single-core",
        mapped_descriptor_count=1,
        unmapped_block_count=0,
        opcode_counts={"WDQ_GEMM": 1},
        gap_counts={},
        issues=[],
    )

    report = build_perf_summary_report(
        run_id="run-spec13-write-slack",
        descriptor_ir=descriptor_ir,
        analysis_ir=analysis_ir,
        coverage_report=coverage,
        scenario=_prefill_scenario_fixture(),
    )

    assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(32.0)
    assert report.fit_floor_source_summary.external_bandwidth_gap_cycles == pytest.approx(32.0)
    assert report.fit_floor_direction_summary.external_write_gap_cycles == pytest.approx(32.0)
    assert report.totals["estimated_cycles"] == pytest.approx(48.0)
    assert report.totals["fitted_work_cycles"] == pytest.approx(80.0)


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
                peak_bytes_by_memory_class={"ACTIVATION": 20480},
                peak_bytes_by_backing_store={"vmem-local": 20480, "ddr-backed-staged": 0, "ddr-persistent": 0},
            ),
            "pong": RegionSummary(
                region_name="pong",
                capacity_bytes=30720,
                peak_bytes=12288,
                fits=True,
                peak_bytes_by_memory_class={"ACTIVATION": 12288},
                peak_bytes_by_backing_store={"vmem-local": 12288, "ddr-backed-staged": 0, "ddr-persistent": 0},
            ),
            "weight": RegionSummary(
                region_name="weight",
                capacity_bytes=32768,
                peak_bytes=16384,
                fits=True,
                peak_bytes_by_memory_class={"WEIGHT": 16384},
                peak_bytes_by_backing_store={"vmem-local": 0, "ddr-backed-staged": 16384, "ddr-persistent": 0},
            ),
        },
        kv_formulas=[],
        diagnostics=[],
        address_diagnostics=[],
    )


def _prefill_scenario_fixture() -> ScenarioProfile:
    return ScenarioProfile(
        scenario_name="prefill_seq128",
        version="phase-a.v1",
        mode="prefill",
        batch=1,
        seq_len=128,
        kv_len=0,
        layer_scope=LayerScope(kind="all"),
        reporting=ReportingConfig(include_layer_breakdown=True, include_bandwidth=True),
    )
