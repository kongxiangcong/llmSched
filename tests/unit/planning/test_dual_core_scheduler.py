from math import ceil
from pathlib import Path


def test_plan_dual_core_schedule_inserts_transfer_for_cross_core_handoff() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
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

    compute_blocks = [block for block in schedule.blocks if block.stage == "compute"]
    transfer_blocks = [block for block in schedule.blocks if block.stage == "transfer"]

    assert schedule.core_mode == "dual-core"
    assert [block.core_id for block in compute_blocks] == [0, 1]
    assert len(transfer_blocks) == 1
    assert transfer_blocks[0].peer_core_id == 1
    assert transfer_blocks[0].resource_set == ["Core Link"]
    assert transfer_blocks[0].barrier_in
    assert transfer_blocks[0].barrier_out


def test_plan_dual_core_schedule_falls_back_to_dma_when_core_link_is_disabled() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    target = target.model_copy(update={"core_link": {"enabled": False, "bandwidth_gbps": 0}}, deep=True)
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

    transfer_block = next(block for block in schedule.blocks if block.stage == "transfer")
    assert transfer_block.resource_set == ["DMA"]
    assert transfer_block.transfer_kind == "dma"


def test_plan_dual_core_schedule_prefers_candidate_rank_over_m_tile() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TileCandidate, TileCandidateResourceSummary, TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    node = _make_wdq_gemm_node(node_id="nig.node.linear.rank", output_shape=[1, 128, 1024], group_size=128)
    bound_nig = _make_bound_nig_ir([node])
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[
            TileCandidate(
                candidate_id=f"{node.node_id}.m24.n256.k128",
                node_id=node.node_id,
                macro_op=node.macro_op,
                strategy="prefill-throughput-first",
                m_tile=24,
                n_tile=256,
                k_tile=128,
                read_bytes=1024,
                write_bytes=512,
                total_vmem_bytes=2048,
                rank=1,
                ranking_reason="fixture-best",
                quant_alignment_ok=True,
                quant_alignment_message="fixture",
                source_memory_plan_region_pressure={"ping": 1024},
                resource_summary=TileCandidateResourceSummary(
                    read_bytes=1024,
                    write_bytes=512,
                    total_vmem_bytes=2048,
                    dma_bytes=1536,
                    region_pressure_bytes={"ping": 1024},
                    storage_binding_ids=[],
                    storage_read_bytes_by_source_kind={},
                    storage_read_bytes_by_backing_store={},
                ),
                issues=[],
            ),
            TileCandidate(
                candidate_id=f"{node.node_id}.m48.n256.k128",
                node_id=node.node_id,
                macro_op=node.macro_op,
                strategy="prefill-throughput-first",
                m_tile=48,
                n_tile=256,
                k_tile=128,
                read_bytes=2048,
                write_bytes=1024,
                total_vmem_bytes=4096,
                rank=2,
                ranking_reason="fixture-second",
                quant_alignment_ok=True,
                quant_alignment_message="fixture",
                source_memory_plan_region_pressure={"ping": 2048},
                resource_summary=TileCandidateResourceSummary(
                    read_bytes=2048,
                    write_bytes=1024,
                    total_vmem_bytes=4096,
                    dma_bytes=3072,
                    region_pressure_bytes={"ping": 2048},
                    storage_binding_ids=[],
                    storage_read_bytes_by_source_kind={},
                    storage_read_bytes_by_backing_store={},
                ),
                issues=[],
            ),
        ],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    compute_block = next(block for block in schedule.blocks if block.stage == "compute")
    assert compute_block.tiling_candidate_id.endswith(".m24.n256.k128")


def test_plan_dual_core_schedule_keeps_sdpa_decode_on_dma_and_vpu() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")
    bound_nig = _make_bound_nig_ir([_make_sdpa_decode_node(node_id="nig.node.attn.decode", shape=[1, 1, 1024])])
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    compute_block = next(block for block in schedule.blocks if block.stage == "compute")
    assert compute_block.macro_op == "SDPA_DECODE"
    assert compute_block.resource_set == ["DMA", "VPU"]


