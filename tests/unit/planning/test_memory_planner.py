from pathlib import Path


def test_plan_memory_for_quantized_gemm_uses_weight_quant_and_accum_regions() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node(
                node_id="nig.wdq.0",
                output_shape=[1, 1, 1024],
                group_size=128,
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    assert {allocation.region_name for allocation in artifact.allocations if allocation.region_name} >= {
        "weight",
        "quant",
        "wdq_reserved",
        "accum",
    }
    accum_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.wdq.0" and allocation.region_name == "accum"
    )
    weight_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.wdq.0" and allocation.region_name == "weight"
    )
    quant_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.wdq.0" and allocation.region_name == "quant"
    )
    assert accum_allocation.lifetime_bucket == "compute"
    assert weight_allocation.lifetime_bucket == "preload"
    assert weight_allocation.backing_store == "ddr-backed-staged"
    assert weight_allocation.backing_symbol.startswith("WEIGHT_BASE::")
    assert weight_allocation.storage_binding_id is not None
    assert quant_allocation.backing_store == "ddr-backed-staged"
    assert quant_allocation.backing_symbol.startswith("QUANT_BASE::")
    assert quant_allocation.storage_binding_id is not None
    weight_binding = next(
        binding
        for binding in artifact.storage_bindings
        if binding.binding_id == weight_allocation.storage_binding_id
    )
    quant_binding = next(
        binding
        for binding in artifact.storage_bindings
        if binding.binding_id == quant_allocation.storage_binding_id
    )
    assert weight_binding.source_kind == "weight_tensor"
    assert weight_binding.binding_scope == "per-tensor-base"
    assert weight_binding.symbol == weight_allocation.backing_symbol
    assert quant_binding.source_kind == "quant_tensor"
    assert quant_binding.binding_scope == "per-tensor-base"
    assert quant_binding.symbol == quant_allocation.backing_symbol
    address_kinds = {
        (diagnostic.address_kind, diagnostic.status, diagnostic.storage_binding_id)
        for diagnostic in artifact.address_diagnostics
        if diagnostic.node_id == "nig.wdq.0"
    }
    assert ("weight", "bound", weight_binding.binding_id) in address_kinds
    assert ("quant", "bound", quant_binding.binding_id) in address_kinds
    assert artifact.region_summaries["weight"].peak_bytes == 8 * 1024
    assert artifact.region_summaries["weight"].peak_lifetime_bucket == "preload"
    assert artifact.region_summaries["weight"].peak_bytes_by_memory_class["WEIGHT"] == 8 * 1024
    assert artifact.region_summaries["weight"].peak_bytes_by_backing_store["ddr-backed-staged"] == 8 * 1024
    assert artifact.region_summaries["quant"].peak_bytes == 4
    assert artifact.region_summaries["quant"].peak_bytes_by_memory_class["QUANT_PARAM"] == 4
    assert artifact.region_summaries["wdq_reserved"].peak_bytes == 1024


def test_plan_memory_for_decode_kv_ops_emits_formula_with_layer_stride() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir([_make_kvload_node("nig.kvload.12", layer_id=12)])
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    formula = artifact.kv_formulas[0]
    kv_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.kvload.12" and allocation.tensor_name == "past_key"
    )
    assert formula.layer_id == 12
    assert formula.token_stride_bytes == 512
    assert formula.kv_kind_stride_bytes == 2_049 * 512
    assert formula.layer_stride_bytes == 2 * 2_049 * 512
    assert kv_allocation.backing_store == "ddr-persistent"
    assert kv_allocation.backing_symbol == "KV_BASE"
    assert kv_allocation.storage_binding_id is not None
    kv_binding = next(
        binding
        for binding in artifact.storage_bindings
        if binding.binding_id == kv_allocation.storage_binding_id
    )
    assert kv_binding.source_kind == "kv_cache_slice"
    assert kv_binding.binding_scope == "per-layer-slice"
    assert kv_binding.symbol == "KV_BASE"
    assert kv_binding.layer_id == 12
    assert kv_binding.tensor_kind == "key"
    assert artifact.address_diagnostics[0].status == "bound"
    assert artifact.address_diagnostics[0].storage_binding_id == kv_binding.binding_id


