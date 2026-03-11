from pathlib import Path


def test_pack_descriptor_bundle_emits_eight_word_payloads_for_compute_and_transfer() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.descriptor_packer import pack_descriptor_bundle
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
    descriptor_ir, _coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    packed_bundle = pack_descriptor_bundle(descriptor_ir, target)

    assert packed_bundle.graph_id == descriptor_ir.graph_id
    assert packed_bundle.container_format == "aligned-flat-v1"
    assert packed_bundle.record_alignment_bytes == 64
    assert packed_bundle.stream_total_bytes == len(packed_bundle.descriptors) * 64
    assert packed_bundle.stream_hex.startswith("0x")
    assert len(packed_bundle.descriptors) == len(descriptor_ir.descriptors)
    compute_payload = next(payload for payload in packed_bundle.descriptors if payload.stage == "compute")
    transfer_payload = next(payload for payload in packed_bundle.descriptors if payload.stage == "transfer")
    assert len(compute_payload.word_hex) == 8
    assert len(transfer_payload.word_hex) == 8
    assert compute_payload.record_index >= 0
    assert compute_payload.stream_offset_bytes == compute_payload.record_index * 64
    assert compute_payload.stream_size_bytes == 64
    assert transfer_payload.stream_offset_bytes == transfer_payload.record_index * 64
    assert compute_payload.word_order == "lsw-first"
    assert compute_payload.byte_order == "little-endian"
    assert compute_payload.packed_hex.startswith("0x")
    assert compute_payload.stream_hex.startswith("0x")
    assert compute_payload.stream_hex != compute_payload.packed_hex
    assert any(field.field_name == "shape_m" for field in compute_payload.field_placements)
    assert any(field.field_name == "transfer_kind" for field in transfer_payload.field_placements)
    assert any(field.field_group == "addr" for field in transfer_payload.field_placements)


def test_pack_descriptor_bundle_honors_target_word_and_byte_order() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.descriptor_packer import pack_descriptor_bundle
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.single_core_scheduler import plan_single_core_schedule
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    target = target.model_copy(
        update={
            "descriptor_encoding": target.descriptor_encoding.model_copy(
                update={
                    "word_order": "msw-first",
                    "byte_order": "big-endian",
                }
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
    descriptor_ir, _coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    packed_bundle = pack_descriptor_bundle(descriptor_ir, target)

    payload = packed_bundle.descriptors[0]
    assert payload.word_order == "msw-first"
    assert payload.byte_order == "big-endian"
    assert payload.stream_hex == "0x" + "".join(word[2:] for word in reversed(payload.word_hex))


def test_pack_descriptor_bundle_honors_target_record_alignment() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.descriptor_packer import pack_descriptor_bundle
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    target = target.model_copy(
        update={
            "descriptor_encoding": target.descriptor_encoding.model_copy(
                update={"record_alignment_bytes": 128}
            )
        }
    )
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node(node_id="nig.node.linear.0", output_shape=[1, 128, 1024], group_size=128),
            _make_wdq_gemm_node(node_id="nig.node.linear.1", output_shape=[1, 128, 1024], group_size=128),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)
    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)
    descriptor_ir, _coverage = build_descriptor_artifacts(
        schedule,
        bound_nig,
        memory_plan,
        target,
        scenario,
    )

    packed_bundle = pack_descriptor_bundle(descriptor_ir, target)

    assert packed_bundle.record_alignment_bytes == 128
    assert packed_bundle.descriptors[1].stream_offset_bytes == 128
    assert packed_bundle.stream_total_bytes == ((len(packed_bundle.descriptors) - 1) * 128) + 64


def test_pack_descriptor_bundle_stabilizes_payload_against_allocation_order() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.descriptor_builder import build_descriptor_artifacts
    from llm_sched.planning.descriptor_packer import pack_descriptor_bundle
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

    packed_bundle = pack_descriptor_bundle(descriptor_ir, target)
    reversed_packed_bundle = pack_descriptor_bundle(reversed_descriptor_ir, target)
    compute_payload = next(payload for payload in packed_bundle.descriptors if payload.stage == "compute")
    reversed_compute_payload = next(
        payload for payload in reversed_packed_bundle.descriptors if payload.stage == "compute"
    )

    assert [placement.field_name for placement in compute_payload.field_placements] == [
        placement.field_name for placement in reversed_compute_payload.field_placements
    ]
    assert compute_payload.packed_hex == reversed_compute_payload.packed_hex
    assert packed_bundle.stream_hex == reversed_packed_bundle.stream_hex


def _make_bound_nig_ir(nodes: list[object]) -> object:
    from llm_sched.ir.nig import NIGIR

    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="spec-12-packed-fixture",
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