def test_plan_dual_core_schedule_allows_vpu_helper_during_sdpa_decode_dma_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_sdpa_decode_node("nig.node.attn.decode", [1, 1, 1024]),
            _make_passthrough_node(
                "nig.node.rope_table",
                "ROPE_TABLE",
                [1, 1, 16],
                input_name="meta",
                output_name="meta_out",
            ),
            _make_passthrough_node(
                "nig.node.helper",
                "SHAPE_HELPER",
                [1, 16, 256],
                input_name="meta_out",
                output_name="meta_done",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    decode_compute = blocks["sched.nig.node.attn.decode.compute.core0"]
    transfer_block = blocks["sched.transfer.nig.node.rope_table.to.nig.node.helper"]
    helper_prepare = blocks["sched.nig.node.helper.prepare.core0"]
    decode_node = next(node for node in bound_nig.nodes if node.node_id == "nig.node.attn.decode")
    decode_candidate = next(
        candidate
        for candidate in tiling_plan.candidates
        if candidate.candidate_id == decode_compute.tiling_candidate_id
    )
    vpu_reservation = next(
        reservation
        for reservation in estimate_stage_resource_reservations(
            macro_op="SDPA_DECODE",
            stage="compute",
            resource_set=decode_compute.resource_set,
            duration_slots=decode_compute.duration_slots,
            node=decode_node,
            candidate=decode_candidate,
            capabilities=capabilities,
        )
        if reservation[0] == "VPU"
    )
    vpu_release = decode_compute.issue_slot + vpu_reservation[1] + vpu_reservation[2]

    assert decode_compute.resource_set == ["DMA", "VPU"]
    assert vpu_reservation[2] < decode_compute.duration_slots
    assert transfer_block.issue_slot + transfer_block.duration_slots <= vpu_release
    assert helper_prepare.issue_slot == vpu_release
    assert helper_prepare.issue_slot < decode_compute.issue_slot + decode_compute.duration_slots


def test_plan_dual_core_schedule_covers_untiled_macros_with_transfer() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_passthrough_node(
                "nig.node.norm",
                "RMSNORM",
                [1, 128, 1024],
                input_name="act0",
                output_name="mid0",
            ),
            _make_passthrough_node(
                "nig.node.add",
                "ELEM_ADD",
                [1, 128, 1024],
                input_name="mid0",
                output_name="out1",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    norm_compute = next(block for block in schedule.blocks if block.node_id == "nig.node.norm" and block.stage == "compute")
    add_compute = next(block for block in schedule.blocks if block.node_id == "nig.node.add" and block.stage == "compute")
    transfer_block = next(block for block in schedule.blocks if block.stage == "transfer")

    assert norm_compute.core_id == 0
    assert add_compute.core_id == 1
    assert transfer_block.resource_set == ["Core Link"]
    assert transfer_block.peer_core_id == 1
    assert transfer_block.transfer_bytes > 0
    assert norm_compute.tiling_candidate_id is None
    assert add_compute.tiling_candidate_id is None


def test_plan_dual_core_schedule_emits_transfer_dependencies_and_overlap_slots() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
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
                output_name="mid1",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.linear.2",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="mid1",
                output_name="out2",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}

    transfer_01 = blocks["sched.transfer.nig.node.linear.0.to.nig.node.linear.1"]
    transfer_12 = blocks["sched.transfer.nig.node.linear.1.to.nig.node.linear.2"]

    assert transfer_01.depends_on == ["sched.nig.node.linear.0.store.core0"]
    assert transfer_01.duration_slots > 1
    assert transfer_12.depends_on == ["sched.nig.node.linear.1.store.core1"]
    assert transfer_12.duration_slots > 1

    assert blocks["sched.nig.node.linear.1.compute.core1"].depends_on == [
        "sched.nig.node.linear.1.dma_in.core1",
        "sched.transfer.nig.node.linear.0.to.nig.node.linear.1",
    ]
    assert blocks["sched.nig.node.linear.2.compute.core0"].depends_on == [
        "sched.nig.node.linear.2.dma_in.core0",
        "sched.transfer.nig.node.linear.1.to.nig.node.linear.2",
    ]
    assert blocks["sched.nig.node.linear.1.compute.core1"].issue_slot >= (
        transfer_01.issue_slot + transfer_01.duration_slots
    )
    assert blocks["sched.nig.node.linear.2.compute.core0"].issue_slot >= (
        transfer_12.issue_slot + transfer_12.duration_slots
    )


def test_plan_dual_core_schedule_models_shared_dma_contention_for_dma_transfer() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    target = target.model_copy(update={"core_link": {"enabled": False, "bandwidth_gbps": 0}}, deep=True)
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
                output_name="mid1",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.linear.2",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="mid1",
                output_name="out2",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    transfer_01 = blocks["sched.transfer.nig.node.linear.0.to.nig.node.linear.1"]
    transfer_12 = blocks["sched.transfer.nig.node.linear.1.to.nig.node.linear.2"]
    node2_dma_in = blocks["sched.nig.node.linear.2.dma_in.core0"]

    assert transfer_01.resource_set == ["DMA"]
    assert transfer_01.transfer_kind == "dma"
    assert transfer_01.depends_on == ["sched.nig.node.linear.0.store.core0"]
    assert transfer_01.duration_slots > 1
    assert transfer_12.issue_slot >= (
        node2_dma_in.issue_slot + node2_dma_in.duration_slots
    )


def test_plan_dual_core_schedule_allows_transport_overlap_with_prior_sync_tail() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node(
                node_id="nig.node.producer.0",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="act0",
                output_name="mid0",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.producer.1",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="act1",
                output_name="mid1",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.consumer.0",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="mid1",
                output_name="out0",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.consumer.1",
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

    transfer_blocks = sorted(
        (block for block in schedule.blocks if block.stage == "transfer"),
        key=lambda block: block.issue_slot,
    )

    assert len(transfer_blocks) == 2
    first_transfer, second_transfer = transfer_blocks
    assert first_transfer.resource_set == ["Core Link"]
    assert second_transfer.resource_set == ["Core Link"]
    assert first_transfer.sync_cost_cycles > 0
    assert second_transfer.issue_slot >= (
        first_transfer.issue_slot
        + (first_transfer.duration_slots - first_transfer.sync_cost_cycles)
    )
    assert second_transfer.issue_slot < (
        first_transfer.issue_slot + first_transfer.duration_slots
    )


def test_plan_dual_core_schedule_allows_core_local_mxu_reuse_during_sdpa_vpu_tail() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_sdpa_node("nig.node.attn.prefill.0", [1, 128, 1024]),
            _make_passthrough_node("nig.node.helper", "SHAPE_HELPER", [1, 1, 16], input_name="meta", output_name="meta_out"),
            _make_wdq_gemm_node(
                node_id="nig.node.linear.tail",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="act_tail",
                output_name="out_tail",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    sdpa_compute = blocks["sched.nig.node.attn.prefill.0.compute.core0"]
    wdq_compute = blocks["sched.nig.node.linear.tail.compute.core0"]

    assert sdpa_compute.resource_set == ["MXU", "VPU"]
    assert wdq_compute.resource_set == ["WDQ", "MXU"]
    assert wdq_compute.issue_slot >= sdpa_compute.issue_slot + 1
    assert wdq_compute.issue_slot < sdpa_compute.issue_slot + sdpa_compute.duration_slots


def test_plan_dual_core_schedule_specializes_geglu_compute_resources() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_passthrough_node(
                "nig.node.geglu",
                "GEGLU",
                [1, 128, 1024],
                input_name="act_geglu",
                output_name="geglu_out",
            ),
            _make_passthrough_node("nig.node.helper", "SHAPE_HELPER", [1, 1, 16], input_name="meta", output_name="meta_out"),
            _make_wdq_gemm_node(
                node_id="nig.node.linear.tail",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="act_tail",
                output_name="out_tail",
            ),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    geglu_compute = blocks["sched.nig.node.geglu.compute.core0"]
    wdq_compute = blocks["sched.nig.node.linear.tail.compute.core0"]

    assert geglu_compute.resource_set == ["MXU", "VPU"]
    assert geglu_compute.duration_slots > 1
    assert wdq_compute.resource_set == ["WDQ", "MXU"]


def test_plan_dual_core_schedule_allows_vpu_issue_after_geglu_prefix() -> None:
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    reservations = estimate_stage_resource_reservations(
        macro_op="GEGLU",
        stage="compute",
        resource_set=["MXU", "VPU"],
        duration_slots=64,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("VPU", 0, 1)],
    )

    assert follower_issue == 8


def test_plan_dual_core_schedule_keeps_vpu_helper_after_sdpa_vpu_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_sdpa_node("nig.node.attn.prefill.0", [1, 128, 1024]),
            _make_passthrough_node("nig.node.filler", "SHAPE_HELPER", [1, 1, 16], input_name="meta", output_name="meta_out"),
            _make_passthrough_node("nig.node.helper", "SHAPE_HELPER", [1, 16, 256]),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    sdpa_compute = blocks["sched.nig.node.attn.prefill.0.compute.core0"]
    helper_prepare = blocks["sched.nig.node.helper.prepare.core0"]
    helper_compute = blocks["sched.nig.node.helper.compute.core0"]
    sdpa_node = next(node for node in bound_nig.nodes if node.node_id == "nig.node.attn.prefill.0")
    sdpa_candidate = next(
        candidate
        for candidate in tiling_plan.candidates
        if candidate.candidate_id == sdpa_compute.tiling_candidate_id
    )
    vpu_reservations = [
        reservation
        for reservation in estimate_stage_resource_reservations(
            macro_op="SDPA",
            stage="compute",
            resource_set=sdpa_compute.resource_set,
            duration_slots=sdpa_compute.duration_slots,
            node=sdpa_node,
            candidate=sdpa_candidate,
            capabilities=capabilities,
        )
        if reservation[0] == "VPU"
    ]
    _resource_name, vpu_tail_start, vpu_tail_duration = vpu_reservations[-1]
    vpu_tail_end = sdpa_compute.issue_slot + vpu_tail_start + vpu_tail_duration

    assert helper_compute.issue_slot >= helper_prepare.issue_slot + helper_prepare.duration_slots
    assert helper_prepare.issue_slot + helper_prepare.duration_slots <= (
        sdpa_compute.issue_slot + vpu_tail_start
    )
    assert helper_compute.issue_slot >= vpu_tail_end


def test_plan_dual_core_schedule_allows_vpu_issue_after_sdpa_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_duration_slots, estimate_stage_resource_reservations
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    sdpa_node = _make_sdpa_node("nig.node.attn.prefill.0", [1, 128, 1024])
    candidate = _make_tile_candidate("fixture.sdpa.compute", "nig.node.attn.prefill.0", "SDPA", 48, 128, 128)
    duration_slots = estimate_stage_duration_slots(
        node=sdpa_node,
        stage="compute",
        candidate=candidate,
        allocations=[],
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="SDPA",
        stage="compute",
        resource_set=["MXU", "VPU"],
        duration_slots=duration_slots,
        node=sdpa_node,
        candidate=candidate,
        capabilities=capabilities,
    )
    attention = sdpa_node.binding.attention
    assert attention is not None
    expected_overhead_slots = ceil((attention.query_len * attention.kv_len * attention.num_heads) / capabilities.vpu.lanes)
    expected_prefix_slots = max(1, ceil(expected_overhead_slots / 2))
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("VPU", 0, 1)],
    )

    assert follower_issue == expected_prefix_slots