def test_plan_memory_reports_region_overflow_with_offending_nodes() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_attention_mask_prep_node(
                node_id="nig.mask.overflow",
                shape=[1, 1, 4096, 4096],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    overflow_regions = {
        diagnostic.region_name: diagnostic
        for diagnostic in artifact.diagnostics
        if diagnostic.status == "overflow"
    }
    assert overflow_regions["ping"].offending_node_ids == ["nig.mask.overflow"]
    assert overflow_regions["pong"].offending_node_ids == ["nig.mask.overflow"]
    assert overflow_regions["ping"].required_bytes_by_memory_class["ACTIVATION"] > 0
    assert overflow_regions["ping"].required_bytes_by_backing_store["vmem-local"] > 0


def test_plan_memory_prefill_gemm_shrinks_m_tile_to_fit_accum_region() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node(
                node_id="nig.wdq.prefill.fit",
                output_shape=[1, 128, 1024],
                group_size=128,
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    accum_allocations = [
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.wdq.prefill.fit" and allocation.region_name == "accum"
    ]
    assert len(accum_allocations) == 1
    assert accum_allocations[0].size_bytes == 24 * 1024
    assert artifact.region_summaries["accum"].fits is True
    assert artifact.region_summaries["accum"].peak_bytes == 24 * 1024


def test_plan_memory_embedding_lookup_uses_token_tile_working_set() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_embedding_lookup_node(
                node_id="nig.embedding.prefill",
                output_shape=[1, 128, 1152],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    weight_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.embedding.prefill"
        and allocation.region_name == "weight"
        and allocation.tensor_name == "model.embed_tokens.weight"
    )
    output_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.embedding.prefill"
        and allocation.region_name == "pong"
        and allocation.tensor_name == "tokens.embed"
    )

    assert weight_allocation.size_bytes == 13 * 1152 * 2
    assert output_allocation.size_bytes == 13 * 1152 * 2
    assert artifact.region_summaries["weight"].fits is True
    assert artifact.region_summaries["pong"].fits is True


def test_plan_memory_layout_fallback_uses_vector_tile_working_set() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_layout_fallback_node(
                node_id="nig.layout.logits.cast",
                shape=[1, 128, 524288],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    input_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.layout.logits.cast"
        and allocation.region_name == "ping"
        and allocation.tensor_name == "logits_fp16"
    )
    output_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.layout.logits.cast"
        and allocation.region_name == "pong"
        and allocation.tensor_name == "logits"
    )

    assert input_allocation.size_bytes == 16 * 128 * 2
    assert output_allocation.size_bytes == 16 * 128 * 2
    assert artifact.region_summaries["ping"].fits is True
    assert artifact.region_summaries["pong"].fits is True


def test_plan_memory_geglu_uses_streaming_activation_tiles() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_geglu_node(
                node_id="nig.geglu.prefill",
                shape=[1, 128, 6912],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    input_allocations = [
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.geglu.prefill"
        and allocation.region_name == "ping"
        and allocation.tensor_role == "input"
    ]
    output_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.geglu.prefill"
        and allocation.region_name == "pong"
        and allocation.tensor_name == "mlp.out"
    )

    assert sorted(allocation.size_bytes for allocation in input_allocations) == [4096, 4096]
    assert output_allocation.size_bytes == 4096
    assert artifact.region_summaries["ping"].peak_bytes == 8192
    assert artifact.region_summaries["ping"].fits is True
    assert artifact.region_summaries["pong"].fits is True


