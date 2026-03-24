import pytest
from pydantic import ValidationError


def test_diagnosis_chain_summary_accepts_stage_chain() -> None:
    from llm_sched.contracts.diagnosis_chain_summary import DiagnosisChainSummary

    summary = DiagnosisChainSummary.model_validate(
        {
            "run_id": "run-001",
            "graph_id": "graph::demo",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "single-core",
            "report_kind": "prefill",
            "stage_chain": [
                {
                    "stage": "model_structure",
                    "headline": "26 layers, 80 structures",
                    "key_facts": {"total_layers": 26, "total_structures": 80},
                },
                {
                    "stage": "assessment",
                    "headline": "unsupported due to support gaps",
                    "key_facts": {"verdict": "unsupported", "recommendation_count": 2},
                },
            ],
        }
    )

    assert summary.stage_chain[0].stage == "model_structure"
    assert summary.stage_chain[1].key_facts["recommendation_count"] == 2


def test_diagnosis_chain_summary_rejects_missing_stage_chain() -> None:
    from llm_sched.contracts.diagnosis_chain_summary import DiagnosisChainSummary

    with pytest.raises(ValidationError):
        DiagnosisChainSummary.model_validate(
            {
                "run_id": "run-001",
                "graph_id": "graph::demo",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "single-core",
                "report_kind": "prefill",
            }
        )
