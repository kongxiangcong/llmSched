"""Unit tests for the TaskDAG builder."""

from __future__ import annotations

import pytest

from llm_sched.frontend.task_dag_builder import TaskDAGBuildError, build_task_dag, validate_task_dag
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


def test_build_task_dag_validates_acyclic_graph_passes() -> None:
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.input",
                macro_op="Input",
                inputs=[],
                outputs=["tokens"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["Input"],
                quant=_make_quant(),
            ),
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
    assert isinstance(dag, TaskDAG)


def test_build_task_dag_raises_on_cycle() -> None:
    # Manually construct a cycle: A consumes B's output, B consumes A's output
    nig_ir = NIGIR(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            NIGNode(
                node_id="nig.a",
                macro_op="GEMM",
                inputs=["b_out", "weight_a"],
                outputs=["a_out"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
            NIGNode(
                node_id="nig.b",
                macro_op="GEMM",
                inputs=["a_out", "weight_b"],
                outputs=["b_out"],
                shape=[1, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["GEMM"],
                quant=_make_quant(),
            ),
        ],
    )
    with pytest.raises(TaskDAGBuildError) as exc_info:
        build_task_dag(nig_ir, graph_input_names=set())
    assert any("cycle" in d.lower() for d in exc_info.value.diagnostics)


def test_build_task_dag_raises_on_orphaned_task() -> None:
    # build_task_dag auto-creates Input/Constant tasks for all consumed tensors,
    # so it cannot naturally produce orphans. Test the orphan check directly
    # on a manually constructed TaskDAG with a closed subgraph disconnected
    # from Input/Constant seeds.
    task_dag = TaskDAG(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            TaskNode(
                task_id="task.a",
                macro_op="Input",
                outputs=[TaskOutput(tensor_name="x")],
            ),
            TaskNode(
                task_id="task.b",
                macro_op="GEMM",
                inputs=[TaskInput(source_task_id="task.a", tensor_name="x")],
                outputs=[TaskOutput(tensor_name="y")],
            ),
            # Disconnected subgraph: orphan feeds orphan2, neither reachable from Input/Constant
            TaskNode(
                task_id="task.orphan",
                macro_op="RMSNorm",
                outputs=[TaskOutput(tensor_name="z")],
            ),
            TaskNode(
                task_id="task.orphan2",
                macro_op="GEMM",
                inputs=[TaskInput(source_task_id="task.orphan", tensor_name="z")],
                outputs=[TaskOutput(tensor_name="w")],
            ),
        ],
        output_tasks=["task.b"],
    )
    with pytest.raises(TaskDAGBuildError) as exc_info:
        validate_task_dag(task_dag)
    assert any("orphaned" in d.lower() for d in exc_info.value.diagnostics)


def test_validate_task_dag_passes_for_valid_dag() -> None:
    task_dag = TaskDAG(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            TaskNode(
                task_id="task.a",
                macro_op="Input",
                outputs=[TaskOutput(tensor_name="x")],
            ),
            TaskNode(
                task_id="task.b",
                macro_op="GEMM",
                inputs=[TaskInput(source_task_id="task.a", tensor_name="x")],
                outputs=[TaskOutput(tensor_name="y")],
            ),
        ],
        output_tasks=["task.b"],
    )
    validate_task_dag(task_dag)  # should not raise


def test_task_dag_build_error_has_diagnostics() -> None:
    # Build a valid TaskDAG then mutate it to introduce a missing producer reference,
    # bypassing the Pydantic construction-time validator.
    task_dag = TaskDAG(
        ir_version="0.10",
        graph_id="test_graph",
        nodes=[
            TaskNode(
                task_id="task.a",
                macro_op="GEMM",
                outputs=[TaskOutput(tensor_name="x")],
            ),
        ],
    )
    # Inject an invalid input reference directly
    task_dag.nodes[0].inputs.append(TaskInput(source_task_id="task.missing", tensor_name="x"))
    with pytest.raises(TaskDAGBuildError) as exc_info:
        validate_task_dag(task_dag)
    error = exc_info.value
    assert isinstance(error.diagnostics, list)
    assert len(error.diagnostics) > 0
    assert str(error) == error.message