def test_plan_memory_rope_table_uses_head_dim_weight_slice() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_rope_table_node(
                node_id="nig.rope.table.prefill",
                shape=[1, 128, 256],
                head_dim=256,
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    weight_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.rope.table.prefill"
        and allocation.region_name == "weight"
    )

    assert weight_allocation.size_bytes == 256
    assert artifact.region_summaries["weight"].peak_bytes == 256
    assert artifact.region_summaries["weight"].fits is True


def test_plan_memory_rope_uses_compact_misc_scratch() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_rope_node(
                node_id="nig.rope.prefill",
                shape=[1, 4, 128, 256],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    misc_allocations = [
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.rope.prefill" and allocation.region_name == "misc"
    ]

    assert sorted(allocation.size_bytes for allocation in misc_allocations) == [256, 256, 2048]
    assert artifact.region_summaries["misc"].peak_bytes == 2048
    assert artifact.region_summaries["misc"].peak_lifetime_bucket == "compute"
    assert artifact.region_summaries["misc"].fits is True


def test_plan_memory_sdpa_uses_streaming_attention_tiles() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_sdpa_node(
                node_id="nig.sdpa.prefill",
                shape=[1, 128, 1024],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    input_allocations = [
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.sdpa.prefill"
        and allocation.region_name == "ping"
        and allocation.tensor_role == "input"
    ]
    output_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.sdpa.prefill"
        and allocation.region_name == "pong"
        and allocation.tensor_name == "attn.out"
    )

    assert sorted(allocation.size_bytes for allocation in input_allocations) == [4096, 4096, 4096, 4096]
    assert output_allocation.size_bytes == 4096
    assert artifact.region_summaries["ping"].peak_bytes == 16 * 1024
    assert artifact.region_summaries["ping"].fits is True
    assert artifact.region_summaries["pong"].fits is True


def test_plan_memory_rmsnorm_gemm_stages_aux_weight_as_vector() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_rmsnorm_gemm_node(
                node_id="nig.lm_head",
                shape=[1, 128, 262144],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    projection_weight = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.lm_head"
        and allocation.region_name == "weight"
        and allocation.tensor_name == "proj_weight"
    )
    norm_weight = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.lm_head"
        and allocation.region_name == "misc"
        and allocation.tensor_name == "norm_weight"
    )

    assert projection_weight.size_bytes == 32 * 1024
    assert norm_weight.size_bytes == 256
    assert artifact.region_summaries["weight"].peak_bytes == 32 * 1024
    assert artifact.region_summaries["weight"].fits is True


