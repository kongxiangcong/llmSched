import pytest
from pydantic import ValidationError


def test_architecture_assessment_report_captures_assessment_bottlenecks_gaps_losses_recommendations_and_confidence() -> None:
    from llm_sched.contracts.architecture_assessment_report import ArchitectureAssessmentReport

    report = ArchitectureAssessmentReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "dual-core",
            "report_kind": "prefill",
            "overall_assessment": {
                "verdict": "constrained_fit",
                "summary": "The target can execute the model, but helper surfaces and bandwidth ceilings still constrain throughput.",
                "dominant_bound": "bandwidth",
                "dominant_bottleneck": "compute-bound",
                "blocking_reasons": [],
                "top_unsupported_structures": [],
                "top_fallback_structures": ["structure.layer0.attention_block"],
                "assessment_basis": "support_then_performance",
                "primary_recommendation": "Reduce helper-surface attention preprocessing or increase effective external bandwidth.",
            },
            "top_bottlenecks": [
                {
                    "subject_id": "nig.node.q_proj.0",
                    "subject_kind": "node",
                    "bottleneck": "compute-bound",
                    "severity": "high",
                    "estimated_cycles": 768.0,
                    "share": 0.75,
                    "message": "Projection GEMM dominates fitted work cycles.",
                }
            ],
            "top_support_gaps": [
                {
                    "subject_id": "structure.layer0.attention_block",
                    "subject_kind": "structure",
                    "support_status": "fallback",
                    "reason_code": "helper_only_lowering",
                    "severity": "high",
                    "message": "Attention block still depends on helper-only RoPE lowering.",
                }
            ],
            "top_timeline_losses": [
                {
                    "subject_id": "sched.block.q_proj.compute",
                    "subject_kind": "block",
                    "loss_kind": "dependency_wait",
                    "severity": "medium",
                    "lost_cycles": 96.0,
                    "message": "Projection compute waits on upstream DMA completion.",
                }
            ],
            "recommendations": [
                {
                    "recommendation_id": "rec.reduce-helper-surface",
                    "priority": 1,
                    "category": "model",
                    "title": "Reduce helper-surface preprocessing",
                    "action": "Fuse or lower RoPE/attention prep onto native op paths before schedule generation.",
                    "rationale": "This removes fallback pressure that propagates into schedule stalls and bandwidth limits.",
                }
            ],
            "confidence_summary": {
                "confidence_level": "medium",
                "evidence_count": 4,
                "assumption_ids": [
                    "approx.compute_ops.from_shape_volume",
                    "roofline.bytes_per_cycle.from_gbps",
                ],
                "warning_messages": [
                    "Roofline ceilings are normalized to bytes-per-cycle from target-profile Gbps.",
                ],
            },
        }
    )

    assert report.overall_assessment.verdict == "constrained_fit"
    assert report.overall_assessment.top_fallback_structures == ["structure.layer0.attention_block"]
    assert report.overall_assessment.assessment_basis == "support_then_performance"
    assert report.top_bottlenecks[0].bottleneck == "compute-bound"
    assert report.top_support_gaps[0].support_status == "fallback"
    assert report.top_timeline_losses[0].loss_kind == "dependency_wait"
    assert report.recommendations[0].priority == 1
    assert report.confidence_summary.confidence_level == "medium"


def test_architecture_assessment_report_requires_confidence_summary() -> None:
    from llm_sched.contracts.architecture_assessment_report import ArchitectureAssessmentReport

    with pytest.raises(ValidationError):
        ArchitectureAssessmentReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "prefill",
                "overall_assessment": {
                    "verdict": "good_fit",
                    "summary": "Looks good.",
                    "dominant_bound": "compute",
                    "dominant_bottleneck": "compute-bound",
                    "primary_recommendation": "Keep current mapping.",
                },
                "top_bottlenecks": [],
                "top_support_gaps": [],
                "top_timeline_losses": [],
                "recommendations": [],
            }
        )


def test_architecture_assessment_report_rejects_unknown_verdict() -> None:
    from llm_sched.contracts.architecture_assessment_report import ArchitectureAssessmentReport

    with pytest.raises(ValidationError):
        ArchitectureAssessmentReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "prefill",
                "overall_assessment": {
                    "verdict": "mystery_fit",
                    "summary": "Unknown verdict.",
                    "dominant_bound": "compute",
                    "dominant_bottleneck": "compute-bound",
                    "primary_recommendation": "None.",
                },
                "top_bottlenecks": [],
                "top_support_gaps": [],
                "top_timeline_losses": [],
                "recommendations": [],
                "confidence_summary": {
                    "confidence_level": "low",
                    "evidence_count": 0,
                    "assumption_ids": [],
                    "warning_messages": [],
                },
            }
        )


def test_architecture_assessment_report_rejects_unsupported_verdict_with_viable_summary() -> None:
    from llm_sched.contracts.architecture_assessment_report import ArchitectureAssessmentReport

    with pytest.raises(ValidationError):
        ArchitectureAssessmentReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "prefill",
                "overall_assessment": {
                    "verdict": "unsupported",
                    "summary": "The target appears viable with only minor tuning.",
                    "dominant_bound": "compute",
                    "dominant_bottleneck": "fallback-bound",
                    "blocking_reasons": ["unsupported attention path"],
                    "top_unsupported_structures": ["structure.layer0.attention_block"],
                    "top_fallback_structures": [],
                    "assessment_basis": "support_blocking_gap",
                    "primary_recommendation": "Remove unsupported attention helper path.",
                },
                "top_bottlenecks": [],
                "top_support_gaps": [],
                "top_timeline_losses": [],
                "recommendations": [],
                "confidence_summary": {
                    "confidence_level": "medium",
                    "evidence_count": 2,
                    "assumption_ids": [],
                    "warning_messages": [],
                },
            }
        )