def test_plan_dual_core_schedule_allows_gemm_before_wdq_mxu_prefix_ends() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node("nig.node.wdq", [1, 128, 1024], 128, input_name="act_wdq", output_name="out_wdq"),
            _make_passthrough_node("nig.node.filler", "SHAPE_HELPER", [1, 1, 16], input_name="meta", output_name="meta_out"),
            _make_gemm_node("nig.node.gemm", [1, 8, 128], input_name="act_gemm", output_name="out_gemm"),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[
            _make_tile_candidate("nig.node.wdq.m128.n128.k128", "nig.node.wdq", "WDQ_GEMM", 128, 128, 128),
            _make_tile_candidate("nig.node.gemm.m8.n32.k32", "nig.node.gemm", "GEMM", 8, 32, 32),
        ],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    wdq_compute = blocks["sched.nig.node.wdq.compute.core0"]
    gemm_dma_in = blocks["sched.nig.node.gemm.dma_in.core0"]
    gemm_compute = blocks["sched.nig.node.gemm.compute.core0"]
    mxu_start_offset = next(
        start_offset
        for resource_name, start_offset, _duration in estimate_stage_resource_reservations(
            macro_op="WDQ_GEMM",
            stage="compute",
            resource_set=wdq_compute.resource_set,
            duration_slots=wdq_compute.duration_slots,
        )
        if resource_name == "MXU"
    )

    assert gemm_compute.issue_slot >= gemm_dma_in.issue_slot + gemm_dma_in.duration_slots
    assert gemm_compute.issue_slot + gemm_compute.duration_slots <= (
        wdq_compute.issue_slot + mxu_start_offset
    )


