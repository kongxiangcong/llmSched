from llm_sched.contracts.isa_coverage_report import ISACoverageIssue, ISACoverageReport
from llm_sched.contracts.tiling_plan import (
    TileCandidate,
    TileCandidateResourceSummary,
    TilingPlanArtifact,
)
from llm_sched.ir.common import AuditRef
from llm_sched.ir.descriptor_ir import (
    AddressField,
    DescriptorIR,
    DescriptorPackingProfile,
    DescriptorRecord,
    TransferFields,
)
from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR


def test_estimate_descriptor_analysis_emits_compute_dma_transfer_and_gap_records() -> None:
    from llm_sched.analysis import estimate_descriptor_analysis

    analysis = estimate_descriptor_analysis(
        _descriptor_ir_fixture(),
        _coverage_report_fixture(),
        _test_target_profile(),
        _test_prefill_scenario(),
    )

    assert [record.subject_id for record in analysis.records] == [
        "sched.block.linear.compute",
        "sched.block.linear.dma_in",
        "sched.transfer.linear",
        "sched.block.unmapped",
    ]

    compute_record = analysis.records[0]
    assert compute_record.metrics == {
        "read_bytes": 20480.0,
        "write_bytes": 12288.0,
        "total_bytes": 32768.0,
        "estimated_cycles": 48.0,
        "fitted_work_cycles": 48.0,
        "schedule_floor_cycles": 0.0,
        "external_read_floor_cycles": 0.0,
        "external_write_floor_cycles": 0.0,
        "external_bandwidth_floor_cycles": 0.0,
        "fit_floor_gap_cycles": 0.0,
        "sync_cycles": 0.0,
        "bandwidth_pressure": 682.6666666666666,
    }
    assert compute_record.tags == ["descriptor-analysis", "compute-bound", "fit-floor:estimated"]

    dma_record = analysis.records[1]
    assert dma_record.metrics == {
        "read_bytes": 8192.0,
        "write_bytes": 0.0,
        "total_bytes": 8192.0,
        "estimated_cycles": 7.0,
        "fitted_work_cycles": 7.0,
        "schedule_floor_cycles": 0.0,
        "external_read_floor_cycles": 0.0,
        "external_write_floor_cycles": 0.0,
        "external_bandwidth_floor_cycles": 0.0,
        "fit_floor_gap_cycles": 0.0,
        "sync_cycles": 0.0,
        "bandwidth_pressure": 1170.2857142857142,
    }
    assert dma_record.tags == ["descriptor-analysis", "memory-bound", "fit-floor:estimated"]

    transfer_record = analysis.records[2]
    assert transfer_record.metrics == {
        "read_bytes": 8192.0,
        "write_bytes": 8192.0,
        "total_bytes": 16384.0,
        "estimated_cycles": 26.0,
        "fitted_work_cycles": 26.0,
        "schedule_floor_cycles": 0.0,
        "external_read_floor_cycles": 0.0,
        "external_write_floor_cycles": 0.0,
        "external_bandwidth_floor_cycles": 0.0,
        "fit_floor_gap_cycles": 0.0,
        "sync_cycles": 18.0,
        "bandwidth_pressure": 630.1538461538462,
    }
    assert transfer_record.tags == ["descriptor-analysis", "sync-bound", "fit-floor:estimated"]

    gap_record = analysis.records[3]
    assert gap_record.metrics == {
        "read_bytes": 0.0,
        "write_bytes": 0.0,
        "total_bytes": 0.0,
        "estimated_cycles": 0.0,
        "fitted_work_cycles": 0.0,
        "schedule_floor_cycles": 0.0,
        "external_read_floor_cycles": 0.0,
        "external_write_floor_cycles": 0.0,
        "external_bandwidth_floor_cycles": 0.0,
        "fit_floor_gap_cycles": 0.0,
        "sync_cycles": 0.0,
        "bandwidth_pressure": 0.0,
    }
    assert gap_record.tags == ["descriptor-analysis", "isa-gap-bound"]


def test_estimate_descriptor_analysis_uses_schedule_duration_floor() -> None:
    from llm_sched.analysis import estimate_descriptor_analysis

    descriptor_ir = _descriptor_ir_fixture().model_copy(deep=True)
    descriptor_ir.descriptors[0].ctrl_fields["duration_slots"] = 64

    analysis = estimate_descriptor_analysis(
        descriptor_ir,
        _coverage_report_fixture(),
        _test_target_profile(),
        _test_prefill_scenario(),
    )

    compute_record = next(record for record in analysis.records if record.subject_id == "sched.block.linear.compute")
    assert compute_record.metrics["estimated_cycles"] == 64.0
    assert compute_record.metrics["fitted_work_cycles"] == 64.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 0.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 0.0
    assert "fit-floor:estimated" in compute_record.tags


