"""Builder for cross-run Phase C acceptance evidence."""

from collections import Counter

from llm_sched.contracts.phase_c_acceptance_report import (
    CANONICAL_PHASE_C_CASE_IDS,
    PhaseCAcceptanceCaseRecord,
    PhaseCAcceptanceIssue,
    PhaseCAcceptanceMatrixCoverage,
    PhaseCAcceptanceReport,
)


def build_phase_c_acceptance_report(
    *,
    report_name: str,
    case_records: list[PhaseCAcceptanceCaseRecord],
) -> PhaseCAcceptanceReport:
    sorted_case_records = sorted(
        case_records,
        key=lambda record: (
            CANONICAL_PHASE_C_CASE_IDS.index(record.case_id),
            record.run_id,
        ),
    )
    case_counts = Counter(record.case_id for record in sorted_case_records)
    present_case_ids = [
        case_id for case_id in CANONICAL_PHASE_C_CASE_IDS if case_counts.get(case_id, 0) > 0
    ]
    missing_case_ids = [
        case_id for case_id in CANONICAL_PHASE_C_CASE_IDS if case_counts.get(case_id, 0) == 0
    ]
    duplicate_case_ids = [
        case_id for case_id in CANONICAL_PHASE_C_CASE_IDS if case_counts.get(case_id, 0) > 1
    ]
    ready_case_count = sum(
        1 for record in sorted_case_records if record.closure_status == "ready_for_acceptance"
    )
    blocked_case_count = len(sorted_case_records) - ready_case_count
    planner_blocked_case_count = sum(
        1
        for record in sorted_case_records
        if record.planner_closure_status != "ready_for_acceptance"
    )
    downstream_blocked_case_count = sum(
        1
        for record in sorted_case_records
        if record.downstream_closure_status != "ready_for_acceptance"
    )

    issues: list[PhaseCAcceptanceIssue] = []
    remaining_gaps: list[str] = []

    for case_id in missing_case_ids:
        issues.append(
            PhaseCAcceptanceIssue(
                code="missing_case",
                case_id=case_id,
                message=f"{case_id} is missing from the canonical Phase C matrix",
            )
        )
        remaining_gaps.append(f"missing canonical case: {case_id}")

    for case_id in duplicate_case_ids:
        issues.append(
            PhaseCAcceptanceIssue(
                code="duplicate_case",
                case_id=case_id,
                message=f"{case_id} appears more than once in the canonical Phase C matrix",
            )
        )
        remaining_gaps.append(f"duplicate canonical case: {case_id}")

    for record in sorted_case_records:
        if record.closure_status == "ready_for_acceptance":
            continue
        gaps = record.remaining_gaps or [
            "required downstream consumers are not yet fully verified"
        ]
        for gap in gaps:
            issues.append(
                PhaseCAcceptanceIssue(
                    code="closure_gap",
                    case_id=record.case_id,
                    run_id=record.run_id,
                    message=f"{record.run_id} is still missing {gap}",
                )
            )
            remaining_gaps.append(f"{record.case_id} ({record.run_id}): {gap}")

    status = "ready_for_acceptance"
    if missing_case_ids or duplicate_case_ids or blocked_case_count > 0:
        status = "in_progress"

    return PhaseCAcceptanceReport(
        report_name=report_name,
        status=status,
        matrix_coverage=PhaseCAcceptanceMatrixCoverage(
            expected_case_ids=list(CANONICAL_PHASE_C_CASE_IDS),
            present_case_ids=present_case_ids,
            missing_case_ids=missing_case_ids,
            duplicate_case_ids=duplicate_case_ids,
            ready_case_count=ready_case_count,
            blocked_case_count=blocked_case_count,
            planner_blocked_case_count=planner_blocked_case_count,
            downstream_blocked_case_count=downstream_blocked_case_count,
        ),
        case_records=sorted_case_records,
        issues=issues,
        remaining_gaps=remaining_gaps,
    )