def test_plan_dual_core_schedule_starts_vpu_helper_at_rmsnorm_gemm_prefix_end() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_rmsnorm_gemm_node("nig.node.rg", [1, 128, 1024], input_name="act_rg", output_name="out_rg"),
            _make_passthrough_node("nig.node.filler", "SHAPE_HELPER", [1, 1, 16], input_name="meta", output_name="meta_out"),
            _make_passthrough_node("nig.node.helper", "SHAPE_HELPER", [1, 16, 256]),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    candidate = _make_tile_candidate("nig.node.rg.m48.n128.k128", "nig.node.rg", "RMSNORM_GEMM", 48, 128, 128)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[candidate],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    rg_compute = blocks["sched.nig.node.rg.compute.core0"]
    helper_prepare = blocks["sched.nig.node.helper.prepare.core0"]
    helper_compute = blocks["sched.nig.node.helper.compute.core0"]
    expected_prefix_slots = ceil((candidate.m_tile * candidate.n_tile) / capabilities.vpu.lanes)

    assert helper_prepare.issue_slot + helper_prepare.duration_slots <= rg_compute.issue_slot + expected_prefix_slots
    assert helper_compute.issue_slot >= helper_prepare.issue_slot + helper_prepare.duration_slots
    assert helper_compute.issue_slot == rg_compute.issue_slot + expected_prefix_slots
    assert helper_compute.issue_slot + helper_compute.duration_slots <= (
        rg_compute.issue_slot + rg_compute.duration_slots
    )