def test_estimate_descriptor_analysis_raises_fitted_work_cycles_for_tiled_external_reads() -> None:
    from llm_sched.analysis import estimate_descriptor_analysis

    analysis = estimate_descriptor_analysis(
        _descriptor_ir_fixture(),
        _coverage_report_fixture(),
        _test_target_profile(),
        _test_prefill_scenario(),
        schedule_ir=_schedule_ir_fixture(),
        tiling_plan=_tiling_plan_fixture(ddr_backed_staged_bytes=122880),
    )

    compute_record = next(record for record in analysis.records if record.subject_id == "sched.block.linear.compute")
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["fitted_work_cycles"] == 96.0
    assert compute_record.metrics["schedule_floor_cycles"] == 48.0
    assert compute_record.metrics["external_read_floor_cycles"] == 96.0
    assert compute_record.metrics["external_write_floor_cycles"] == 0.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 96.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 48.0
    assert "fit-floor:external_bandwidth" in compute_record.tags


def test_estimate_descriptor_analysis_adds_residual_external_stall_above_schedule_floor() -> None:
    from llm_sched.analysis import estimate_descriptor_analysis

    schedule_ir = _schedule_ir_fixture().model_copy(
        update={
            "blocks": [
                block.model_copy(update={"duration_slots": 64})
                if block.block_id == "sched.block.linear.compute"
                else block
                for block in _schedule_ir_fixture().blocks
            ]
        }
    )

    analysis = estimate_descriptor_analysis(
        _descriptor_ir_fixture(),
        _coverage_report_fixture(),
        _test_target_profile(),
        _test_prefill_scenario(),
        schedule_ir=schedule_ir,
        tiling_plan=_tiling_plan_fixture(ddr_backed_staged_bytes=122880),
    )

    compute_record = next(record for record in analysis.records if record.subject_id == "sched.block.linear.compute")
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_read_floor_cycles"] == 96.0
    assert compute_record.metrics["external_write_floor_cycles"] == 0.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 96.0
    assert compute_record.metrics["fitted_work_cycles"] == 112.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 64.0
    assert "fit-floor:external_bandwidth" in compute_record.tags


def test_tiling_plan_fixture_preserves_external_write_backing_store_bytes() -> None:
    tiling_plan = _tiling_plan_fixture(
        ddr_backed_staged_bytes=122880,
        ddr_backed_staged_write_bytes=40960,
    )

    resource_summary = tiling_plan.candidates[0].resource_summary
    assert resource_summary is not None
    assert resource_summary.storage_write_bytes_by_backing_store == {"ddr-backed-staged": 40960}


def test_estimate_descriptor_analysis_adds_residual_external_write_stall() -> None:
    from llm_sched.analysis import estimate_descriptor_analysis

    analysis = estimate_descriptor_analysis(
        _descriptor_ir_fixture(),
        _coverage_report_fixture(),
        _test_target_profile(),
        _test_prefill_scenario(),
        schedule_ir=_schedule_ir_fixture(),
        tiling_plan=_tiling_plan_fixture(
            ddr_backed_staged_bytes=0,
            ddr_backed_staged_write_bytes=40960,
        ),
    )

    compute_record = next(record for record in analysis.records if record.subject_id == "sched.block.linear.compute")
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["external_read_floor_cycles"] == 0.0
    assert compute_record.metrics["external_write_floor_cycles"] == 32.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 32.0
    assert compute_record.metrics["fitted_work_cycles"] == 80.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 32.0


def test_estimate_descriptor_analysis_adds_bidirectional_shared_dma_stall_above_schedule_floor() -> None:
    from llm_sched.analysis import estimate_descriptor_analysis

    schedule_ir = _schedule_ir_fixture().model_copy(
        update={
            "blocks": [
                block.model_copy(update={"duration_slots": 64})
                if block.block_id == "sched.block.linear.compute"
                else block
                for block in _schedule_ir_fixture().blocks
            ]
        }
    )

    analysis = estimate_descriptor_analysis(
        _descriptor_ir_fixture(),
        _coverage_report_fixture(),
        _test_target_profile(),
        _test_prefill_scenario(),
        schedule_ir=schedule_ir,
        tiling_plan=_tiling_plan_fixture(
            ddr_backed_staged_bytes=122880,
            ddr_backed_staged_write_bytes=40960,
        ),
    )

    compute_record = next(record for record in analysis.records if record.subject_id == "sched.block.linear.compute")
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_read_floor_cycles"] == 96.0
    assert compute_record.metrics["external_write_floor_cycles"] == 32.0
    assert compute_record.metrics["external_bandwidth_floor_cycles"] == 128.0
    assert compute_record.metrics["fitted_work_cycles"] == 128.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 80.0
    assert "fit-floor:external_bandwidth" in compute_record.tags


