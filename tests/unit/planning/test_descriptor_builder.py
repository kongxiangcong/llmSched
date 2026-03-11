from pathlib import Path


def test_build_descriptor_artifacts_maps_single_core_compute_blocks() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.single_core_scheduler import plan_single_core_schedule
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [_make_wdq_gemm_node(node_id="nig.node.linear", output_shape=[1, 128, 1024], group_size=128)]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)
    schedule = plan_single_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    descriptor_ir, coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    compute_descriptor = next(
        descriptor
        for descriptor in descriptor_ir.descriptors
        if descriptor.schedule_block_id.endswith(".compute")
    )
    assert compute_descriptor.opcode == "WDQ_GEMM"
    assert compute_descriptor.encoding_bits == 512
    assert compute_descriptor.packing_profile.stage_family == "compute"
    assert compute_descriptor.packing_profile.opcode_family == "wdq_gemm_compute"
    assert compute_descriptor.packing_profile.layout_template == "wdq_compute_v1"
    assert compute_descriptor.packing_profile.required_shape_axes == ["m", "n", "k"]
    assert compute_descriptor.packing_profile.field_layout[:4] == [
        "opcode",
        "control",
        "order_key",
        "group_size",
    ]
    assert compute_descriptor.packing_profile.field_widths["opcode"] == 16
    assert compute_descriptor.packing_profile.field_widths["shape_m"] == 16
    assert compute_descriptor.packing_profile.field_widths["shape_n"] == 16
    assert compute_descriptor.packing_profile.field_widths["shape_k"] == 16
    assert compute_descriptor.packing_profile.field_widths["dst_addr_low"] == 32
    assert compute_descriptor.ctrl_fields["issue_slot"] >= 0
    assert compute_descriptor.ctrl_fields["duration_slots"] > 0
    assert compute_descriptor.shape_pack == {"m": 48, "n": 128, "k": 128}
    assert {field.role for field in compute_descriptor.address_fields} >= {"input", "weight", "output"}
    output_field = next(field for field in compute_descriptor.address_fields if field.role == "output")
    assert output_field.descriptor_field == "DST_ADDR"
    assert output_field.encoded_width_bits == 32
    dma_load_descriptor = next(
        descriptor
        for descriptor in descriptor_ir.descriptors
        if descriptor.opcode == "DMA_LOAD"
    )
    dma_store_descriptor = next(
        descriptor
        for descriptor in descriptor_ir.descriptors
        if descriptor.opcode == "DMA_STORE"
    )
    assert dma_load_descriptor.packing_profile.stage_family == "dma"
    assert dma_load_descriptor.packing_profile.opcode_family == "dma_load"
    assert dma_load_descriptor.packing_profile.layout_template == "dma_load_v1"
    assert dma_load_descriptor.packing_profile.required_dma_fields == ["length", "channel", "priority"]
    assert dma_load_descriptor.packing_profile.field_layout[-3:] == [
        "dma_length",
        "dma_channel",
        "dma_priority",
    ]
    assert dma_store_descriptor.packing_profile.opcode_family == "dma_store"
    assert dma_store_descriptor.packing_profile.layout_template == "dma_store_v1"
    assert {field.role for field in dma_load_descriptor.address_fields} >= {"input", "weight"}
    assert dma_load_descriptor.dma_fields["length"] > 0
    assert dma_store_descriptor.dma_fields["length"] > 0
    assert coverage.mapped_descriptor_count == len(descriptor_ir.descriptors)
    assert coverage.unmapped_block_count == 0