def test_plan_dual_core_schedule_allows_dma_overlap_during_wdq_dma_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_wdq_gemm_node("nig.node.wdq", [1, 128, 1024], 128, input_name="act_wdq", output_name="out_wdq"),
            _make_passthrough_node("nig.node.kvload", "KVLOAD", [1, 128, 1024], memory_class="kv"),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target, scenario)

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    wdq_dma = blocks["sched.nig.node.wdq.dma_in.core0"]
    kvload_dma = blocks["sched.nig.node.kvload.dma_in.core1"]
    wdq_node = next(node for node in bound_nig.nodes if node.node_id == "nig.node.wdq")
    wdq_candidate = next(candidate for candidate in tiling_plan.candidates if candidate.node_id == "nig.node.wdq")
    dma_window = next(
        reservation
        for reservation in estimate_stage_resource_reservations(
            macro_op="WDQ_GEMM",
            stage="dma_in",
            resource_set=["DMA"],
            duration_slots=wdq_dma.duration_slots,
            node=wdq_node,
            candidate=wdq_candidate,
            capabilities=capabilities,
        )
        if reservation[0] == "DMA"
    )

    assert kvload_dma.issue_slot == wdq_dma.issue_slot + dma_window[2]
    assert kvload_dma.issue_slot < wdq_dma.issue_slot + wdq_dma.duration_slots


def test_plan_dual_core_schedule_allows_dma_before_kvstore_dma_window() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_passthrough_node("nig.node.kvstore", "KVSTORE", [1, 128, 1024], memory_class="kv"),
            _make_passthrough_node("nig.node.rope_table", "ROPE_TABLE", [1, 1, 16]),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    kvstore_store = blocks["sched.nig.node.kvstore.store.core0"]
    rope_table_dma = blocks["sched.nig.node.rope_table.dma_in.core1"]
    kvstore_node = next(node for node in bound_nig.nodes if node.node_id == "nig.node.kvstore")
    dma_window = next(
        reservation
        for reservation in estimate_stage_resource_reservations(
            macro_op="KVSTORE",
            stage="store",
            resource_set=["DMA"],
            duration_slots=kvstore_store.duration_slots,
            node=kvstore_node,
            candidate=None,
            capabilities=capabilities,
        )
        if reservation[0] == "DMA"
    )

    assert rope_table_dma.issue_slot == 0
    assert rope_table_dma.issue_slot < kvstore_store.issue_slot + dma_window[1]


def test_plan_dual_core_schedule_allows_dma_at_rmsnorm_store_issue_with_vpu_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    rmsnorm_node = _make_passthrough_node("nig.node.rmsnorm", "RMSNORM", [1, 128, 1024])
    reservations = estimate_stage_resource_reservations(
        macro_op="RMSNORM",
        stage="store",
        resource_set=["DMA"],
        duration_slots=4,
        node=rmsnorm_node,
        candidate=None,
        capabilities=capabilities,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("DMA", 0, 1)],
    )

    assert follower_issue == 0


def test_plan_dual_core_schedule_allows_dma_at_layout_store_issue_with_vpu_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    layout_node = _make_layout_fallback_node("nig.node.layout", [1, 1152, 1])
    reservations = estimate_stage_resource_reservations(
        macro_op="LAYOUT_FALLBACK",
        stage="store",
        resource_set=["DMA"],
        duration_slots=4,
        node=layout_node,
        candidate=None,
        capabilities=capabilities,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("DMA", 0, 1)],
    )

    assert follower_issue == 0


def test_plan_dual_core_schedule_allows_dma_at_attention_mask_store_issue_with_vpu_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    mask_node = _make_attention_mask_prep_node("nig.node.mask", [1, 1, 128, 128], "Trilu")
    reservations = estimate_stage_resource_reservations(
        macro_op="ATTENTION_MASK_PREP",
        stage="store",
        resource_set=["DMA"],
        duration_slots=4,
        node=mask_node,
        candidate=None,
        capabilities=capabilities,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("DMA", 0, 1)],
    )

    assert follower_issue == 0


def test_plan_dual_core_schedule_allows_dma_at_rope_store_issue_with_vpu_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    rope_node = _make_passthrough_node("nig.node.rope", "ROPE", [1, 128, 1024])
    reservations = estimate_stage_resource_reservations(
        macro_op="ROPE",
        stage="store",
        resource_set=["DMA"],
        duration_slots=4,
        node=rope_node,
        candidate=None,
        capabilities=capabilities,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("DMA", 0, 1)],
    )

    assert follower_issue == 0


