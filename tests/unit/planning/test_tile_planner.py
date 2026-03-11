from pathlib import Path


def test_plan_tiling_prefill_emits_descending_m_tile_candidates_for_quant_gemm() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [_make_wdq_gemm_node(node_id="nig.node.linear", output_shape=[1, 128, 1024], group_size=128)]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)

    artifact = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    linear_candidates = [candidate for candidate in artifact.candidates if candidate.node_id == "nig.node.linear"]
    assert [candidate.m_tile for candidate in linear_candidates] == [48, 32, 24, 16]
    assert [candidate.rank for candidate in linear_candidates] == [1, 2, 3, 4]
    assert linear_candidates[0].ranking_reason.startswith("prefill-throughput-first")
    assert all(candidate.quant_alignment_ok for candidate in linear_candidates)
    assert all(candidate.resource_summary is not None for candidate in linear_candidates)
    assert all(candidate.resource_summary.storage_binding_ids for candidate in linear_candidates)
    assert linear_candidates[0].resource_summary.storage_read_bytes_by_source_kind["weight_tensor"] == 8 * 1024
    assert linear_candidates[0].resource_summary.storage_read_bytes_by_source_kind["quant_tensor"] == 4
    assert linear_candidates[-1].resource_summary.storage_read_bytes_by_source_kind["weight_tensor"] == 8 * 1024
    assert linear_candidates[-1].resource_summary.storage_read_bytes_by_source_kind["quant_tensor"] == 4


def test_plan_tiling_decode_defaults_to_m_tile_1_for_sdpa_decode() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")
    bound_nig = _make_bound_nig_ir([_make_sdpa_decode_node(node_id="nig.node.attn.decode", shape=[1, 1, 1024])])
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)

    artifact = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    decode_candidates = [candidate for candidate in artifact.candidates if candidate.node_id == "nig.node.attn.decode"]
    assert len(decode_candidates) == 1
    assert decode_candidates[0].m_tile == 1
    assert decode_candidates[0].rank == 1
    assert decode_candidates[0].strategy == "decode-latency-first"
    assert decode_candidates[0].ranking_reason.startswith("decode-latency-first")


def _make_bound_nig_ir(nodes: list[object]) -> object:
    from llm_sched.ir.nig import NIGIR

    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="spec-09-fixture",
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


def _make_sdpa_decode_node(node_id: str, shape: list[int]) -> object:
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
        macro_op="SDPA_DECODE",
        inputs=["q", "k_cache", "v_cache", "mask"],
        outputs=["attn.out"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["SDPA_DECODE"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "q": "ACTIVATION",
                "k_cache": "KV_CACHE",
                "v_cache": "KV_CACHE",
                "mask": "ACTIVATION",
            },
            output_memory_classes={"attn.out": "ACTIVATION"},
            quant=quant,
            attention=AttentionBinding(
                mode="decode",
                query_len=1,
                kv_len=2049,
                head_dim=256,
                num_heads=4,
                num_key_value_heads=1,
                tensor_layout="BHSD",
                kv_layout_rule="per-layer-slice-of-LBHSD",
            ),
        ),
        attrs={
            "canonical_pattern": "SDPA",
            "query_len": 1,
            "kv_len": 2049,
            "num_heads": 4,
            "head_dim": 256,
        },
        source_ref=["onnx::MatMul_qk", "onnx::Softmax_0", "onnx::MatMul_sv"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::MatMul_qk", "onnx::Softmax_0", "onnx::MatMul_sv"],
        ),
    )