def test_plan_memory_rmsnorm_uses_streaming_activation_tiles() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_rmsnorm_node(
                node_id="nig.rmsnorm.prefill",
                shape=[1, 128, 1152],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    input_allocations = [
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.rmsnorm.prefill"
        and allocation.region_name == "ping"
        and allocation.tensor_role == "input"
    ]

    assert sorted(allocation.size_bytes for allocation in input_allocations) == [4096, 4096]
    assert artifact.region_summaries["ping"].fits is True


def test_plan_memory_elem_add_uses_streaming_activation_tiles() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_elem_add_node(
                node_id="nig.elem.add.prefill",
                shape=[1, 128, 1152],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    input_allocations = [
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.elem.add.prefill"
        and allocation.region_name == "ping"
        and allocation.tensor_role == "input"
    ]

    assert sorted(allocation.size_bytes for allocation in input_allocations) == [4096, 4096]
    assert artifact.region_summaries["ping"].fits is True


def test_plan_memory_decode_kvload_uses_query_tile_output() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir([_make_kvload_node("nig.kvload.decode", layer_id=0)])
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    output_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.kvload.decode"
        and allocation.region_name == "pong"
        and allocation.tensor_name == "key_cache_tile"
    )

    assert output_allocation.size_bytes == 256
    assert artifact.region_summaries["pong"].fits is True


def test_plan_memory_decode_kvstore_uses_query_tile_activation_input() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir([_make_kvstore_node("nig.kvstore.decode", mode="decode", query_len=1)])
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    input_allocation = next(
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.kvstore.decode"
        and allocation.region_name == "ping"
        and allocation.tensor_name == "value_tile"
    )

    assert input_allocation.size_bytes == 256
    assert artifact.region_summaries["ping"].fits is True


def test_plan_memory_reports_unresolved_kv_address_when_layer_id_is_missing() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir([_make_kvload_node("nig.kvload.unknown", layer_id=None)])
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    diagnostic = artifact.address_diagnostics[0]
    assert diagnostic.status == "unresolved"
    assert diagnostic.address_kind == "kv"


def test_plan_memory_uses_lifetime_reuse_for_misc_region_peak() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact

    bound_nig = _make_bound_nig_ir(
        [
            _make_shape_helper_node(
                node_id="nig.shape.helper",
                shape=[1, 2048],
            )
        ]
    )
    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    artifact = plan_memory_artifact(bound_nig, target, scenario)

    misc_allocations = [
        allocation
        for allocation in artifact.allocations
        if allocation.node_id == "nig.shape.helper" and allocation.region_name == "misc"
    ]

    assert sorted(allocation.lifetime_bucket for allocation in misc_allocations) == ["compute", "preload", "store"]
    assert sorted(allocation.size_bytes for allocation in misc_allocations) == [256, 256, 4096]
    assert artifact.region_summaries["misc"].peak_bytes == 4096
    assert artifact.region_summaries["misc"].peak_lifetime_bucket == "compute"
    assert artifact.region_summaries["misc"].peak_bytes_by_lifetime_bucket == {
        "preload": 256,
        "compute": 4096,
        "store": 256,
        "persist": 0,
    }
    assert artifact.region_summaries["misc"].peak_bytes_by_memory_class["METADATA"] == 4096
    assert artifact.region_summaries["misc"].peak_bytes_by_backing_store["vmem-local"] == 4096


def _make_bound_nig_ir(nodes: list[object]) -> object:
    from llm_sched.ir.nig import NIGIR

    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="spec-08-fixture",
        binding_state="bound",
        nodes=nodes,
    )


def _make_wdq_gemm_node(node_id: str, output_shape: list[int], group_size: int) -> object:
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
        inputs=["act", "weight", "scale", "zp"],
        outputs=["out"],
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
                "act": "ACTIVATION",
                "weight": "WEIGHT",
                "scale": "QUANT_PARAM",
                "zp": "QUANT_PARAM",
            },
            output_memory_classes={"out": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
        ),
    )


def _make_kvload_node(node_id: str, layer_id: int | None) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import AttentionBinding, NIGBinding, NIGNode, QuantBinding

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
    attention = AttentionBinding(
        mode="decode",
        query_len=1,
        kv_len=2049,
        head_dim=256,
        num_heads=4,
        num_key_value_heads=1,
        tensor_layout="BHSD",
        kv_layout_rule="per-layer-slice-of-LBHSD",
    )
    return NIGNode(
        node_id=node_id,
        macro_op="KVLOAD",
        inputs=["past_key"],
        outputs=["key_cache_tile"],
        shape=[1, 1, 2049, 256],
        layout="BHSD",
        memory_class="kv",
        legal_opcodes=["KVLOAD"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=[1, 1, 2049, 256],
            canonical_layout="BHSD",
            memory_class="ACTIVATION",
            input_memory_classes={"past_key": "KV_CACHE"},
            output_memory_classes={"key_cache_tile": "ACTIVATION"},
            quant=quant,
            attention=attention,
        ),
        attrs={"tensor_kind": "key"},
        source_ref=(
            [f"onnx::/model/layers.{layer_id}/self_attn/Slice_1"]
            if layer_id is not None
            else ["onnx::/model/self_attn/Slice_1"]
        ),
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=(
                [f"onnx::/model/layers.{layer_id}/self_attn/Slice_1"]
                if layer_id is not None
                else ["onnx::/model/self_attn/Slice_1"]
            ),
        ),
    )


