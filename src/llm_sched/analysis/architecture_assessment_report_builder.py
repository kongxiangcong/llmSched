"""Builder for the DIAG-08 architecture assessment report."""

from __future__ import annotations

from llm_sched.contracts.architecture_assessment_report import (
    ArchitectureAssessmentReport,
    BottleneckFinding,
    ConfidenceSummary,
    OverallAssessment,
    RecommendationEntry,
    SupportGapFinding,
    TimelineLossFinding,
)
from llm_sched.contracts.performance_diagnostics_report import PerformanceDiagnosticsReport
from llm_sched.contracts.resource_demand_report import ResourceDemandReport
from llm_sched.contracts.roofline_report import RooflineReport
from llm_sched.contracts.schedule_diagnostics_report import ScheduleDiagnosticsReport
from llm_sched.contracts.support_matrix_report import SupportMatrixReport


def build_architecture_assessment_report(
    *,
    run_id: str,
    resource_demand_report: ResourceDemandReport,
    support_matrix_report: SupportMatrixReport,
    schedule_diagnostics_report: ScheduleDiagnosticsReport,
    performance_diagnostics_report: PerformanceDiagnosticsReport,
    roofline_report: RooflineReport,
) -> ArchitectureAssessmentReport:
    graph_id = resource_demand_report.graph_id
    scenario_name = resource_demand_report.scenario_name
    _validate_shared_identity(
        graph_id=graph_id,
        scenario_name=scenario_name,
        support_matrix_report=support_matrix_report,
        schedule_diagnostics_report=schedule_diagnostics_report,
        performance_diagnostics_report=performance_diagnostics_report,
        roofline_report=roofline_report,
    )

    top_bottlenecks = _build_top_bottlenecks(performance_diagnostics_report)
    top_support_gaps = _build_top_support_gaps(support_matrix_report)
    top_timeline_losses = _build_top_timeline_losses(schedule_diagnostics_report)
    recommendations = _build_recommendations(
        roofline_report=roofline_report,
        top_support_gaps=top_support_gaps,
        top_timeline_losses=top_timeline_losses,
        performance_diagnostics_report=performance_diagnostics_report,
    )
    confidence_summary = _build_confidence_summary(resource_demand_report)

    return ArchitectureAssessmentReport(
        run_id=run_id,
        graph_id=graph_id,
        scenario_name=scenario_name,
        schedule_kind=performance_diagnostics_report.schedule_kind,
        report_kind=performance_diagnostics_report.report_kind,
        overall_assessment=_build_overall_assessment(
            roofline_report=roofline_report,
            performance_diagnostics_report=performance_diagnostics_report,
            top_support_gaps=top_support_gaps,
            recommendations=recommendations,
        ),
        top_bottlenecks=top_bottlenecks,
        top_support_gaps=top_support_gaps,
        top_timeline_losses=top_timeline_losses,
        recommendations=recommendations,
        confidence_summary=confidence_summary,
    )


def _validate_shared_identity(
    *,
    graph_id: str,
    scenario_name: str,
    support_matrix_report: SupportMatrixReport,
    schedule_diagnostics_report: ScheduleDiagnosticsReport,
    performance_diagnostics_report: PerformanceDiagnosticsReport,
    roofline_report: RooflineReport,
) -> None:
    if any(
        candidate != graph_id
        for candidate in (
            support_matrix_report.graph_id,
            schedule_diagnostics_report.graph_id,
            performance_diagnostics_report.graph_id,
            roofline_report.graph_id,
        )
    ):
        raise ValueError("graph_id mismatch across DIAG-03/04/05/06/07 inputs")
    if any(
        candidate != scenario_name
        for candidate in (
            support_matrix_report.scenario_name,
            schedule_diagnostics_report.scenario_name,
            performance_diagnostics_report.scenario_name,
            roofline_report.scenario_name,
        )
    ):
        raise ValueError("scenario_name mismatch across DIAG-03/04/05/06/07 inputs")


def _build_top_bottlenecks(
    performance_diagnostics_report: PerformanceDiagnosticsReport,
) -> list[BottleneckFinding]:
    return [
        BottleneckFinding(
            subject_id=row.node_id,
            subject_kind="node",
            bottleneck=row.bound_kind,
            severity="high" if index == 0 else "medium",
            estimated_cycles=row.estimated_cycles,
            share=row.cycle_share,
            message=(f"{row.node_id} is a top hotspot under {row.bound_kind or 'unknown'} pressure."),
        )
        for index, row in enumerate(
            sorted(
                performance_diagnostics_report.node_hotspots,
                key=lambda item: (-item.fitted_work_cycles, -item.estimated_cycles, item.node_id),
            )[:3]
        )
    ]


def _build_top_support_gaps(
    support_matrix_report: SupportMatrixReport,
) -> list[SupportGapFinding]:
    severity_order = {"unsupported": 0, "fallback": 1, "constrained": 2, "native": 3}
    return [
        SupportGapFinding(
            subject_id=row.subject_id,
            subject_kind=row.subject_kind,
            support_status=row.support_status,
            reason_code=row.reason_code,
            severity="high" if row.support_status in {"unsupported", "fallback"} else "medium",
            message=row.message,
        )
        for row in sorted(
            support_matrix_report.critical_gaps,
            key=lambda item: (
                severity_order[item.support_status],
                item.subject_kind,
                item.subject_id,
            ),
        )[:3]
    ]


