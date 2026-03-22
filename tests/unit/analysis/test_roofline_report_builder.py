from llm_sched.config.target_profile import (
    CoreLinkConfig,
    DescriptorEncodingConfig,
    KVCacheConfig,
    MXUConfig,
    QuantizationConfig,
    SharedDMAConfig,
    SyncConfig,
    TargetProfile,
    VPUConfig,
    VMEMConfig,
    WDQConfig,
)
from llm_sched.contracts.performance_diagnostics_report import (
    BandwidthDiagnostics,
    BottleneckClassification,
    CriticalPathSummary,
    LayerHotspotEntry,
    NodeHotspotEntry,
    PerformanceDiagnosticsReport,
    PhaseBreakdownEntry,
    SupportGapDiagnostics,
    VMEMDiagnostics,
)
from llm_sched.contracts.resource_demand_report import (
    LayerDemandEntry,
    ResourceDemandEntry,
    ResourceDemandReport,
    ResourceDemandTotals,
    StructureDemandEntry,
)


def test_build_roofline_report_derives_ceilings_points_bound_and_headroom() -> None:
    from llm_sched.analysis.roofline_report_builder import build_roofline_report

    report = build_roofline_report(
        run_id="run-diagnosis-001",
        target_profile=_target_profile(),
        resource_demand_report=_resource_demand_report(),
        performance_diagnostics_report=_performance_diagnostics_report(),
    )

    assert report.graph_id == "graph::gemma3-prefill"
    assert report.schedule_kind == "single-core"
    assert report.report_kind == "prefill"
    assert report.compute_ceiling.peak_ops_per_cycle == 64.0
    assert [(entry.ceiling_id, entry.bandwidth_bytes_per_cycle) for entry in report.bandwidth_ceilings] == [
        ("shared_dma", 2.0),
        ("core_link", 1.0),
    ]
    assert report.node_points[0].node_id == "nig.node.q_proj.0"
    assert report.node_points[0].arithmetic_intensity == 32.0
    assert report.node_points[0].achieved_ops_per_cycle == 64.0
    assert report.node_points[0].dominant_bound == "compute"
    assert report.node_points[0].active_bandwidth_ceiling_id == "shared_dma"
    assert report.node_points[0].headroom_ratio == 0.0
    assert report.node_points[1].dominant_bound == "bandwidth"
    assert report.node_points[1].headroom_ratio == 0.0
    assert report.layer_points[0].layer_id == 0
    assert report.layer_points[0].dominant_bound == "bandwidth"
    assert report.dominant_bound_summary.dominant_bound == "bandwidth"
    assert report.dominant_bound_summary.node_counts == {"bandwidth": 1, "compute": 1}
    assert report.headroom_summary.max_headroom_ratio == 0.0
    assert report.headroom_summary.mean_headroom_ratio == 0.0
    assert report.headroom_summary.most_limited_node_id == "nig.node.q_proj.0"


def test_build_roofline_report_rejects_graph_id_mismatch() -> None:
    from llm_sched.analysis.roofline_report_builder import build_roofline_report

    performance_report = _performance_diagnostics_report().model_copy(
        update={"graph_id": "graph::other"},
        deep=True,
    )

    try:
        build_roofline_report(
            run_id="run-diagnosis-001",
            target_profile=_target_profile(),
            resource_demand_report=_resource_demand_report(),
            performance_diagnostics_report=performance_report,
        )
    except ValueError as exc:
        assert "graph_id" in str(exc)
    else:
        raise AssertionError("expected graph_id mismatch to fail")


def _target_profile() -> TargetProfile:
    return TargetProfile(
        profile_name="roofline_test_target",
        version="1.0",
        core_mode="single-core",
        num_cores=1,
        shared_dma=SharedDMAConfig(channels=4, effective_bandwidth_gbps=16.0),
        vmem=VMEMConfig(per_core_kb=64, regions={"ping": 32, "pong": 32}),
        quantization=QuantizationConfig(
            weight_dtype="int4",
            activation_dtype="bf16",
            group_sizes=[128],
        ),
        opcodes=["WDQ_GEMM", "ROPE"],
        sync=SyncConfig(barrier_cost_cycles=12, cross_core_transfer_cost_cycles=0),
        vpu=VPUConfig(lanes=64, sublanes=4, controls_mxu=True),
        mxu=MXUConfig(rows=8, cols=8, dataflow="weight_stationary"),
        wdq=WDQConfig(enabled=True, supported_group_sizes=[128]),
        kv_cache=KVCacheConfig(layout="LBHSD", storage="ddr", dtype="bf16"),
        core_link=CoreLinkConfig(enabled=True, bandwidth_gbps=8.0),
        descriptor_encoding=DescriptorEncodingConfig(),
    )