def test_plan_dual_core_schedule_allows_dma_at_embedding_store_issue_with_vpu_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    embedding_node = _make_embedding_lookup_node("nig.node.embedding", [1, 16, 1024])
    reservations = estimate_stage_resource_reservations(
        macro_op="EMBEDDING_LOOKUP",
        stage="store",
        resource_set=["DMA"],
        duration_slots=4,
        node=embedding_node,
        candidate=None,
        capabilities=capabilities,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("DMA", 0, 1)],
    )

    assert follower_issue == 0


def test_plan_dual_core_schedule_allows_dma_at_sdpa_store_issue_with_vpu_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    sdpa_node = _make_sdpa_decode_node("nig.node.attn.decode", [1, 1, 1024])
    candidate = _make_tile_candidate("fixture.sdpa.decode.store", "nig.node.attn.decode", "SDPA_DECODE", 1, 128, 128)
    reservations = estimate_stage_resource_reservations(
        macro_op="SDPA_DECODE",
        stage="store",
        resource_set=["DMA"],
        duration_slots=3,
        node=sdpa_node,
        candidate=candidate,
        capabilities=capabilities,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("DMA", 0, 1)],
    )

    assert follower_issue == 0


def test_plan_dual_core_schedule_allows_dma_at_geglu_store_issue_with_vpu_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations
    from llm_sched.planning.schedule_reservations import (
        build_reservation_timeline,
        find_earliest_issue_slot,
        reserve_resource_windows,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    geglu_node = _make_passthrough_node("nig.node.geglu", "GEGLU", [1, 128, 1024])
    reservations = estimate_stage_resource_reservations(
        macro_op="GEGLU",
        stage="store",
        resource_set=["DMA"],
        duration_slots=4,
        node=geglu_node,
        candidate=None,
        capabilities=capabilities,
    )
    reservations_by_resource = build_reservation_timeline()
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=0,
        requested_reservations=reservations,
    )

    follower_issue = find_earliest_issue_slot(
        ready_slot=0,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=[("DMA", 0, 1)],
    )

    assert follower_issue == 0


def test_plan_dual_core_schedule_allows_dma_during_kvload_vpu_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_passthrough_node("nig.node.kvload.0", "KVLOAD", [1, 128, 1024], memory_class="kv"),
            _make_passthrough_node("nig.node.rope_table", "ROPE_TABLE", [1, 128, 1024]),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    kvload_0 = blocks["sched.nig.node.kvload.0.dma_in.core0"]
    rope_table_dma = blocks["sched.nig.node.rope_table.dma_in.core1"]
    kvload_node = next(node for node in bound_nig.nodes if node.node_id == "nig.node.kvload.0")
    dma_window = next(
        reservation
        for reservation in estimate_stage_resource_reservations(
            macro_op="KVLOAD",
            stage="dma_in",
            resource_set=["DMA"],
            duration_slots=kvload_0.duration_slots,
            node=kvload_node,
            candidate=None,
            capabilities=capabilities,
        )
        if reservation[0] == "DMA"
    )

    assert kvload_0.resource_set == ["DMA"]
    assert rope_table_dma.resource_set == ["DMA"]
    assert rope_table_dma.issue_slot == kvload_0.issue_slot + dma_window[2]
    assert rope_table_dma.issue_slot < kvload_0.issue_slot + kvload_0.duration_slots


def test_plan_dual_core_schedule_allows_dma_during_embedding_lookup_vpu_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_embedding_lookup_node("nig.node.embedding", [1, 16, 1024]),
            _make_passthrough_node("nig.node.rope_table", "ROPE_TABLE", [1, 1, 16]),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    embedding_dma = blocks["sched.nig.node.embedding.dma_in.core0"]
    rope_table_dma = blocks["sched.nig.node.rope_table.dma_in.core1"]
    embedding_node = next(node for node in bound_nig.nodes if node.node_id == "nig.node.embedding")
    dma_window = next(
        reservation
        for reservation in estimate_stage_resource_reservations(
            macro_op="EMBEDDING_LOOKUP",
            stage="dma_in",
            resource_set=["DMA"],
            duration_slots=embedding_dma.duration_slots,
            node=embedding_node,
            candidate=None,
            capabilities=capabilities,
        )
        if reservation[0] == "DMA"
    )

    assert embedding_dma.resource_set == ["DMA"]
    assert rope_table_dma.resource_set == ["DMA"]
    assert rope_table_dma.issue_slot == embedding_dma.issue_slot + dma_window[2]
    assert rope_table_dma.issue_slot < embedding_dma.issue_slot + embedding_dma.duration_slots


