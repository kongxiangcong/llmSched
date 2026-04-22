"""Unit tests for the TaskDAG IR schema."""

from __future__ import annotations

import pytest

from llm_sched.ir.common import AuditRef
from llm_sched.ir.task_dag import TaskDAG, TaskInput, TaskNode, TaskOutput


def test_task_dag_serializes_to_json() -> None:
    task_dag = TaskDAG(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            TaskNode(task_id="task.a", macro_op="GEMM"),
            TaskNode(task_id="task.b", macro_op="RMSNorm"),
        ],
    )
    result = task_dag.model_dump(mode="json")
    assert isinstance(result, dict)
    assert "ir_version" in result
    assert "graph_id" in result
    assert "nodes" in result
    assert "output_tasks" in result


def test_task_dag_edges_property_returns_adjacency_list() -> None:
    task_dag = TaskDAG(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            TaskNode(
                task_id="task.a",
                macro_op="GEMM",
                outputs=[TaskOutput(tensor_name="x")],
            ),
            TaskNode(
                task_id="task.b",
                macro_op="RMSNorm",
                inputs=[TaskInput(source_task_id="task.a", tensor_name="x")],
            ),
        ],
    )
    # edges maps consumer -> list of producers it depends on
    assert task_dag.edges == {"task.a": [], "task.b": ["task.a"]}


def test_task_dag_rejects_duplicate_task_ids() -> None:
    with pytest.raises(ValueError, match="task ids must be unique"):
        TaskDAG(
            ir_version="0.10",
            graph_id="test_graph",
            nodes=[
                TaskNode(task_id="task.a", macro_op="GEMM"),
                TaskNode(task_id="task.a", macro_op="RMSNorm"),
            ],
        )


def test_task_dag_rejects_missing_source_task_id() -> None:
    with pytest.raises(ValueError, match="unknown source_task_id"):
        TaskDAG(
            ir_version="0.10",
            graph_id="test_graph",
            nodes=[
                TaskNode(
                    task_id="task.a",
                    macro_op="GEMM",
                    inputs=[TaskInput(source_task_id="task.missing", tensor_name="x")],
                ),
            ],
        )


def test_task_node_defaults() -> None:
    node = TaskNode(task_id="task.a", macro_op="GEMM")
    assert node.inputs == []
    assert node.outputs == []
    assert node.attrs == {}
    assert isinstance(node.audit_ref, AuditRef)


def test_task_dag_round_trip_via_model_dump_validate() -> None:
    original = TaskDAG(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            TaskNode(
                task_id="task.a",
                macro_op="GEMM",
                outputs=[TaskOutput(tensor_name="x", shape=[1, 128])],
            ),
            TaskNode(
                task_id="task.b",
                macro_op="RMSNorm",
                inputs=[TaskInput(source_task_id="task.a", tensor_name="x")],
            ),
        ],
        output_tasks=["task.b"],
    )
    dumped = original.model_dump(mode="json")
    reconstructed = TaskDAG.model_validate(dumped)
    assert reconstructed.ir_version == original.ir_version
    assert reconstructed.graph_id == original.graph_id
    assert len(reconstructed.nodes) == len(original.nodes)
    assert reconstructed.output_tasks == original.output_tasks


def test_task_dag_rejects_missing_source_task_id_at_ir_level() -> None:
    with pytest.raises(ValueError, match="unknown source_task_id"):
        TaskDAG(
            ir_version="0.10",
            graph_id="test_graph",
            nodes=[
                TaskNode(
                    task_id="task.consumer",
                    macro_op="GEMM",
                    inputs=[TaskInput(source_task_id="task.nonexistent", tensor_name="x")],
                ),
            ],
        )
