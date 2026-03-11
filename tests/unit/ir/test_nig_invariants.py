import pytest
from pydantic import ValidationError

from llm_sched.ir.validators import validate_nig_ir


def test_nig_ir_rejects_empty_legal_opcode_set() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_nig_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "nig-001",
                "nodes": [
                    {
                        "node_id": "nig.node.0",
                        "macro_op": "RMSNORM_GEMM",
                        "inputs": ["tensor.input"],
                        "outputs": ["tensor.q"],
                        "layout": "HSD",
                        "memory_class": "activation",
                        "legal_opcodes": [],
                        "quant": {
                            "weight_dtype": "int4",
                            "activation_dtype": "bf16",
                            "group_size": 128,
                        },
                    }
                ],
            }
        )

    assert "nig nodes must declare at least one legal opcode" in str(exc_info.value)


def test_nig_ir_accepts_shape_and_attrs_fields() -> None:
    nig = validate_nig_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "nig-001",
            "nodes": [
                {
                    "node_id": "nig.node.0",
                    "macro_op": "ATTENTION_MASK_PREP",
                    "inputs": ["attn.mask.raw"],
                    "outputs": ["attn.mask.ready"],
                    "shape": [1, 1, 128, 128],
                    "layout": "LBHSD",
                    "memory_class": "activation",
                    "legal_opcodes": ["ATTENTION_MASK_PREP"],
                    "quant": {
                        "weight_dtype": "none",
                        "activation_dtype": "bf16",
                        "group_size": 1,
                    },
                    "attrs": {
                        "canonical_pattern": "AttentionMaskPrep",
                        "original_op_kind": "Mul",
                    },
                }
            ],
        }
    )

    assert nig.nodes[0].shape == [1, 1, 128, 128]
    assert nig.nodes[0].attrs == {
        "canonical_pattern": "AttentionMaskPrep",
        "original_op_kind": "Mul",
    }


def test_nig_ir_rejects_bound_compute_node_without_binding() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_nig_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "nig-001",
                "binding_state": "bound",
                "nodes": [
                    {
                        "node_id": "nig.node.0",
                        "macro_op": "GEMM",
                        "inputs": ["tensor.input"],
                        "outputs": ["tensor.hidden"],
                        "shape": [1, 128, 1024],
                        "layout": "HSD",
                        "memory_class": "activation",
                        "legal_opcodes": ["GEMM"],
                        "quant": {
                            "weight_dtype": "bf16",
                            "activation_dtype": "bf16",
                            "group_size": 1,
                        },
                    }
                ],
            }
        )

    assert "bound nig compute nodes must declare binding payloads" in str(exc_info.value)