def test_plan_dual_core_schedule_allows_dma_during_rope_table_vpu_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    bound_nig = _make_bound_nig_ir(
        [
            _make_rope_table_node("nig.node.rope.table", [1, 1, 256]),
            _make_passthrough_node("nig.node.elem.add", "ELEM_ADD", [1, 1, 256]),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    rope_table_dma = blocks["sched.nig.node.rope.table.dma_in.core0"]
    elem_add_dma = blocks["sched.nig.node.elem.add.dma_in.core1"]
    rope_table_node = next(node for node in bound_nig.nodes if node.node_id == "nig.node.rope.table")
    dma_window = next(
        reservation
        for reservation in estimate_stage_resource_reservations(
            macro_op="ROPE_TABLE",
            stage="dma_in",
            resource_set=["DMA"],
            duration_slots=rope_table_dma.duration_slots,
            node=rope_table_node,
            candidate=None,
            capabilities=capabilities,
        )
        if reservation[0] == "DMA"
    )

    assert rope_table_dma.resource_set == ["DMA"]
    assert elem_add_dma.resource_set == ["DMA"]
    assert elem_add_dma.issue_slot == rope_table_dma.issue_slot + dma_window[2]
    assert elem_add_dma.issue_slot < rope_table_dma.issue_slot + rope_table_dma.duration_slots


def test_plan_dual_core_schedule_delays_same_core_vpu_after_heavier_attention_mask_prep() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")

    def _build_schedule(original_op_kind: str) -> object:
        bound_nig = _make_bound_nig_ir(
            [
                _make_attention_mask_prep_node("nig.node.mask", [1, 1, 128, 128], original_op_kind),
                _make_passthrough_node("nig.node.filler", "SHAPE_HELPER", [1, 1, 16], input_name="meta", output_name="meta_out"),
                _make_passthrough_node("nig.node.elem.add", "ELEM_ADD", [1, 1, 16]),
            ]
        )
        memory_plan = plan_memory_artifact(bound_nig, target, scenario)
        tiling_plan = TilingPlanArtifact(
            graph_id=bound_nig.graph_id,
            scenario_name=scenario.scenario_name,
            core_mode="dual-core",
            candidates=[],
        )
        return plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    trilu_schedule = _build_schedule("Trilu")
    add_schedule = _build_schedule("Add")
    trilu_blocks = {block.block_id: block for block in trilu_schedule.blocks}
    add_blocks = {block.block_id: block for block in add_schedule.blocks}

    trilu_mask_compute = trilu_blocks["sched.nig.node.mask.compute.core0"]
    add_mask_compute = add_blocks["sched.nig.node.mask.compute.core0"]
    trilu_elem_compute = trilu_blocks["sched.nig.node.elem.add.compute.core0"]
    add_elem_compute = add_blocks["sched.nig.node.elem.add.compute.core0"]

    assert trilu_mask_compute.duration_slots > add_mask_compute.duration_slots
    assert trilu_elem_compute.issue_slot > add_elem_compute.issue_slot


def test_plan_dual_core_schedule_characterizes_layout_fallback_dma_overlap() -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.planning.dual_core_scheduler import plan_dual_core_schedule
    from llm_sched.planning.memory_planner import plan_memory_artifact

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json")
    scenario = load_scenario_profile(repo_root / "profiles" / "scenarios" / "prefill_seq128.json")
    bound_nig = _make_bound_nig_ir(
        [
            _make_layout_fallback_node("nig.node.layout", [1, 1152, 1]),
            _make_passthrough_node("nig.node.elem.add", "ELEM_ADD", [1, 1, 16]),
        ]
    )
    memory_plan = plan_memory_artifact(bound_nig, target, scenario)
    tiling_plan = TilingPlanArtifact(
        graph_id=bound_nig.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode="dual-core",
        candidates=[],
    )

    schedule = plan_dual_core_schedule(bound_nig, memory_plan, tiling_plan, target, scenario)

    blocks = {block.block_id: block for block in schedule.blocks}
    layout_dma = blocks["sched.nig.node.layout.dma_in.core0"]
    layout_prepare = blocks["sched.nig.node.layout.prepare.core0"]
    layout_compute = blocks["sched.nig.node.layout.compute.core0"]
    layout_store = blocks["sched.nig.node.layout.store.core0"]
    elem_dma = blocks["sched.nig.node.elem.add.dma_in.core1"]

    assert layout_dma.resource_set == ["DMA"]
    assert layout_prepare.resource_set == ["VPU"]
    assert layout_compute.resource_set == ["VPU"]
    assert layout_store.resource_set == ["DMA"]
    assert elem_dma.issue_slot == layout_dma.issue_slot + layout_dma.duration_slots
    assert elem_dma.issue_slot < layout_store.issue_slot


def _make_bound_nig_ir(nodes: list[object]) -> object:
    from llm_sched.ir.nig import NIGIR

    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="spec-11-fixture",
        binding_state="bound",
        nodes=nodes,
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


def _make_rope_table_node(node_id: str, output_shape: list[int]) -> object:
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
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["ROPE_TABLE"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "position_ids": "METADATA",
                "rope.inv_freq": "WEIGHT",
            },
            output_memory_classes={
                "rope.cos": "ACTIVATION",
                "rope.sin": "ACTIVATION",
            },
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "ROPETable",
            "head_dim": output_shape[-1],
        },
        source_ref=["onnx::Cos_0", "onnx::Sin_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Cos_0", "onnx::Sin_0"],
        ),
    )