def test_estimate_descriptor_analysis_uses_schedule_slack_to_absorb_external_write_drain() -> None:
    from llm_sched.analysis import estimate_descriptor_analysis

    schedule_ir = _schedule_ir_fixture().model_copy(
        update={
            "blocks": [
                block.model_copy(update={"duration_slots": 64})
                if block.block_id == "sched.block.linear.compute"
                else block
                for block in _schedule_ir_fixture().blocks
            ]
        }
    )

    analysis = estimate_descriptor_analysis(
        _descriptor_ir_fixture(),
        _coverage_report_fixture(),
        _test_target_profile(),
        _test_prefill_scenario(),
        schedule_ir=schedule_ir,
        tiling_plan=_tiling_plan_fixture(
            ddr_backed_staged_bytes=0,
            ddr_backed_staged_write_bytes=40960,
        ),
    )

    compute_record = next(record for record in analysis.records if record.subject_id == "sched.block.linear.compute")
    assert compute_record.metrics["estimated_cycles"] == 48.0
    assert compute_record.metrics["schedule_floor_cycles"] == 64.0
    assert compute_record.metrics["external_write_floor_cycles"] == 32.0
    assert compute_record.metrics["fitted_work_cycles"] == 80.0
    assert compute_record.metrics["fit_floor_gap_cycles"] == 32.0


def _descriptor_ir_fixture() -> DescriptorIR:
    return DescriptorIR(
        ir_version="phase-a.v1",
        graph_id="spec13-graph",
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.linear.compute",
                schedule_block_id="sched.block.linear.compute",
                opcode="WDQ_GEMM",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"stage": "compute", "macro_op": "WDQ_GEMM"},
                packing_profile=DescriptorPackingProfile(
                    stage_family="compute",
                    opcode_family="tensor_compute",
                    layout_template="wdq_compute_v1",
                    field_groups=["ctrl", "shape", "addr"],
                    required_ctrl_fields=["stage", "macro_op"],
                    required_shape_axes=["m", "n", "k"],
                    required_addr_roles=["activation", "weight", "output"],
                    required_dma_fields=[],
                    field_widths={
                        "opcode": 16,
                        "control": 16,
                        "shape": 16,
                        "act_addr": 64,
                        "weight_addr": 64,
                        "dst_addr_low": 32,
                    },
                ),
                shape_pack={"m": 48, "n": 128, "k": 128},
                addr_fields={"activation": "VMEM:ping", "weight": "VMEM:weight", "output": "VMEM:pong"},
                address_fields=[
                    AddressField(
                        role="activation",
                        address_space="VMEM",
                        region_name="ping",
                        offset_bytes=0,
                        symbol="VMEM:ping",
                        descriptor_field="ACT_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                    AddressField(
                        role="weight",
                        address_space="VMEM",
                        region_name="weight",
                        offset_bytes=0,
                        symbol="VMEM:weight",
                        descriptor_field="WEIGHT_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                    AddressField(
                        role="output",
                        address_space="VMEM",
                        region_name="pong",
                        offset_bytes=0,
                        symbol="VMEM:pong",
                        descriptor_field="DST_ADDR",
                        encoded_width_bits=32,
                        uses_addr_ext=False,
                    ),
                ],
                dma_fields={},
                source_ref=["onnx::MatMul_0"],
                audit_ref=AuditRef(schedule_block_ids=["sched.block.linear.compute"]),
            ),
            DescriptorRecord(
                descriptor_id="desc.linear.dma",
                schedule_block_id="sched.block.linear.dma_in",
                opcode="DMA_LOAD",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"stage": "dma_in", "macro_op": "WDQ_GEMM"},
                packing_profile=DescriptorPackingProfile(
                    stage_family="dma",
                    opcode_family="dma_load",
                    layout_template="dma_load_v1",
                    field_groups=["ctrl", "shape", "addr", "dma"],
                    required_ctrl_fields=["stage", "macro_op"],
                    required_shape_axes=["m", "n", "k"],
                    required_addr_roles=["activation", "dst"],
                    required_dma_fields=["length", "channel", "priority"],
                    field_widths={
                        "opcode": 16,
                        "control": 16,
                        "shape": 16,
                        "act_addr": 64,
                        "dst_addr_low": 32,
                        "dma_length": 32,
                        "dma_channel": 8,
                        "dma_priority": 4,
                    },
                ),
                shape_pack={"m": 48, "n": 128, "k": 128},
                addr_fields={"activation": "DDR:act", "dst": "VMEM:ping"},
                address_fields=[
                    AddressField(
                        role="activation",
                        address_space="DDR",
                        region_name="act",
                        offset_bytes=0,
                        symbol="DDR:act",
                        descriptor_field="ACT_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                    AddressField(
                        role="dst",
                        address_space="VMEM",
                        region_name="ping",
                        offset_bytes=0,
                        symbol="VMEM:ping",
                        descriptor_field="DST_ADDR",
                        encoded_width_bits=32,
                        uses_addr_ext=False,
                    ),
                ],
                dma_fields={"length": 8192, "channel": 0, "priority": 1},
                source_ref=["onnx::MatMul_0"],
                audit_ref=AuditRef(schedule_block_ids=["sched.block.linear.dma_in"]),
            ),
            DescriptorRecord(
                descriptor_id="desc.transfer.0",
                schedule_block_id="sched.transfer.linear",
                opcode="CORE_LINK_COPY",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"stage": "transfer", "macro_op": "WDQ_GEMM"},
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
                addr_fields={"src": "VMEM:pong", "dst": "VMEM:ping"},
                address_fields=[
                    AddressField(
                        role="src",
                        address_space="VMEM",
                        region_name="pong",
                        offset_bytes=0,
                        symbol="VMEM:pong",
                        descriptor_field="SRC_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                    AddressField(
                        role="dst",
                        address_space="VMEM",
                        region_name="ping",
                        offset_bytes=0,
                        symbol="VMEM:ping",
                        descriptor_field="DST_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                ],
                dma_fields={"length": 8192, "channel": 0, "priority": 1},
                transfer_fields=TransferFields(
                    kind="core_link",
                    src_core_id=0,
                    dst_core_id=1,
                    transfer_bytes=8192,
                ),
                source_ref=["onnx::MatMul_0"],
                audit_ref=AuditRef(schedule_block_ids=["sched.transfer.linear"]),
            ),
        ],
    )


