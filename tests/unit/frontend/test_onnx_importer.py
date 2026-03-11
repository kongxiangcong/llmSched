import onnx
from onnx import TensorProto, helper

from llm_sched.frontend import import_onnx_to_graph_ir
from llm_sched.frontend.canonicalize import canonicalize_graph_ir
from llm_sched.frontend.onnx_importer import build_frontend_import_report


def test_importer_builds_graph_ir_from_tiny_onnx_model() -> None:
    graph_ir = import_onnx_to_graph_ir(_build_tiny_matmul_model())

    assert graph_ir.ir_version == "phase-a.v1"
    assert graph_ir.graph_id == "tiny-matmul"
    assert [node.op_kind for node in graph_ir.nodes] == ["Input", "Constant", "MatMul"]

    input_node, constant_node, matmul_node = graph_ir.nodes

    assert input_node.node_id.startswith("graph.input.")
    assert input_node.inputs == []
    assert input_node.outputs == ["tokens"]
    assert input_node.shape == [1, 2]
    assert input_node.dtype == "float32"
    assert input_node.source_ref == ["onnx::tokens"]
    assert input_node.audit_ref.graph_node_ids == [input_node.node_id]
    assert input_node.audit_ref.source_ids == ["onnx::tokens"]

    assert constant_node.node_id.startswith("graph.const.")
    assert constant_node.inputs == []
    assert constant_node.outputs == ["weight"]
    assert constant_node.shape == [2, 4]
    assert constant_node.dtype == "float32"
    assert constant_node.source_ref == ["onnx::weight"]
    assert constant_node.audit_ref.graph_node_ids == [constant_node.node_id]
    assert constant_node.audit_ref.source_ids == ["onnx::weight"]

    assert matmul_node.node_id.startswith("graph.node.")
    assert matmul_node.inputs == ["tokens", "weight"]
    assert matmul_node.outputs == ["hidden"]
    assert matmul_node.shape == [1, 4]
    assert matmul_node.dtype == "float32"
    assert matmul_node.attrs == {}
    assert matmul_node.source_ref == ["onnx::MatMul_0"]
    assert matmul_node.audit_ref.graph_node_ids == [matmul_node.node_id]
    assert matmul_node.audit_ref.source_ids == ["onnx::MatMul_0"]


def test_importer_applies_optional_shape_bindings_before_inference() -> None:
    graph_ir = import_onnx_to_graph_ir(
        _build_symbolic_add_model(),
        shape_bindings={"batch_size": 1, "sequence_length": 128},
    )

    input_node, bias_node, add_node = graph_ir.nodes

    assert input_node.shape == [1, 128]
    assert bias_node.shape == [1, 128]
    assert add_node.shape == [1, 128]


def test_build_frontend_import_report_counts_unresolved_shapes_and_residual_ops() -> None:
    imported_graph_ir = import_onnx_to_graph_ir(_build_symbolic_add_model())
    canonical_graph_ir = canonicalize_graph_ir(imported_graph_ir)

    report = build_frontend_import_report(imported_graph_ir, canonical_graph_ir)

    assert report.graph_id == "symbolic-add"
    assert report.raw_node_total == 3
    assert report.canonical_node_total == 3
    assert report.imported_input_count == 1
    assert report.imported_constant_count == 1
    assert report.unresolved_shape_node_count == 2
    assert report.unresolved_shape_dim_count == 3
    assert report.raw_node_counts == {"Add": 1, "Constant": 1, "Input": 1}
    assert report.canonical_node_counts == {"Add": 1, "Constant": 1, "Input": 1}
    assert report.residual_op_counts == {"Add": 1}
    assert report.warning_counts == {
        "dynamic_shape_unresolved": 1,
        "residual_raw_op": 1,
    }
    assert report.warnings[0].rule_id == "dynamic_shape_unresolved"
    assert report.warnings[1].rule_id == "residual_raw_op"
    assert report.warnings[1].op_kind == "Add"


def _build_tiny_matmul_model() -> onnx.ModelProto:
    tokens = helper.make_tensor_value_info("tokens", TensorProto.FLOAT, [1, 2])
    hidden = helper.make_tensor_value_info("hidden", TensorProto.FLOAT, [1, 4])
    weight = helper.make_tensor(
        "weight",
        TensorProto.FLOAT,
        dims=[2, 4],
        vals=[
            0.0,
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
            6.0,
            7.0,
        ],
    )
    matmul = helper.make_node(
        "MatMul",
        inputs=["tokens", "weight"],
        outputs=["hidden"],
        name="MatMul_0",
    )
    graph = helper.make_graph(
        nodes=[matmul],
        name="tiny-matmul",
        inputs=[tokens],
        outputs=[hidden],
        initializer=[weight],
    )
    return helper.make_model(graph, producer_name="llm-sched-tests")


def _build_symbolic_add_model() -> onnx.ModelProto:
    tokens = helper.make_tensor_value_info(
        "tokens",
        TensorProto.FLOAT,
        ["batch_size", "sequence_length"],
    )
    hidden = helper.make_tensor_value_info(
        "hidden",
        TensorProto.FLOAT,
        ["batch_size", "sequence_length"],
    )
    bias = helper.make_tensor(
        "bias",
        TensorProto.FLOAT,
        dims=[1, 128],
        vals=[0.0] * 128,
    )
    add = helper.make_node(
        "Add",
        inputs=["tokens", "bias"],
        outputs=["hidden"],
        name="Add_0",
    )
    graph = helper.make_graph(
        nodes=[add],
        name="symbolic-add",
        inputs=[tokens],
        outputs=[hidden],
        initializer=[bias],
    )
    return helper.make_model(graph, producer_name="llm-sched-tests")