def _make_attention_mask_prep_node(node_id: str, shape: list[int], original_op_kind: str) -> object:
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
            "original_op_kind": original_op_kind,
        },
        source_ref=[f"onnx::{original_op_kind}_mask_ready"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=[f"onnx::{original_op_kind}_mask_ready"],
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
        inputs=["tokens.embed"],
        outputs=["tokens.transposed"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["LAYOUT_FALLBACK"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"tokens.embed": "ACTIVATION"},
            output_memory_classes={"tokens.transposed": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "LayoutFallback",
            "original_op_kind": "Transpose",
        },
        source_ref=["onnx::Transpose_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Transpose_0"],
        ),
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
        source_ref=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
        ),
    )


def _make_gemm_node(
    node_id: str,
    output_shape: list[int],
    *,
    input_name: str = "act",
    output_name: str = "out",
) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="bf16",
        activation_dtype="bf16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=32,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="GEMM",
        inputs=[input_name, "weight"],
        outputs=[output_name],
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["GEMM"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                input_name: "ACTIVATION",
                "weight": "WEIGHT",
            },
            output_memory_classes={output_name: "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::/model/layers.0/mlp/gemm"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::/model/layers.0/mlp/gemm"],
        ),
    )


def _make_rmsnorm_gemm_node(
    node_id: str,
    output_shape: list[int],
    *,
    input_name: str = "act",
    output_name: str = "out",
) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="bf16",
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
        macro_op="RMSNORM_GEMM",
        inputs=[input_name, "weight"],
        outputs=[output_name],
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["RMSNORM_GEMM"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                input_name: "ACTIVATION",
                "weight": "WEIGHT",
            },
            output_memory_classes={output_name: "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::/model/layers.0/mlp/rmsnorm_gemm"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::/model/layers.0/mlp/rmsnorm_gemm"],
        ),
    )
    return NIGNode(
        node_id=node_id,
        macro_op="GEMM",
        inputs=[input_name, "weight"],
        outputs=[output_name],
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["GEMM"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                input_name: "ACTIVATION",
                "weight": "WEIGHT",
            },
            output_memory_classes={output_name: "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::/model/layers.0/mlp/gemm"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::/model/layers.0/mlp/gemm"],
        ),
    )


def _make_tile_candidate(
    candidate_id: str,
    node_id: str,
    macro_op: str,
    m_tile: int,
    n_tile: int,
    k_tile: int,
) -> object:
    from llm_sched.contracts.tiling_plan import TileCandidate

    return TileCandidate(
        candidate_id=candidate_id,
        node_id=node_id,
        macro_op=macro_op,
        strategy="fixture",
        m_tile=m_tile,
        n_tile=n_tile,
        k_tile=k_tile,
        read_bytes=0,
        write_bytes=0,
        total_vmem_bytes=0,
        rank=1,
        ranking_reason="fixture",
        quant_alignment_ok=True,
        quant_alignment_message="fixture",
        source_memory_plan_region_pressure={},
        resource_summary=None,
        issues=[],
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


def _make_passthrough_node(
    node_id: str,
    macro_op: str,
    shape: list[int],
    *,
    memory_class: str = "activation",
    input_name: str = "in0",
    output_name: str = "out0",
) -> object:
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
    input_memory_class = "KV_CACHE" if memory_class == "kv" else "ACTIVATION"
    output_memory_class = "KV_CACHE" if memory_class == "kv" else "ACTIVATION"
    return NIGNode(
        node_id=node_id,
        macro_op=macro_op,
        inputs=[input_name],
        outputs=[output_name],
        shape=shape,
        layout="HSD",
        memory_class=memory_class,
        legal_opcodes=[macro_op],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class=output_memory_class,
            input_memory_classes={input_name: input_memory_class},
            output_memory_classes={output_name: output_memory_class},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=[f"onnx::{macro_op}"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=[f"onnx::{macro_op}"],
        ),
    )