def test_build_descriptor_artifacts_propagates_storage_binding_metadata_into_address_fields() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.single_core_scheduler import plan_single_core_schedule
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [_make_wdq_gemm_node(node_id="nig.node.linear", output_shape=[1, 128, 1024], group_size=128)]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)
    schedule = plan_single_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    descriptor_ir, _coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    compute_descriptor = next(
        descriptor
        for descriptor in descriptor_ir.descriptors
        if descriptor.schedule_block_id.endswith(".compute")
    )
    weight_field = next(field for field in compute_descriptor.address_fields if field.role == "weight")
    output_field = next(field for field in compute_descriptor.address_fields if field.role == "output")

    assert weight_field.storage_binding_id is not None
    assert weight_field.storage_binding_id.startswith("storage.weight.")
    assert weight_field.backing_store == "ddr-backed-staged"
    assert output_field.storage_binding_id is None
    assert output_field.backing_store == "vmem-local"


def test_build_descriptor_artifacts_maps_dual_core_transfer_blocks() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node(
                node_id="nig.node.linear.0",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="act0",
                output_name="mid0",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.linear.1",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="mid0",
                output_name="out1",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)
    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    descriptor_ir, coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    transfer_descriptor = next(
        descriptor
        for descriptor in descriptor_ir.descriptors
        if descriptor.transfer_fields is not None
    )
    assert transfer_descriptor.opcode == "CORE_LINK_COPY"
    assert transfer_descriptor.packing_profile.stage_family == "transfer"
    assert transfer_descriptor.packing_profile.opcode_family == "core_link_transfer"
    assert transfer_descriptor.packing_profile.layout_template == "core_link_transfer_v1"
    assert transfer_descriptor.packing_profile.field_layout[:3] == [
        "opcode",
        "control",
        "order_key",
    ]
    assert transfer_descriptor.packing_profile.field_layout[-4:] == [
        "transfer_kind",
        "transfer_src_core_id",
        "transfer_dst_core_id",
        "transfer_bytes",
    ]
    assert transfer_descriptor.packing_profile.field_widths["transfer_kind"] == 8
    assert transfer_descriptor.packing_profile.field_widths["transfer_bytes"] == 32
    assert transfer_descriptor.transfer_fields is not None
    assert transfer_descriptor.transfer_fields.kind == "core_link"
    assert transfer_descriptor.transfer_fields.dst_core_id == 1
    assert transfer_descriptor.ctrl_fields["issue_slot"] >= 0
    assert transfer_descriptor.ctrl_fields["duration_slots"] > 0
    assert {field.role for field in transfer_descriptor.address_fields} == {"src", "dst"}
    assert {field.descriptor_field for field in transfer_descriptor.address_fields} == {"SRC_ADDR", "DST_ADDR"}
    assert coverage.opcode_counts["CORE_LINK_COPY"] == 1


def test_build_descriptor_artifacts_specializes_dma_transfer_layout_by_transport() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    target = target.model_copy(
        update={
            "core_link": target.core_link.model_copy(
                update={"enabled": False, "bandwidth_gbps": 0}
            )
        }
    )
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node(
                node_id="nig.node.linear.0",
                output_shape=[1, 1, 1024],
                group_size=128,
                input_name="act0",
                output_name="mid0",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.linear.1",
                output_shape=[1, 1, 1024],
                group_size=128,
                input_name="mid0",
                output_name="out1",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)
    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    descriptor_ir, coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    transfer_descriptor = next(
        descriptor
        for descriptor in descriptor_ir.descriptors
        if descriptor.transfer_fields is not None
    )
    assert transfer_descriptor.opcode == "DMA_TRANSFER"
    assert transfer_descriptor.packing_profile.opcode_family == "dma_transfer"
    assert transfer_descriptor.packing_profile.layout_template == "dma_transfer_v1"
    assert transfer_descriptor.transfer_fields is not None
    assert transfer_descriptor.transfer_fields.kind == "dma"
    assert coverage.opcode_counts["DMA_TRANSFER"] == 1