def _resource_demand_report() -> ResourceDemandReport:
    return ResourceDemandReport(
        run_id="run-diagnosis-001",
        graph_id="graph::gemma3-prefill",
        scenario_name="prefill_seq128",
        node_demands=[
            ResourceDemandEntry(
                subject_id="nig.node.q_proj.0",
                layer_id=0,
                structure_id="structure.layer0.attention_block",
                macro_op="WDQ_GEMM",
                phase="projection",
                compute_ops=6400.0,
                read_bytes=160.0,
                write_bytes=40.0,
                working_set_bytes=80.0,
                dependency_depth=1,
            ),
            ResourceDemandEntry(
                subject_id="nig.node.rope.0",
                layer_id=0,
                structure_id="structure.layer0.attention_block",
                macro_op="ROPE",
                phase="attention",
                compute_ops=800.0,
                read_bytes=150.0,
                write_bytes=50.0,
                working_set_bytes=60.0,
                dependency_depth=1,
            ),
        ],
        layer_demands=[
            LayerDemandEntry(
                layer_id=0,
                compute_ops=7200.0,
                read_bytes=310.0,
                write_bytes=90.0,
                working_set_bytes=140.0,
                dependency_depth=1,
                node_count=2,
                structure_ids=["structure.layer0.attention_block"],
            )
        ],
        structure_demands=[
            StructureDemandEntry(
                structure_id="structure.layer0.attention_block",
                layer_id=0,
                structure_kind="attention_block",
                compute_ops=7200.0,
                read_bytes=310.0,
                write_bytes=90.0,
                working_set_bytes=140.0,
                dependency_depth=1,
                node_count=2,
            )
        ],
        totals=ResourceDemandTotals(
            compute_ops=7200.0,
            read_bytes=310.0,
            write_bytes=90.0,
            working_set_bytes=140.0,
            node_count=2,
            layer_count=1,
            structure_count=1,
        ),
        assumptions=[],
    )


def _performance_diagnostics_report() -> PerformanceDiagnosticsReport:
    return PerformanceDiagnosticsReport(
        run_id="run-diagnosis-001",
        graph_id="graph::gemma3-prefill",
        scenario_name="prefill_seq128",
        schedule_kind="single-core",
        report_kind="prefill",
        phase_breakdown=[
            PhaseBreakdownEntry(
                phase="projection",
                estimated_cycles=100.0,
                fitted_work_cycles=100.0,
                critical_path_share=0.8,
                total_bytes=200.0,
            )
        ],
        layer_hotspots=[
            LayerHotspotEntry(
                layer_id=0,
                estimated_cycles=110.0,
                fitted_work_cycles=120.0,
                cycle_share=1.0,
                fitted_cycle_share=1.0,
                total_bytes=400.0,
            )
        ],
        node_hotspots=[
            NodeHotspotEntry(
                node_id="nig.node.q_proj.0",
                estimated_cycles=100.0,
                fitted_work_cycles=100.0,
                cycle_share=0.8,
                fitted_cycle_share=0.8,
                total_bytes=200.0,
            ),
            NodeHotspotEntry(
                node_id="nig.node.rope.0",
                estimated_cycles=90.0,
                fitted_work_cycles=100.0,
                cycle_share=0.2,
                fitted_cycle_share=0.2,
                total_bytes=200.0,
            ),
        ],
        critical_path_summary=CriticalPathSummary(
            critical_path_cycles=120.0,
            estimated_cycles=190.0,
            fitted_work_cycles=200.0,
            critical_path_minus_estimated_cycles=-70.0,
            critical_path_minus_fitted_cycles=-80.0,
            critical_path_blocks=["sched.block.q_proj.compute"],
            dominant_phase="projection",
            dominant_macro="WDQ_GEMM",
        ),
        bottleneck_classification=BottleneckClassification(
            dominant_bottleneck="compute-bound",
            bottleneck_counts={"compute-bound": 1, "bandwidth-bound": 1},
            issue_count=0,
            issues=[],
        ),
        bandwidth_diagnostics=BandwidthDiagnostics(
            peak_bandwidth_pressure=2.0,
            peak_pressure_subject_id="nig.node.rope.0",
            dominant_read_address_space="DDR",
            dominant_write_address_space="VMEM",
            dominant_read_backing_store="ddr-backed-staged",
            dominant_write_backing_store="vmem-local",
            dominant_read_memory_class="WEIGHT",
            dominant_write_memory_class="ACTIVATION",
            read_bytes_by_address_space={"DDR": 310.0},
            write_bytes_by_address_space={"VMEM": 90.0},
        ),
        vmem_diagnostics=VMEMDiagnostics(),
        support_gap_diagnostics=SupportGapDiagnostics(),
    )
