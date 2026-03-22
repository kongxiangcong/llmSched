import pytest
from pydantic import ValidationError


def test_support_matrix_report_captures_node_layer_structure_and_gap_summaries() -> None:
    from llm_sched.contracts.support_matrix_report import SupportMatrixReport

    report = SupportMatrixReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_support_entries": [
                {
                    "subject_id": "nig.node.q_proj.0",
                    "graph_node_id": "graph.node.q_proj",
                    "layer_id": 0,
                    "structure_id": "structure.layer0.attention_block",
                    "structure_kind": "attention_block",
                    "phase": "prefill",
                    "macro_op": "WDQ_GEMM",
                    "canonical_op": "matmul",
                    "support_status": "native",
                    "fallback_kind": "none",
                    "binding_issue_ids": [],
                    "legality_rule_ids": [],
                    "reason_codes": [],
                    "detail_messages": [],
                },
                {
                    "subject_id": "nig.node.rope.0",
                    "graph_node_id": "graph.node.rope",
                    "layer_id": 0,
                    "structure_id": "structure.layer0.attention_block",
                    "structure_kind": "attention_block",
                    "phase": "prefill",
                    "macro_op": "ROPE",
                    "canonical_op": "rope",
                    "support_status": "fallback",
                    "fallback_kind": "helper_only",
                    "binding_issue_ids": ["binding.rope.helper_surface"],
                    "legality_rule_ids": ["rule.rope.helper_only"],
                    "reason_codes": ["helper_only_lowering"],
                    "detail_messages": ["RoPE is currently lowered through helper surface."],
                },
            ],
            "layer_support_summary": [
                {
                    "layer_id": 0,
                    "support_status": "fallback",
                    "node_count": 2,
                    "native_count": 1,
                    "constrained_count": 0,
                    "fallback_count": 1,
                    "unsupported_count": 0,
                    "reason_codes": ["helper_only_lowering"],
                }
            ],
            "structure_support_summary": [
                {
                    "structure_id": "structure.layer0.attention_block",
                    "layer_id": 0,
                    "structure_kind": "attention_block",
                    "support_status": "fallback",
                    "node_count": 2,
                    "native_count": 1,
                    "constrained_count": 0,
                    "fallback_count": 1,
                    "unsupported_count": 0,
                    "reason_codes": ["helper_only_lowering"],
                }
            ],
            "reason_counts": {
                "helper_only_lowering": 1,
            },
            "critical_gaps": [
                {
                    "subject_id": "structure.layer0.attention_block",
                    "subject_kind": "structure",
                    "support_status": "fallback",
                    "reason_code": "helper_only_lowering",
                    "message": "Attention block still depends on helper-only RoPE lowering.",
                }
            ],
        }
    )

    assert report.node_support_entries[1].support_status == "fallback"
    assert report.node_support_entries[0].structure_kind == "attention_block"
    assert report.node_support_entries[0].phase == "prefill"
    assert report.node_support_entries[0].canonical_op == "matmul"
    assert report.node_support_entries[1].fallback_kind == "helper_only"
    assert report.node_support_entries[1].binding_issue_ids == ["binding.rope.helper_surface"]
    assert report.node_support_entries[1].legality_rule_ids == ["rule.rope.helper_only"]
    assert report.layer_support_summary[0].fallback_count == 1
    assert report.structure_support_summary[0].structure_kind == "attention_block"
    assert report.reason_counts["helper_only_lowering"] == 1
    assert report.critical_gaps[0].subject_kind == "structure"


def test_support_matrix_report_requires_reason_counts() -> None:
    from llm_sched.contracts.support_matrix_report import SupportMatrixReport

    with pytest.raises(ValidationError):
        SupportMatrixReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "node_support_entries": [],
                "layer_support_summary": [],
                "structure_support_summary": [],
                "critical_gaps": [],
            }
        )


def test_support_matrix_report_rejects_unknown_support_status() -> None:
    from llm_sched.contracts.support_matrix_report import SupportMatrixReport

    with pytest.raises(ValidationError):
        SupportMatrixReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "node_support_entries": [
                    {
                        "subject_id": "nig.node.bad.0",
                        "graph_node_id": "graph.node.bad",
                        "layer_id": 0,
                        "structure_id": "structure.layer0.bad",
                        "structure_kind": "bad_block",
                        "phase": "prefill",
                        "macro_op": "BAD",
                        "canonical_op": "bad",
                        "support_status": "mystery",
                        "fallback_kind": "none",
                        "binding_issue_ids": [],
                        "legality_rule_ids": [],
                        "reason_codes": [],
                        "detail_messages": [],
                    }
                ],
                "layer_support_summary": [],
                "structure_support_summary": [],
                "reason_counts": {},
                "critical_gaps": [],
            }
        )


def test_support_matrix_report_rejects_legacy_minimal_node_support_entry_payload() -> None:
    from llm_sched.contracts.support_matrix_report import SupportMatrixReport

    with pytest.raises(ValidationError):
        SupportMatrixReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "node_support_entries": [
                    {
                        "subject_id": "nig.node.q_proj.0",
                        "graph_node_id": "graph.node.q_proj",
                        "layer_id": 0,
                        "structure_id": "structure.layer0.attention_block",
                        "macro_op": "WDQ_GEMM",
                        "support_status": "native",
                        "reason_codes": [],
                        "detail_messages": [],
                    }
                ],
                "layer_support_summary": [],
                "structure_support_summary": [],
                "reason_counts": {},
                "critical_gaps": [],
            }
        )
