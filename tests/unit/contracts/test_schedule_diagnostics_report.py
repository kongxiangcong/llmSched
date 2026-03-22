import pytest
from pydantic import ValidationError


def test_schedule_diagnostics_report_captures_blocks_lanes_idle_stalls_and_contention() -> None:
    from llm_sched.contracts.schedule_diagnostics_report import ScheduleDiagnosticsReport

    report = ScheduleDiagnosticsReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "blocks": [
                {
                    "block_id": "sched.block.q_proj.dma_in",
                    "node_id": "nig.node.q_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "stage": "dma_in",
                    "core_ids": [0],
                    "issue_slot": 0,
                    "duration_slots": 3,
                    "start_slot": 0,
                    "end_slot": 3,
                    "span_slots": 3,
                    "depends_on": [],
                    "stall_reason": None,
                    "wait_for_block_ids": [],
                },
                {
                    "block_id": "sched.block.q_proj.compute",
                    "node_id": "nig.node.q_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "stage": "compute",
                    "core_ids": [0],
                    "issue_slot": 4,
                    "duration_slots": 6,
                    "start_slot": 4,
                    "end_slot": 10,
                    "span_slots": 6,
                    "depends_on": ["sched.block.q_proj.dma_in"],
                    "stall_reason": "dependency_wait",
                    "wait_for_block_ids": ["sched.block.q_proj.dma_in"],
                },
            ],
            "core_lanes": [
                {
                    "core_id": 0,
                    "occupied_slots": 9,
                    "makespan_slots": 10,
                    "utilization_ratio": 0.9,
                    "block_ids": [
                        "sched.block.q_proj.dma_in",
                        "sched.block.q_proj.compute",
                    ],
                }
            ],
            "idle_spans": [
                {
                    "core_id": 0,
                    "start_slot": 3,
                    "end_slot": 4,
                    "span_slots": 1,
                    "reason": "dependency_wait",
                    "preceding_block_id": "sched.block.q_proj.dma_in",
                    "following_block_id": "sched.block.q_proj.compute",
                }
            ],
            "stall_events": [
                {
                    "block_id": "sched.block.q_proj.compute",
                    "core_id": 0,
                    "start_slot": 3,
                    "end_slot": 4,
                    "span_slots": 1,
                    "reason": "dependency_wait",
                    "wait_for_block_ids": ["sched.block.q_proj.dma_in"],
                }
            ],
            "critical_path_blocks": [
                "sched.block.q_proj.dma_in",
                "sched.block.q_proj.compute",
            ],
            "resource_contention_summary": {
                "makespan_slots": 10,
                "contention_slots": 1,
                "contention_ratio": 0.1,
                "contended_resources": {
                    "DMA": 1,
                },
                "top_contention_block_ids": ["sched.block.q_proj.compute"],
            },
        }
    )

    assert report.blocks[1].end_slot == 10
    assert report.core_lanes[0].utilization_ratio == pytest.approx(0.9)
    assert report.idle_spans[0].reason == "dependency_wait"
    assert report.stall_events[0].wait_for_block_ids == ["sched.block.q_proj.dma_in"]
    assert report.resource_contention_summary.contended_resources["DMA"] == 1


def test_schedule_diagnostics_report_requires_resource_contention_summary() -> None:
    from llm_sched.contracts.schedule_diagnostics_report import ScheduleDiagnosticsReport

    with pytest.raises(ValidationError):
        ScheduleDiagnosticsReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "blocks": [],
                "core_lanes": [],
                "idle_spans": [],
                "stall_events": [],
                "critical_path_blocks": [],
            }
        )


def test_schedule_diagnostics_report_rejects_inconsistent_block_span() -> None:
    from llm_sched.contracts.schedule_diagnostics_report import ScheduleDiagnosticsReport

    with pytest.raises(ValidationError):
        ScheduleDiagnosticsReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "blocks": [
                    {
                        "block_id": "sched.block.bad",
                        "node_id": "nig.node.bad.0",
                        "macro_op": "BAD",
                        "stage": "compute",
                        "core_ids": [0],
                        "issue_slot": 2,
                        "duration_slots": 5,
                        "start_slot": 2,
                        "end_slot": 6,
                        "span_slots": 4,
                        "depends_on": [],
                        "stall_reason": None,
                        "wait_for_block_ids": [],
                    }
                ],
                "core_lanes": [],
                "idle_spans": [],
                "stall_events": [],
                "critical_path_blocks": [],
                "resource_contention_summary": {
                    "makespan_slots": 0,
                    "contention_slots": 0,
                    "contention_ratio": 0.0,
                    "contended_resources": {},
                    "top_contention_block_ids": [],
                },
            }
        )
