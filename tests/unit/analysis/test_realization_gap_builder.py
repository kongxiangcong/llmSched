def test_build_realization_gap_rows_classifies_support_and_bandwidth_gaps() -> None:
    from llm_sched.analysis.realization_gap_builder import build_realization_gap_rows

    rows = build_realization_gap_rows(
        structure_demand_rows=[
            {
                "structure_id": "structure.layer0.attention_block",
                "structure_kind": "attention_block",
                "layer_id": 0,
                "compute_ops": 1024.0,
                "read_bytes": 256.0,
                "write_bytes": 256.0,
                "arithmetic_intensity": 2.0,
            },
            {
                "structure_id": "structure.layer1.mlp_block",
                "structure_kind": "mlp_block",
                "layer_id": 1,
                "compute_ops": 2048.0,
                "read_bytes": 1024.0,
                "write_bytes": 1024.0,
                "arithmetic_intensity": 1.0,
            },
        ],
        structure_support_rows=[
            {
                "structure_id": "structure.layer0.attention_block",
                "worst_support_status": "unsupported",
                "blocking_gap_count": 2,
                "native_count": 0,
                "constrained_count": 0,
                "fallback_count": 0,
                "unsupported_count": 2,
            },
            {
                "structure_id": "structure.layer1.mlp_block",
                "worst_support_status": "native",
                "blocking_gap_count": 0,
                "native_count": 3,
                "constrained_count": 0,
                "fallback_count": 0,
                "unsupported_count": 0,
            },
        ],
        schedule_block_rows=[],
        perf_by_structure_rows=[
            {
                "structure_id": "structure.layer0.attention_block",
                "estimated_cycles": 300.0,
                "fitted_work_cycles": 280.0,
                "total_bytes": 800.0,
                "dominant_bound": "bandwidth_bound",
            },
            {
                "structure_id": "structure.layer1.mlp_block",
                "estimated_cycles": 120.0,
                "fitted_work_cycles": 100.0,
                "total_bytes": 512.0,
                "dominant_bound": "bandwidth_bound",
            },
        ],
        subject_block_rows=[],
    )

    assert rows[0]["gap_kind"] == "support_gap"
    assert rows[0]["gap_confidence"] == "high"
    assert rows[1]["gap_kind"] == "bandwidth_gap"
    assert rows[1]["gap_confidence"] == "medium"


def test_build_timeline_loss_rows_classify_and_aggregate() -> None:
    from types import SimpleNamespace
    from llm_sched.analysis.timeline_loss_builder import (
        build_timeline_loss_detail_rows,
        build_timeline_loss_summary_rows,
    )

    report = SimpleNamespace(
        stall_events=[
            SimpleNamespace(
                block_id="sched.block.0",
                core_id=0,
                start_slot=10,
                end_slot=14,
                span_slots=4,
                reason="barrier sync wait",
                wait_for_block_ids=["sched.block.prev"],
            ),
            SimpleNamespace(
                block_id="sched.block.1",
                core_id=0,
                start_slot=20,
                end_slot=28,
                span_slots=8,
                reason="dma underlap",
                wait_for_block_ids=[],
            ),
        ],
        idle_spans=[
            SimpleNamespace(
                core_id=0,
                start_slot=30,
                end_slot=32,
                span_slots=2,
                reason="tiny gap",
                preceding_block_id="sched.block.1",
                following_block_id="sched.block.2",
            )
        ],
        resource_contention_summary=SimpleNamespace(makespan_slots=40),
    )

    detail_rows = build_timeline_loss_detail_rows(report)
    summary_rows = build_timeline_loss_summary_rows(detail_rows, makespan_slots=40)

    assert {row["loss_kind"] for row in detail_rows} == {"barrier_wait", "dma_underlap", "granularity_overhead"}
    dma_summary = next(row for row in summary_rows if row["loss_kind"] == "dma_underlap")
    assert dma_summary["recoverable_slots_total"] == 6.4
    assert "sched.block.1" in dma_summary["representative_entities"]