def _make_embedding_lookup_node(node_id: str, output_shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="EMBEDDING_LOOKUP",
        inputs=["model.embed_tokens.weight", "input_ids"],
        outputs=["tokens.embed"],
        shape=output_shape,
        layout="SD",
        memory_class="weight",
        legal_opcodes=["EMBEDDING_LOOKUP"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="SD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "model.embed_tokens.weight": "WEIGHT",
                "input_ids": "METADATA",
            },
            output_memory_classes={"tokens.embed": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "EmbeddingLookup",
            "embedding_dim": output_shape[-1],
            "vocab_size": 262144,
        },
        source_ref=["onnx::Gather_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Gather_0"],
        ),
    )


def _make_layout_fallback_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="LAYOUT_FALLBACK",
        inputs=["logits_fp16"],
        outputs=["logits"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["LAYOUT_FALLBACK"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"logits_fp16": "ACTIVATION"},
            output_memory_classes={"logits": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "LayoutFallback",
            "original_op_kind": "Cast",
        },
        source_ref=["onnx::Cast_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Cast_0"],
        ),
    )


def _make_attention_mask_prep_node(node_id: str, shape: list[int]) -> object:
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
        inputs=["attn.mask.raw"],
        outputs=["attn.mask.ready"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["ATTENTION_MASK_PREP"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"attn.mask.raw": "ACTIVATION"},
            output_memory_classes={"attn.mask.ready": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "AttentionMaskPrep",
            "original_op_kind": "Add",
        },
        source_ref=["onnx::Add_mask_ready"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Add_mask_ready"],
        ),
    )


def _make_geglu_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="GEGLU",
        inputs=["gate", "up"],
        outputs=["mlp.out"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["GEGLU"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"gate": "ACTIVATION", "up": "ACTIVATION"},
            output_memory_classes={"mlp.out": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={"canonical_pattern": "GeGLU"},
        source_ref=["onnx::Mul_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Mul_0"],
        ),
    )


def _make_rope_table_node(node_id: str, shape: list[int], head_dim: int) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="ROPE_TABLE",
        inputs=["position_ids", "rope.inv_freq"],
        outputs=["rope.cos", "rope.sin"],
        shape=shape,
        layout="HSD",
        memory_class="metadata",
        legal_opcodes=["ROPE_TABLE"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="METADATA",
            input_memory_classes={"position_ids": "METADATA", "rope.inv_freq": "WEIGHT"},
            output_memory_classes={"rope.cos": "METADATA", "rope.sin": "METADATA"},
            quant=quant,
            attention=None,
        ),
        attrs={"canonical_pattern": "ROPETable", "head_dim": head_dim},
        source_ref=["onnx::Cos_0", "onnx::Sin_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Cos_0", "onnx::Sin_0"],
        ),
    )


def _make_rope_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import AttentionBinding, NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="ROPE",
        inputs=["q.norm", "rope.cos", "rope.sin"],
        outputs=["q.rot"],
        shape=shape,
        layout="BHSD",
        memory_class="activation",
        legal_opcodes=["ROPE"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="BHSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "q.norm": "ACTIVATION",
                "rope.cos": "METADATA",
                "rope.sin": "METADATA",
            },
            output_memory_classes={"q.rot": "ACTIVATION"},
            quant=quant,
            attention=AttentionBinding(
                mode="prefill",
                query_len=128,
                kv_len=128,
                head_dim=256,
                num_heads=4,
                num_key_value_heads=1,
                tensor_layout="BHSD",
                kv_layout_rule="per-layer-slice-of-LBHSD",
            ),
        ),
        attrs={"canonical_pattern": "RoPE"},
        source_ref=["onnx::Add_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Add_0"],
        ),
    )


