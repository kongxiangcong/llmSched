import pytest
from pydantic import ValidationError


def test_resource_demand_report_tracks_node_layer_structure_and_total_demands() -> None:
    from llm_sched.contracts.resource_demand_report import ResourceDemandReport

    report = ResourceDemandReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_demands": [
                {
                    "subject_id": "nig.node.q_proj.0",
                    "layer_id": 0,
                    "structure_id": "structure.layer0.attention_block",
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "compute_ops": 67108864.0,
                    "read_bytes": 131072.0,
                    "write_bytes": 32768.0,
                    "working_set_bytes": 65536.0,
                    "dependency_depth": 1,
                }
            ],
            "layer_demands": [
                {
                    "layer_id": 0,
                    "compute_ops": 67108864.0,
                    "read_bytes": 131072.0,
                    "write_bytes": 32768.0,
                    "working_set_bytes": 65536.0,
                    "dependency_depth": 1,
                    "node_count": 1,
                    "structure_ids": ["structure.layer0.attention_block"],
                }
            ],
            "structure_demands": [
                {
                    "structure_id": "structure.layer0.attention_block",
                    "layer_id": 0,
                    "structure_kind": "attention_block",
                    "compute_ops": 67108864.0,
                    "read_bytes": 131072.0,
                    "write_bytes": 32768.0,
                    "working_set_bytes": 65536.0,
                    "dependency_depth": 1,
                    "node_count": 1,
                }
            ],
            "totals": {
                "compute_ops": 67108864.0,
                "read_bytes": 131072.0,
                "write_bytes": 32768.0,
                "working_set_bytes": 65536.0,
                "node_count": 1,
                "layer_count": 1,
                "structure_count": 1,
            },
            "assumptions": [
                {
                    "assumption_id": "approx.compute.wdq_gemm",
                    "category": "compute_model",
                    "message": "WDQ_GEMM compute_ops are estimated from output shape and reduction size.",
                }
            ],
        }
    )

    assert report.node_demands[0].compute_ops == 67108864.0
    assert report.layer_demands[0].structure_ids == ["structure.layer0.attention_block"]
    assert report.structure_demands[0].structure_kind == "attention_block"
    assert report.totals.structure_count == 1
    assert report.assumptions[0].category == "compute_model"


def test_resource_demand_report_requires_totals() -> None:
    from llm_sched.contracts.resource_demand_report import ResourceDemandReport

    with pytest.raises(ValidationError):
        ResourceDemandReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "node_demands": [],
                "layer_demands": [],
                "structure_demands": [],
                "assumptions": [],
            }
        )


def test_resource_demand_report_rejects_negative_demands() -> None:
    from llm_sched.contracts.resource_demand_report import ResourceDemandReport

    with pytest.raises(ValidationError):
        ResourceDemandReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "node_demands": [
                    {
                        "subject_id": "nig.node.bad.0",
                        "layer_id": 0,
                        "structure_id": "structure.layer0.bad",
                        "macro_op": "BAD",
                        "phase": "other",
                        "compute_ops": -1.0,
                        "read_bytes": 0.0,
                        "write_bytes": 0.0,
                        "working_set_bytes": 0.0,
                        "dependency_depth": 0,
                    }
                ],
                "layer_demands": [],
                "structure_demands": [],
                "totals": {
                    "compute_ops": 0.0,
                    "read_bytes": 0.0,
                    "write_bytes": 0.0,
                    "working_set_bytes": 0.0,
                    "node_count": 0,
                    "layer_count": 0,
                    "structure_count": 0,
                },
                "assumptions": [],
            }
        )