def _build_top_timeline_losses(
    schedule_diagnostics_report: ScheduleDiagnosticsReport,
) -> list[TimelineLossFinding]:
    findings: list[TimelineLossFinding] = []
    for row in schedule_diagnostics_report.stall_events:
        findings.append(
            TimelineLossFinding(
                subject_id=row.block_id,
                subject_kind="block",
                loss_kind=row.reason,
                severity="high" if row.span_slots >= 8 else "medium",
                lost_cycles=float(row.span_slots),
                message=f"{row.block_id} stalls on {row.reason}.",
            )
        )
    for row in schedule_diagnostics_report.idle_spans:
        findings.append(
            TimelineLossFinding(
                subject_id=row.following_block_id or row.preceding_block_id or f"core.{row.core_id}",
                subject_kind="block" if row.following_block_id or row.preceding_block_id else "core",
                loss_kind=row.reason,
                severity="medium",
                lost_cycles=float(row.span_slots),
                message=f"Idle span caused by {row.reason}.",
            )
        )
    return sorted(
        findings,
        key=lambda item: (-item.lost_cycles, item.subject_kind, item.subject_id),
    )[:3]


def _build_recommendations(
    *,
    roofline_report: RooflineReport,
    top_support_gaps: list[SupportGapFinding],
    top_timeline_losses: list[TimelineLossFinding],
    performance_diagnostics_report: PerformanceDiagnosticsReport,
) -> list[RecommendationEntry]:
    recommendations: list[RecommendationEntry] = []
    unsupported_gaps = [gap for gap in top_support_gaps if gap.support_status == "unsupported"]

    if unsupported_gaps:
        recommendations.append(
            RecommendationEntry(
                recommendation_id="rec.model.remove-blocking-support-gap",
                priority=1,
                category="model",
                title="Remove blocking unsupported structures",
                action="Remove unsupported structures from the hottest path before schedule generation.",
                rationale=unsupported_gaps[0].message,
            )
        )
        recommendations.append(
            RecommendationEntry(
                recommendation_id="rec.compiler.close-unsupported-lowering-gap",
                priority=2,
                category="compiler",
                title="Close unsupported lowering gaps",
                action="Add or enable compiler lowerings for the blocking unsupported structures.",
                rationale=unsupported_gaps[0].message,
            )
        )
    elif top_support_gaps:
        recommendations.append(
            RecommendationEntry(
                recommendation_id="rec.model.reduce-support-gaps",
                priority=1,
                category="model",
                title="Reduce support gaps",
                action="Reduce fallback-only structures on the hottest path.",
                rationale=top_support_gaps[0].message,
            )
        )

    next_priority = len(recommendations) + 1
    recommendations.append(
        RecommendationEntry(
            recommendation_id="rec.hardware.target-dominant-bound",
            priority=next_priority,
            category="hardware",
            title="Target dominant roofline bound",
            action=f"Focus next hardware change on the {roofline_report.dominant_bound_summary.dominant_bound} ceiling.",
            rationale=(
                f"Roofline summary is dominated by {roofline_report.dominant_bound_summary.dominant_bound} limits."
            ),
        )
    )
    if top_timeline_losses:
        recommendations.append(
            RecommendationEntry(
                recommendation_id="rec.schedule.absorb-timeline-losses",
                priority=len(recommendations) + 1,
                category="schedule",
                title="Reduce timeline losses",
                action="Increase overlap or rebalance issue order around the largest observed stall spans.",
                rationale=top_timeline_losses[0].message,
            )
        )
    return recommendations


def _build_confidence_summary(
    resource_demand_report: ResourceDemandReport,
) -> ConfidenceSummary:
    assumption_ids = [entry.assumption_id for entry in resource_demand_report.assumptions]
    return ConfidenceSummary(
        confidence_level="medium",
        evidence_count=5,
        assumption_ids=assumption_ids,
        warning_messages=(
            ["Assessment inherits approximate demand/ceiling assumptions from upstream diagnosis reports."]
            if assumption_ids
            else []
        ),
    )


def _build_overall_assessment(
    *,
    roofline_report: RooflineReport,
    performance_diagnostics_report: PerformanceDiagnosticsReport,
    top_support_gaps: list[SupportGapFinding],
    recommendations: list[RecommendationEntry],
) -> OverallAssessment:
    unsupported_gaps = [row for row in top_support_gaps if row.support_status == "unsupported"]
    fallback_gaps = [row for row in top_support_gaps if row.support_status == "fallback"]

    if unsupported_gaps:
        verdict = "unsupported"
        assessment_basis = "support_blocking_gap"
    elif fallback_gaps or roofline_report.dominant_bound_summary.dominant_bound == "bandwidth":
        verdict = "constrained_fit"
        assessment_basis = "support_then_performance"
    else:
        verdict = "good_fit"
        assessment_basis = "performance_then_roofline"

    primary_recommendation = recommendations[0].action if recommendations else "Keep current configuration."
    blocking_reasons = [row.message for row in unsupported_gaps]
    top_unsupported_structures = [
        row.subject_id for row in unsupported_gaps if row.subject_kind == "structure"
    ]
    top_fallback_structures = [
        row.subject_id for row in fallback_gaps if row.subject_kind == "structure"
    ]

    if verdict == "unsupported":
        summary = "The current target cannot execute the model as intended because blocking support gaps remain on the hottest path."
    elif verdict == "constrained_fit":
        summary = (
            "The target can run the model, but support gaps and dominant performance limits still constrain throughput."
        )
    else:
        summary = "The current target/model pairing looks viable under the available diagnosis evidence."

    return OverallAssessment(
        verdict=verdict,
        summary=summary,
        dominant_bound=roofline_report.dominant_bound_summary.dominant_bound,
        dominant_bottleneck=performance_diagnostics_report.bottleneck_classification.dominant_bottleneck,
        blocking_reasons=blocking_reasons,
        top_unsupported_structures=top_unsupported_structures,
        top_fallback_structures=top_fallback_structures,
        assessment_basis=assessment_basis,
        primary_recommendation=primary_recommendation,
    )