def _make_sdpa_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import AttentionBinding, NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="SDPA",
        inputs=["q", "k", "v", "mask"],
        outputs=["attn.out"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["SDPA"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "q": "ACTIVATION",
                "k": "ACTIVATION",
                "v": "ACTIVATION",
                "mask": "ACTIVATION",
            },
            output_memory_classes={"attn.out": "ACTIVATION"},
            quant=quant,
            attention=AttentionBinding(
                mode="prefill",
                query_len=128,
                kv_len=128,
                head_dim=256,
                num_heads=4,
                num_key_value_heads=1,
                tensor_layout="BHSD",
                kv_layout_rule="per-layer-slice-of-LBHSD",
            ),
        ),
        attrs={
            "canonical_pattern": "SDPA",
            "query_len": 128,
            "kv_len": 128,
            "num_heads": 4,
            "head_dim": 256,
        },
        source_ref=["onnx::MatMul_qk", "onnx::Softmax_0", "onnx::MatMul_sv"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::MatMul_qk", "onnx::Softmax_0", "onnx::MatMul_sv"],
        ),
    )


def _make_rmsnorm_gemm_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="float16",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="RMSNORM_GEMM",
        inputs=["act", "norm_weight", "proj_weight"],
        outputs=["logits"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["RMSNORM_GEMM"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "act": "ACTIVATION",
                "norm_weight": "WEIGHT",
                "proj_weight": "WEIGHT",
            },
            output_memory_classes={"logits": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={"canonical_pattern": "MatMul", "weight_transposed": True},
        source_ref=["onnx::Mul_norm", "onnx::MatMul_logits"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Mul_norm", "onnx::MatMul_logits"],
        ),
    )


def _make_rmsnorm_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="RMSNORM",
        inputs=["x", "w"],
        outputs=["y"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["RMSNORM"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"x": "ACTIVATION", "w": "ACTIVATION"},
            output_memory_classes={"y": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={"canonical_pattern": "RMSNorm"},
        source_ref=["onnx::Mul_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Mul_0"],
        ),
    )


def _make_elem_add_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="ELEM_ADD",
        inputs=["lhs", "rhs"],
        outputs=["out"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["ELEM_ADD"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"lhs": "ACTIVATION", "rhs": "ACTIVATION"},
            output_memory_classes={"out": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={"canonical_pattern": "ResidualAdd"},
        source_ref=["onnx::Add_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Add_0"],
        ),
    )


def _make_kvstore_node(node_id: str, mode: str, query_len: int) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import AttentionBinding, NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="KVSTORE",
        inputs=["past_value", "value_tile"],
        outputs=["present_value"],
        shape=[1, 1, 2049, 256],
        layout="BHSD",
        memory_class="kv_cache",
        legal_opcodes=["KVSTORE"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=[1, 1, 2049, 256],
            canonical_layout="BHSD",
            memory_class="KV_CACHE",
            input_memory_classes={"past_value": "KV_CACHE", "value_tile": "ACTIVATION"},
            output_memory_classes={"present_value": "KV_CACHE"},
            quant=quant,
            attention=AttentionBinding(
                mode=mode,
                query_len=query_len,
                kv_len=2049,
                head_dim=256,
                num_heads=4,
                num_key_value_heads=1,
                tensor_layout="BHSD",
                kv_layout_rule="per-layer-slice-of-LBHSD",
            ),
        ),
        attrs={"canonical_pattern": "KVStore", "tensor_kind": "value"},
        source_ref=["onnx::Concat_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Concat_0"],
        ),
    )


def _make_shape_helper_node(node_id: str, shape: list[int]) -> object:
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
        inputs=["shape.meta"],
        outputs=["shape.ready"],
        shape=shape,
        layout="HSD",
        memory_class="metadata",
        legal_opcodes=["SHAPE_HELPER"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="METADATA",
            input_memory_classes={"shape.meta": "METADATA"},
            output_memory_classes={"shape.ready": "METADATA"},
            quant=quant,
            attention=None,
        ),
        attrs={"canonical_pattern": "ShapeHelper"},
        source_ref=["onnx::Shape_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Shape_0"],
        ),
    )