def test_build_descriptor_artifacts_reports_unsupported_blocks_as_gaps() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_unmapped_node(
                node_id="nig.node.mask",
                output_shape=[1, 128, 1024],
            )
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    schedule = ScheduleIR(
        ir_version="phase-a.v1",
        graph_id=bound_nig.graph_id,
        core_mode="single-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.nig.node.mask.compute",
                core_id=0,
                node_id="nig.node.mask",
                macro_op="ATTENTION_MASK_PREP",
                stage="compute",
                tiling_candidate_id="nig.node.mask.m48.n128.k128",
                resource_set=["VPU"],
                buffer_binding={"activation": "misc"},
                barrier_in=[],
                barrier_out=[],
                order_key=0,
                audit_ref=AuditRef(nig_node_ids=["nig.node.mask"]),
            )
        ],
    )

    descriptor_ir, coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    assert descriptor_ir.descriptors == []
    assert coverage.unmapped_block_count == 1
    assert coverage.gap_counts["compute_opcode_not_supported"] == 1
    assert coverage.issues[0].schedule_block_id == "sched.nig.node.mask.compute"
    assert coverage.issues[0].code == "compute_opcode_not_supported"


def test_build_descriptor_artifacts_reports_transfer_transport_gaps() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    target = target.model_copy(
        update={
            "core_link": target.core_link.model_copy(
                update={"enabled": False, "bandwidth_gbps": 0}
            )
        }
    )
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")
    bound_nig = _make_bound_nig_ir(
        [_make_wdq_gemm_node(node_id="nig.node.linear", output_shape=[1, 1, 1024], group_size=128)]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    schedule = ScheduleIR(
        ir_version="phase-a.v1",
        graph_id=bound_nig.graph_id,
        core_mode="dual-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.transfer.0",
                core_id=0,
                peer_core_id=1,
                node_id="nig.node.linear",
                macro_op="WDQ_GEMM",
                stage="transfer",
                tiling_candidate_id="nig.node.linear.m1.n128.k128",
                resource_set=["Core Link"],
                buffer_binding={"src": "ping", "dst": "pong"},
                barrier_in=["sync.transfer.0.in"],
                barrier_out=["sync.transfer.0.out"],
                transfer_kind="core_link",
                transfer_bytes=4096,
                sync_cost_cycles=12,
                order_key=0,
                audit_ref=AuditRef(nig_node_ids=["nig.node.linear"]),
            )
        ],
    )

    descriptor_ir, coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    assert descriptor_ir.descriptors == []
    assert coverage.unmapped_block_count == 1
    assert coverage.gap_counts["transfer_core_link_not_available"] == 1
    assert coverage.issues[0].code == "transfer_core_link_not_available"


def test_build_descriptor_artifacts_reports_address_width_overflow_as_gap() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.single_core_scheduler import plan_single_core_schedule
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    target = target.model_copy(
        update={
            "descriptor_encoding": target.descriptor_encoding.model_copy(
                update={"split_address_bits": 4}
            )
        }
    )
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [_make_wdq_gemm_node(node_id="nig.node.linear", output_shape=[1, 128, 1024], group_size=128)]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)
    schedule = plan_single_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    descriptor_ir, coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    assert not any(
        descriptor.schedule_block_id.endswith(".compute")
        for descriptor in descriptor_ir.descriptors
    )
    assert coverage.gap_counts["descriptor_address_width_overflow"] >= 1
    assert any(issue.code == "descriptor_address_width_overflow" for issue in coverage.issues)


def test_build_descriptor_artifacts_falls_back_to_min_shape_pack_for_prepare_helpers() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir([_make_shape_helper_node(node_id="nig.node.shape_helper", output_shape=[])])
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    schedule = ScheduleIR(
        ir_version="phase-a.v1",
        graph_id=bound_nig.graph_id,
        core_mode="single-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.nig.node.shape_helper.prepare",
                core_id=0,
                node_id="nig.node.shape_helper",
                macro_op="SHAPE_HELPER",
                stage="prepare",
                tiling_candidate_id=None,
                resource_set=["VPU"],
                buffer_binding={"input": "VMEM:misc"},
                barrier_in=[],
                barrier_out=[],
                order_key=0,
                audit_ref=AuditRef(nig_node_ids=["nig.node.shape_helper"]),
            )
        ],
    )

    descriptor_ir, coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    assert coverage.unmapped_block_count == 0
    assert len(descriptor_ir.descriptors) == 1
    assert descriptor_ir.descriptors[0].shape_pack == {"m": 1, "n": 1, "k": 128}


