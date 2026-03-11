import pytest
from pydantic import ValidationError

from llm_sched.ir.validators import validate_schedule_ir


def test_schedule_ir_accepts_single_core_scheduler_block_metadata() -> None:
    schedule = validate_schedule_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "sched-001",
            "core_mode": "single-core",
            "blocks": [
                {
                    "block_id": "sched.block.linear.compute",
                    "core_id": 0,
                    "node_id": "nig.node.linear",
                    "macro_op": "WDQ_GEMM",
                    "stage": "compute",
                    "tiling_candidate_id": "nig.node.linear.m48.n128.k128",
                    "resource_set": ["WDQ", "MXU"],
                    "buffer_binding": {"input": "ping", "output": "pong"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "depends_on": [],
                    "issue_slot": 2,
                    "duration_slots": 1,
                    "order_key": 2,
                }
            ],
        }
    )

    assert schedule.blocks[0].stage == "compute"
    assert schedule.blocks[0].tiling_candidate_id == "nig.node.linear.m48.n128.k128"
    assert schedule.blocks[0].issue_slot == 2


def test_schedule_ir_rejects_duplicate_block_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_schedule_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "sched-001",
                "core_mode": "dual-core",
                "blocks": [
                    {
                        "block_id": "sched.block.0",
                        "core_id": 0,
                        "resource_set": ["DMA"],
                        "buffer_binding": {"input": "ping"},
                        "barrier_in": [],
                        "barrier_out": [],
                        "order_key": 0,
                    },
                    {
                        "block_id": "sched.block.0",
                        "core_id": 1,
                        "resource_set": ["VPU"],
                        "buffer_binding": {"input": "pong"},
                        "barrier_in": [],
                        "barrier_out": [],
                        "order_key": 1,
                    },
                ],
            }
        )

    assert "schedule block ids must be unique" in str(exc_info.value)


def test_single_core_schedule_rejects_core_link_resource() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_schedule_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "sched-002",
                "core_mode": "single-core",
                "blocks": [
                    {
                        "block_id": "sched.block.0",
                        "core_id": 0,
                        "node_id": "nig.node.0",
                        "macro_op": "WDQ_GEMM",
                        "stage": "dma_in",
                        "tiling_candidate_id": "nig.node.0.m48.n128.k128",
                        "resource_set": ["DMA", "Core Link"],
                        "buffer_binding": {"input": "ping"},
                        "barrier_in": [],
                        "barrier_out": [],
                        "order_key": 0,
                    }
                ],
            }
        )

    assert "single-core schedules must not use Core Link" in str(exc_info.value)


def test_schedule_ir_accepts_dual_core_transfer_metadata() -> None:
    schedule = validate_schedule_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "sched-003",
            "core_mode": "dual-core",
            "blocks": [
                {
                    "block_id": "sched.block.0",
                    "core_id": 0,
                    "node_id": "nig.node.attn",
                    "macro_op": "SDPA",
                    "stage": "compute",
                    "tiling_candidate_id": "nig.node.attn.m32.n128.k128",
                    "resource_set": ["MXU", "VPU"],
                    "buffer_binding": {"activation": "pong"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "depends_on": [],
                    "issue_slot": 2,
                    "duration_slots": 1,
                    "order_key": 2,
                },
                {
                    "block_id": "sched.transfer.0",
                    "core_id": 0,
                    "peer_core_id": 1,
                    "node_id": "nig.node.attn",
                    "macro_op": "SDPA",
                    "stage": "transfer",
                    "tiling_candidate_id": "nig.node.attn.m32.n128.k128",
                    "resource_set": ["Core Link"],
                    "buffer_binding": {"activation": "pong"},
                    "barrier_in": ["sync.transfer.0.in"],
                    "barrier_out": ["sync.transfer.0.out"],
                    "depends_on": ["sched.block.0"],
                    "issue_slot": 3,
                    "duration_slots": 1,
                    "transfer_kind": "core_link",
                    "transfer_bytes": 8192,
                    "sync_cost_cycles": 18,
                    "order_key": 3,
                }
            ],
        }
    )

    block = schedule.blocks[1]
    assert block.stage == "transfer"
    assert block.peer_core_id == 1
    assert block.transfer_kind == "core_link"
    assert block.transfer_bytes == 8192


def test_schedule_ir_rejects_unknown_dependency_block_id() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_schedule_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "sched-005",
                "core_mode": "single-core",
                "blocks": [
                    {
                        "block_id": "sched.block.0",
                        "core_id": 0,
                        "node_id": "nig.node.0",
                        "macro_op": "RMSNORM",
                        "stage": "compute",
                        "tiling_candidate_id": None,
                        "resource_set": ["VPU"],
                        "buffer_binding": {"input": "ping", "output": "pong"},
                        "barrier_in": [],
                        "barrier_out": [],
                        "depends_on": ["sched.block.missing"],
                        "issue_slot": 1,
                        "duration_slots": 1,
                        "order_key": 0,
                    }
                ],
            }
        )

    assert "schedule depends_on entries must reference existing block ids" in str(exc_info.value)


def test_dual_core_schedule_rejects_transfer_without_barriers() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_schedule_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "sched-004",
                "core_mode": "dual-core",
                "blocks": [
                    {
                        "block_id": "sched.transfer.0",
                        "core_id": 0,
                        "peer_core_id": 1,
                        "node_id": "nig.node.attn",
                        "macro_op": "SDPA",
                        "stage": "transfer",
                        "tiling_candidate_id": "nig.node.attn.m32.n128.k128",
                        "resource_set": ["DMA"],
                        "buffer_binding": {"activation": "pong"},
                        "barrier_in": [],
                        "barrier_out": [],
                        "transfer_kind": "dma",
                        "transfer_bytes": 4096,
                        "sync_cost_cycles": 18,
                        "order_key": 4,
                    }
                ],
            }
        )

    assert "transfer blocks must declare barrier_in and barrier_out" in str(exc_info.value)
