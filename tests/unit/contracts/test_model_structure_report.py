import pytest
from pydantic import ValidationError


def test_model_structure_report_captures_hierarchy_and_traceability() -> None:
    from llm_sched.contracts.model_structure_report import ModelStructureReport

    report = ModelStructureReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "model_summary": {
                "model_name": "gemma3_1b",
                "total_layers": 1,
                "total_structures": 2,
                "total_nodes": 3,
                "structure_type_counts": {
                    "attention_block": 1,
                    "mlp_block": 1,
                },
            },
            "structures": [
                {
                    "structure_id": "structure.layer0.attention",
                    "structure_name": "layer0_attention",
                    "structure_kind": "attention_block",
                    "hierarchy_path": ["model", "layer.0", "attention"],
                    "layer_id": 0,
                    "parent_structure_id": None,
                    "node_ids": [
                        "graph.node.q_proj",
                        "graph.node.k_proj",
                    ],
                    "input_ports": [
                        {
                            "tensor_name": "hidden_states",
                            "shape": [1, 128, 2048],
                            "dtype": "bf16",
                        }
                    ],
                    "output_ports": [
                        {
                            "tensor_name": "attn_out",
                            "shape": [1, 128, 2048],
                            "dtype": "bf16",
                        }
                    ],
                    "attributes": {
                        "has_kv_cache": True,
                        "sequence_dependent": True,
                    },
                },
                {
                    "structure_id": "structure.layer0.mlp",
                    "structure_name": "layer0_mlp",
                    "structure_kind": "mlp_block",
                    "hierarchy_path": ["model", "layer.0", "mlp"],
                    "layer_id": 0,
                    "parent_structure_id": None,
                    "node_ids": ["graph.node.gate_proj"],
                    "input_ports": [],
                    "output_ports": [],
                    "attributes": {},
                },
            ],
            "layers": [
                {
                    "layer_id": 0,
                    "layer_name": "layer.0",
                    "structure_ids": [
                        "structure.layer0.attention",
                        "structure.layer0.mlp",
                    ],
                    "node_ids": [
                        "graph.node.q_proj",
                        "graph.node.k_proj",
                        "graph.node.gate_proj",
                    ],
                    "structure_kinds": [
                        "attention_block",
                        "mlp_block",
                    ],
                }
            ],
            "node_index": [
                {
                    "node_id": "graph.node.q_proj",
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.attention"],
                    "node_name": "q_proj",
                },
                {
                    "node_id": "graph.node.k_proj",
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.attention"],
                    "node_name": "k_proj",
                },
                {
                    "node_id": "graph.node.gate_proj",
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.mlp"],
                    "node_name": "gate_proj",
                },
            ],
        }
    )

    assert report.model_summary.total_layers == 1
    assert report.structures[0].hierarchy_path == ["model", "layer.0", "attention"]
    assert report.structures[0].input_ports[0].tensor_name == "hidden_states"
    assert report.layers[0].structure_ids == [
        "structure.layer0.attention",
        "structure.layer0.mlp",
    ]
    assert report.node_index[0].structure_ids == ["structure.layer0.attention"]


def test_model_structure_report_rejects_missing_required_fields() -> None:
    from llm_sched.contracts.model_structure_report import ModelStructureReport

    with pytest.raises(ValidationError):
        ModelStructureReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "structures": [],
                "layers": [],
                "node_index": [],
            }
        )


def test_model_structure_report_rejects_negative_layer_ids() -> None:
    from llm_sched.contracts.model_structure_report import ModelStructureReport

    with pytest.raises(ValidationError):
        ModelStructureReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "model_summary": {
                    "model_name": "gemma3_1b",
                    "total_layers": 1,
                    "total_structures": 1,
                    "total_nodes": 1,
                    "structure_type_counts": {"attention_block": 1},
                },
                "structures": [
                    {
                        "structure_id": "structure.invalid",
                        "structure_name": "invalid",
                        "structure_kind": "attention_block",
                        "hierarchy_path": ["model", "layer.-1", "attention"],
                        "layer_id": -1,
                        "parent_structure_id": None,
                        "node_ids": ["graph.node.q_proj"],
                        "input_ports": [],
                        "output_ports": [],
                        "attributes": {},
                    }
                ],
                "layers": [
                    {
                        "layer_id": -1,
                        "layer_name": "layer.-1",
                        "structure_ids": ["structure.invalid"],
                        "node_ids": ["graph.node.q_proj"],
                        "structure_kinds": ["attention_block"],
                    }
                ],
                "node_index": [
                    {
                        "node_id": "graph.node.q_proj",
                        "layer_id": -1,
                        "structure_ids": ["structure.invalid"],
                        "node_name": "q_proj",
                    }
                ],
            }
        )