def _coverage_report_fixture() -> ISACoverageReport:
    return ISACoverageReport(
        graph_id="spec13-graph",
        schedule_kind="dual-core",
        mapped_descriptor_count=3,
        unmapped_block_count=1,
        opcode_counts={"WDQ_GEMM": 1, "DMA_LOAD": 1, "CORE_LINK_COPY": 1},
        gap_counts={"opcode_not_supported": 1},
        issues=[
            ISACoverageIssue(
                issue_id="gap.0",
                schedule_block_id="sched.block.unmapped",
                core_id=1,
                stage="compute",
                macro_op="ATTENTION_MASK_PREP",
                requested_opcode="ATTENTION_MASK_PREP",
                code="opcode_not_supported",
                message="target profile does not advertise ATTENTION_MASK_PREP",
            )
        ],
    )


def _schedule_ir_fixture() -> ScheduleIR:
    return ScheduleIR(
        ir_version="phase-a.v1",
        graph_id="spec13-graph",
        core_mode="dual-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.block.linear.compute",
                core_id=0,
                node_id="nig.node.linear.compute",
                macro_op="WDQ_GEMM",
                stage="compute",
                tiling_candidate_id="nig.node.linear.compute.m48.n128.k128",
                resource_set=["WDQ", "MXU"],
                buffer_binding={"activation": "ping", "output": "pong"},
                barrier_in=[],
                barrier_out=[],
                depends_on=[],
                issue_slot=0,
                duration_slots=48,
                order_key=0,
                audit_ref=AuditRef(schedule_block_ids=["sched.block.linear.compute"]),
            ),
            ScheduleBlock(
                block_id="sched.block.linear.dma_in",
                core_id=0,
                node_id="nig.node.linear.dma",
                macro_op="WDQ_GEMM",
                stage="dma_in",
                tiling_candidate_id=None,
                resource_set=["DMA"],
                buffer_binding={"activation": "ping"},
                barrier_in=[],
                barrier_out=[],
                depends_on=[],
                issue_slot=48,
                duration_slots=7,
                order_key=1,
                audit_ref=AuditRef(schedule_block_ids=["sched.block.linear.dma_in"]),
            ),
            ScheduleBlock(
                block_id="sched.transfer.linear",
                core_id=0,
                peer_core_id=1,
                node_id="nig.node.linear.transfer",
                macro_op="WDQ_GEMM",
                stage="transfer",
                tiling_candidate_id=None,
                resource_set=["Core Link"],
                buffer_binding={"src": "pong", "dst": "ping"},
                barrier_in=["sync.transfer.linear.in"],
                barrier_out=["sync.transfer.linear.out"],
                depends_on=["sched.block.linear.compute"],
                issue_slot=55,
                duration_slots=26,
                transfer_kind="core_link",
                transfer_bytes=8192,
                sync_cost_cycles=18,
                order_key=2,
                audit_ref=AuditRef(schedule_block_ids=["sched.transfer.linear"]),
            ),
        ],
    )