def test_build_descriptor_artifacts_stabilizes_compute_address_field_order_against_allocation_order() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.single_core_scheduler import plan_single_core_schedule
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [_make_wdq_gemm_node(node_id="nig.node.linear", output_shape=[1, 128, 1024], group_size=128)]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    reversed_memory_plan = memory_plan.model_copy(update={"allocations": list(reversed(memory_plan.allocations))})
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)
    schedule = plan_single_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    descriptor_ir, _coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )
    reversed_descriptor_ir, _reversed_coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        reversed_memory_plan,
        target,
        scenario,
    )

    compute_descriptor = next(
        descriptor
        for descriptor in descriptor_ir.descriptors
        if descriptor.schedule_block_id.endswith(".compute")
    )
    reversed_compute_descriptor = next(
        descriptor
        for descriptor in reversed_descriptor_ir.descriptors
        if descriptor.schedule_block_id.endswith(".compute")
    )

    expected_roles = ["input", "weight", "scale", "zp", "output"]
    assert [field.role for field in compute_descriptor.address_fields] == expected_roles
    assert [field.role for field in reversed_compute_descriptor.address_fields] == expected_roles
    assert compute_descriptor.packing_profile.field_layout == reversed_compute_descriptor.packing_profile.field_layout


def _make_bound_nig_ir(nodes: list[object]) -> object:
    from llm_sched.ir.nig import NIGIR

    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="spec-12-fixture",
        binding_state="bound",
        nodes=nodes,
    )


def _make_wdq_gemm_node(
    node_id: str,
    output_shape: list[int],
    group_size: int,
    *,
    input_name: str = "act",
    output_name: str = "out",
) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="int4",
        activation_dtype="bf16",
        group_size=group_size,
        quant_mode="per-group",
        scale_present=True,
        zero_point_present=True,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="WDQ_GEMM",
        inputs=[input_name, "weight", "scale", "zp"],
        outputs=[output_name],
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["WDQ_GEMM"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                input_name: "ACTIVATION",
                "weight": "WEIGHT",
                "scale": "QUANT_PARAM",
                "zp": "QUANT_PARAM",
            },
            output_memory_classes={output_name: "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::MatMul_0"],
        audit_ref=AuditRef(graph_node_ids=[node_id.replace("nig.", "graph.", 1)], source_ids=["onnx::MatMul_0"]),
    )


def _make_unmapped_node(node_id: str, output_shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="bf16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="ATTENTION_MASK_PREP",
        inputs=["mask"],
        outputs=["mask.out"],
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["ATTENTION_MASK_PREP"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"mask": "ACTIVATION"},
            output_memory_classes={"mask.out": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::MaskPrep_0"],
        audit_ref=AuditRef(graph_node_ids=[node_id.replace("nig.", "graph.", 1)], source_ids=["onnx::MaskPrep_0"]),
    )


def _make_shape_helper_node(node_id: str, output_shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="bf16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="SHAPE_HELPER",
        inputs=["shape.in"],
        outputs=["shape.out"],
        shape=output_shape,
        layout="METADATA",
        memory_class="metadata",
        legal_opcodes=["SHAPE_HELPER"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="METADATA",
            memory_class="METADATA",
            input_memory_classes={"shape.in": "METADATA"},
            output_memory_classes={"shape.out": "METADATA"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::ShapeHelper_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::ShapeHelper_0"],
        ),
    )
