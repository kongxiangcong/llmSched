import pytest
from pydantic import ValidationError

from llm_sched.ir.validators import validate_graph_ir


def test_graph_ir_rejects_duplicate_node_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_graph_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "graph-001",
                "nodes": [
                    {
                        "node_id": "graph.node.0",
                        "op_kind": "Input",
                        "inputs": [],
                        "outputs": ["tensor.0"],
                        "shape": [1],
                        "dtype": "bf16",
                        "attrs": {},
                    },
                    {
                        "node_id": "graph.node.0",
                        "op_kind": "Identity",
                        "inputs": ["tensor.0"],
                        "outputs": ["tensor.1"],
                        "shape": [1],
                        "dtype": "bf16",
                        "attrs": {},
                    },
                ],
            }
        )

    assert "graph node ids must be unique" in str(exc_info.value)