def _tiling_plan_fixture(
    *,
    ddr_backed_staged_bytes: int,
    ddr_backed_staged_write_bytes: int = 0,
) -> TilingPlanArtifact:
    return TilingPlanArtifact(
        graph_id="spec13-graph",
        scenario_name="prefill-seq128",
        core_mode="dual-core",
        candidates=[
            TileCandidate(
                candidate_id="nig.node.linear.compute.m48.n128.k128",
                node_id="nig.node.linear.compute",
                macro_op="WDQ_GEMM",
                strategy="throughput-first",
                m_tile=48,
                n_tile=128,
                k_tile=128,
                read_bytes=32768,
                write_bytes=12288,
                total_vmem_bytes=45056,
                rank=1,
                ranking_reason="fixture",
                quant_alignment_ok=True,
                quant_alignment_message="aligned",
                source_memory_plan_region_pressure={"ping": 20480, "pong": 12288},
                resource_summary=TileCandidateResourceSummary(
                    read_bytes=32768,
                    write_bytes=12288,
                    total_vmem_bytes=45056,
                    dma_bytes=0,
                    region_pressure_bytes={"ping": 20480, "pong": 12288},
                    storage_binding_ids=["storage.weight"],
                    storage_read_bytes_by_source_kind={"weight_tensor": ddr_backed_staged_bytes},
                    storage_read_bytes_by_backing_store={"ddr-backed-staged": ddr_backed_staged_bytes},
                    storage_write_bytes_by_backing_store={"ddr-backed-staged": ddr_backed_staged_write_bytes},
                ),
                issues=[],
            )
        ],
    )


def _test_prefill_scenario():
    from llm_sched.config.scenario_profile import LayerScope, ReportingConfig, ScenarioProfile

    return ScenarioProfile(
        scenario_name="prefill-seq128",
        version="phase-a.v1",
        mode="prefill",
        batch=1,
        seq_len=128,
        kv_len=0,
        layer_scope=LayerScope(kind="all"),
        reporting=ReportingConfig(include_layer_breakdown=True, include_bandwidth=True),
    )


def _test_target_profile():
    from llm_sched.config.target_profile import (
        CoreLinkConfig,
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

    return TargetProfile(
        profile_name="test-target",
        version="phase-a.v1",
        core_mode="dual-core",
        num_cores=2,
        shared_dma=SharedDMAConfig(channels=8, effective_bandwidth_gbps=20.0),
        vmem=VMEMConfig(
            per_core_kb=128,
            regions={
                "ping": 30,
                "pong": 30,
                "weight": 32,
                "accum": 24,
                "misc": 4,
                "wdq_reserved": 4,
                "quant": 4,
            },
        ),
        quantization=QuantizationConfig(weight_dtype="int4", activation_dtype="bf16", group_sizes=[128]),
        opcodes=["WDQ_GEMM", "DMA_LOAD", "DMA_STORE", "CORE_LINK_COPY"],
        sync=SyncConfig(barrier_cost_cycles=12, cross_core_transfer_cost_cycles=18),
        vpu=VPUConfig(lanes=128, sublanes=8, controls_mxu=True),
        mxu=MXUConfig(rows=128, cols=128, dataflow="weight_stationary"),
        wdq=WDQConfig(enabled=True, supported_group_sizes=[128]),
        kv_cache=KVCacheConfig(layout="LBHSD", storage="ddr", dtype="bf16"),
        core_link=CoreLinkConfig(enabled=True, bandwidth_gbps=16.0),
    )
