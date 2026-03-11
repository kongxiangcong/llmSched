from pydantic import ValidationError


def test_tiling_plan_artifact_accepts_candidate_metadata() -> None:
    from llm_sched.contracts.tiling_plan import (
        TileCandidate,
        TileCandidateResourceSummary,
        TilingPlanArtifact,
    )

    artifact = TilingPlanArtifact(
        graph_id="spec-09-fixture",
        scenario_name="prefill_seq128",
        core_mode="single-core",
        candidates=[
            TileCandidate(
                candidate_id="candidate.linear.m48",
                node_id="nig.node.linear",
                macro_op="WDQ_GEMM",
                strategy="prefill-balanced",
                m_tile=48,
                n_tile=128,
                k_tile=128,
                read_bytes=16_384,
                write_bytes=12_288,
                total_vmem_bytes=24_576,
                rank=1,
                ranking_reason="prefill-throughput-first: largest fitting m_tile wins",
                quant_alignment_ok=True,
                quant_alignment_message="group_size=128 aligns with k_tile=128",
                source_memory_plan_region_pressure={"ping": 12_288, "pong": 12_288, "accum": 24_576},
                resource_summary=TileCandidateResourceSummary(
                    read_bytes=16_384,
                    write_bytes=12_288,
                    total_vmem_bytes=24_576,
                    dma_bytes=28_672,
                    region_pressure_bytes={"ping": 12_288, "pong": 12_288, "accum": 24_576},
                    storage_binding_ids=["storage.weight.nig.node.linear.weight"],
                    storage_read_bytes_by_source_kind={"weight_tensor": 8_192, "quant_tensor": 4},
                    storage_read_bytes_by_backing_store={"ddr-backed-staged": 8_196},
                ),
            )
        ],
    )

    candidate = artifact.candidates[0]
    assert candidate.m_tile == 48
    assert candidate.rank == 1
    assert candidate.quant_alignment_ok is True
    assert candidate.source_memory_plan_region_pressure["accum"] == 24_576
    assert candidate.resource_summary.storage_binding_ids == ["storage.weight.nig.node.linear.weight"]
    assert candidate.resource_summary.storage_read_bytes_by_source_kind["weight_tensor"] == 8_192


def test_tile_candidate_rejects_non_positive_tile_shape() -> None:
    from llm_sched.contracts.tiling_plan import TileCandidate

    try:
        TileCandidate(
            candidate_id="candidate.bad",
            node_id="nig.node.bad",
            macro_op="GEMM",
            strategy="prefill-balanced",
            m_tile=0,
            n_tile=128,
            k_tile=128,
            read_bytes=1,
            write_bytes=1,
            total_vmem_bytes=1,
            rank=1,
            ranking_reason="bad",
            quant_alignment_ok=True,
            quant_alignment_message="ok",
            source_memory_plan_region_pressure={},
        )
    except ValidationError:
        return

    raise AssertionError("expected TileCandidate to reject non-positive m_tile")


def test_tile_candidate_rejects_non_positive_rank() -> None:
    from llm_sched.contracts.tiling_plan import TileCandidate

    try:
        TileCandidate(
            candidate_id="candidate.bad.rank",
            node_id="nig.node.bad",
            macro_op="GEMM",
            strategy="prefill-balanced",
            m_tile=16,
            n_tile=128,
            k_tile=128,
            read_bytes=1,
            write_bytes=1,
            total_vmem_bytes=1,
            rank=0,
            ranking_reason="bad",
            quant_alignment_ok=True,
            quant_alignment_message="ok",
            source_memory_plan_region_pressure={},
        )
    except ValidationError:
        return

    raise AssertionError("expected TileCandidate to reject non-positive rank")
