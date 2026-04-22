"""Unit tests for the TaskDAG builder."""

from __future__ import annotations

import pytest

from llm_sched.frontend.task_dag_builder import TaskDAGBuildError, build_task_dag
from llm_sched.ir.common import AuditRef
from llm_sched.ir.nig import NIGIR, NIGNode, QuantBinding
from llm_sched.ir.task_dag import TaskDAG, TaskInput, TaskNode, TaskOutput


def _make_quant() -> QuantBinding:
    return QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
    )


def test_build_task_dag_creates_task_nodes_for_compute_ops() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.node.gemm",
                macro_op="GEMM",
                inputs=["tokens", "weight"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    compute_tasks = [n for n in dag.nodes if n.macro_op not in {"Input", "Constant"}]
    assert len(compute_tasks) == 1
    task = compute_tasks[0]
    assert task.task_id == "task.node.gemm"
    assert task.macro_op == "GEMM"
    assert len(task.inputs) == 2
    assert task.inputs[0].tensor_name == "tokens"
    assert task.inputs[1].tensor_name == "weight"


def test_build_task_dag_elides_layout_ops() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.layout",
                macro_op="LAYOUT_FALLBACK",
                inputs=["tokens"],
                outputs=["tokens.layout"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["LAYOUT_FALLBACK"],
                quant=_make_quant(),
            ),
            NIGNode(
                node_id="nig.gemm",
                macro_op="GEMM",
                inputs=["tokens.layout", "weight"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    compute_tasks = [n for n in dag.nodes if n.macro_op not in {"Input", "Constant"}]
    assert len(compute_tasks) == 1
    task = compute_tasks[0]
    assert task.task_id == "task.gemm"
    assert task.macro_op == "GEMM"

    # The GEMM's input for "tokens.layout" should resolve to the Input task for "tokens"
    input_task = next((n for n in dag.nodes if n.macro_op == "Input"), None)
    assert input_task is not None
    tokens_input = next((inp for inp in task.inputs if inp.tensor_name == "tokens"), None)
    assert tokens_input is not None
    assert tokens_input.source_task_id == input_task.task_id


def test_build_task_dag_creates_input_tasks_for_graph_inputs() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.gemm",
                macro_op="GEMM",
                inputs=["tokens", "weight"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    input_task = next((n for n in dag.nodes if n.macro_op == "Input"), None)
    assert input_task is not None
    assert input_task.task_id == "task.input.tokens"
    assert any(o.tensor_name == "tokens" for o in input_task.outputs)

    gemm_task = next((n for n in dag.nodes if n.macro_op == "GEMM"), None)
    assert gemm_task is not None
    tokens_input = next((inp for inp in gemm_task.inputs if inp.tensor_name == "tokens"), None)
    assert tokens_input is not None
    assert tokens_input.source_task_id == input_task.task_id


def test_build_task_dag_creates_constant_tasks_for_weight_tensors() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.gemm",
                macro_op="GEMM",
                inputs=["tokens", "weight"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    constant_task = next((n for n in dag.nodes if n.macro_op == "Constant"), None)
    assert constant_task is not None
    assert constant_task.task_id == "task.const.weight"
    assert any(o.tensor_name == "weight" for o in constant_task.outputs)

    gemm_task = next((n for n in dag.nodes if n.macro_op == "GEMM"), None)
    assert gemm_task is not None
    weight_input = next((inp for inp in gemm_task.inputs if inp.tensor_name == "weight"), None)
    assert weight_input is not None
    assert weight_input.source_task_id == constant_task.task_id


def test_build_task_dag_traces_dependencies_through_elided_chain() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.gemm1",
                macro_op="GEMM",
                inputs=["tokens", "weight1"],
                outputs=["mid"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
            NIGNode(
                node_id="nig.layout",
                macro_op="LAYOUT_FALLBACK",
                inputs=["mid"],
                outputs=["mid.layout"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["LAYOUT_FALLBACK"],
                quant=_make_quant(),
            ),
            NIGNode(
                node_id="nig.shape",
                macro_op="SHAPE_HELPER",
                inputs=["mid.layout"],
                outputs=["mid.shape"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["SHAPE_HELPER"],
                quant=_make_quant(),
            ),
            NIGNode(
                node_id="nig.gemm2",
                macro_op="GEMM",
                inputs=["mid.shape", "weight2"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    gemm2_task = next((n for n in dag.nodes if n.task_id == "task.gemm2"), None)
    assert gemm2_task is not None
    mid_input = next((inp for inp in gemm2_task.inputs if inp.tensor_name == "mid"), None)
    assert mid_input is not None
    assert mid_input.source_task_id == "task.gemm1"


def test_build_task_dag_sets_output_tasks_correctly() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.gemm",
                macro_op="GEMM",
                inputs=["tokens", "weight"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    gemm_task = next((n for n in dag.nodes if n.macro_op == "GEMM"), None)
    assert gemm_task is not None
    assert gemm_task.task_id in dag.output_tasks


def test_build_task_dag_preserves_audit_ref() -> None:
    audit = AuditRef(graph_node_ids=["onnx.gemm_0"], source_ids=["src"])
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.gemm",
                macro_op="GEMM",
                inputs=["tokens", "weight"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
                audit_ref=audit,
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    gemm_task = next((n for n in dag.nodes if n.macro_op == "GEMM"), None)
    assert gemm_task is not None
    assert gemm_task.audit_ref.graph_node_ids == ["onnx.gemm_0"]
    assert gemm_task.audit_ref.source_ids == ["src"]


def test_build_task_dag_preserves_attrs() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.gemm",
                macro_op="GEMM",
                inputs=["tokens", "weight"],
                outputs=["hidden"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
                attrs={"alpha": 1.0, "beta": 0.0},
            ),
        ],
    )
    dag = build_task_dag(nig_ir, graph_input_names={"tokens"})

    gemm_task = next((n for n in dag.nodes if n.macro_op == "GEMM"), None)
    assert gemm_task is not None
    assert gemm_task.attrs == {"alpha": 1.0, "beta": 0.0}
