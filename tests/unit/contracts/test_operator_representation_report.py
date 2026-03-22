import pytest
from pydantic import ValidationError


def test_operator_representation_report_captures_mapping_groups_and_traceability() -> None:
    from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport

    report = OperatorRepresentationReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_mappings": [
                {
                    "graph_node_id": "graph.node.q_proj",
                    "canonical_op": "MatMul",
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "normalized_node_id": "nig.node.q_proj.0",
                    "schedule_block_ids": ["sched.block.q_proj"],
                    "descriptor_ids": ["desc.q_proj.0"],
                    "fallback_kind": None,
                    "helper_surface": False,
                },
                {
                    "graph_node_id": "graph.node.rope",
                    "canonical_op": "RoPE",
                    "macro_op": "ROPE",
                    "phase": "attention",
                    "normalized_node_id": "nig.node.rope.0",
                    "schedule_block_ids": [],
                    "descriptor_ids": [],
                    "fallback_kind": "helper",
                    "helper_surface": True,
                },
            ],
            "macro_groups": [
                {
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "normalized_node_ids": ["nig.node.q_proj.0"],
                    "graph_node_ids": ["graph.node.q_proj"],
                    "schedule_block_ids": ["sched.block.q_proj"],
                },
                {
                    "macro_op": "ROPE",
                    "phase": "attention",
                    "normalized_node_ids": ["nig.node.rope.0"],
                    "graph_node_ids": ["graph.node.rope"],
                    "schedule_block_ids": [],
                },
            ],
            "phase_groups": [
                {
                    "phase": "projection",
                    "macro_ops": ["WDQ_GEMM"],
                    "normalized_node_ids": ["nig.node.q_proj.0"],
                    "graph_node_ids": ["graph.node.q_proj"],
                },
                {
                    "phase": "attention",
                    "macro_ops": ["ROPE"],
                    "normalized_node_ids": ["nig.node.rope.0"],
                    "graph_node_ids": ["graph.node.rope"],
                },
            ],
            "fallback_entries": [
                {
                    "graph_node_id": "graph.node.rope",
                    "normalized_node_id": "nig.node.rope.0",
                    "macro_op": "ROPE",
                    "phase": "attention",
                    "fallback_kind": "helper",
                    "reason": "helper-only lowering",
                }
            ],
            "traceability_index": [
                {
                    "graph_node_id": "graph.node.q_proj",
                    "normalized_node_id": "nig.node.q_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "schedule_block_ids": ["sched.block.q_proj"],
                    "descriptor_ids": ["desc.q_proj.0"],
                }
            ],
        }
    )

    assert report.node_mappings[0].macro_op == "WDQ_GEMM"
    assert report.node_mappings[1].helper_surface is True
    assert report.macro_groups[0].schedule_block_ids == ["sched.block.q_proj"]
    assert report.phase_groups[1].phase == "attention"
    assert report.fallback_entries[0].fallback_kind == "helper"
    assert report.traceability_index[0].descriptor_ids == ["desc.q_proj.0"]


def test_operator_representation_report_requires_traceability_index() -> None:
    from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport

    with pytest.raises(ValidationError):
        OperatorRepresentationReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "node_mappings": [],
                "macro_groups": [],
                "phase_groups": [],
                "fallback_entries": [],
            }
        )


def test_operator_representation_report_rejects_unknown_fallback_kind() -> None:
    from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport

    with pytest.raises(ValidationError):
        OperatorRepresentationReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "node_mappings": [
                    {
                        "graph_node_id": "graph.node.bad",
                        "canonical_op": "CustomOp",
                        "macro_op": "CUSTOM",
                        "phase": "other",
                        "normalized_node_id": "nig.node.bad.0",
                        "schedule_block_ids": [],
                        "descriptor_ids": [],
                        "fallback_kind": "mystery",
                        "helper_surface": False,
                    }
                ],
                "macro_groups": [],
                "phase_groups": [],
                "fallback_entries": [],
                "traceability_index": [],
            }
        )
