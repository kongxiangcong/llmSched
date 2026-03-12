import pytest
from pydantic import ValidationError


def test_phase_c_acceptance_case_record_requires_matching_case_id() -> None:
    from llm_sched.contracts.phase_c_acceptance_report import PhaseCAcceptanceCaseRecord

    with pytest.raises(ValidationError):
        PhaseCAcceptanceCaseRecord.model_validate(
            {
                "case_id": "dual-core:decode",
                "run_id": "run-prefill-single",
                "run_root": "tmp/run-prefill-single",
                "scenario_name": "prefill_seq128",
                "mode": "prefill",
                "schedule_kind": "single-core",
                "target_profile_name": "riscv_npu_single_core_v1",
                "closure_report_path": "reports/memory_planner_closure_report.json",
                "closure_status": "ready_for_acceptance",
                "planner_closure_status": "ready_for_acceptance",
                "planner_remaining_gaps": [],
                "downstream_closure_status": "ready_for_acceptance",
                "downstream_remaining_gaps": [],
                "downstream_missing_consumers": [],
                "verified_required_consumer_count": 5,
                "required_consumer_count": 5,
                "remaining_gaps": [],
            }
        )


def test_phase_c_acceptance_report_tracks_matrix_coverage_and_issues() -> None:
    from llm_sched.contracts.phase_c_acceptance_report import PhaseCAcceptanceReport

    report = PhaseCAcceptanceReport.model_validate(
        {
            "report_name": "phase-c-canonical-matrix",
            "status": "in_progress",
            "matrix_coverage": {
                "expected_case_ids": [
                    "single-core:prefill",
                    "single-core:decode",
                    "dual-core:prefill",
                    "dual-core:decode",
                ],
                "present_case_ids": [
                    "single-core:prefill",
                    "dual-core:prefill",
                    "dual-core:decode",
                ],
                "missing_case_ids": ["single-core:decode"],
                "duplicate_case_ids": ["dual-core:decode"],
                "ready_case_count": 2,
                "blocked_case_count": 2,
                "planner_blocked_case_count": 1,
                "downstream_blocked_case_count": 1,
            },
            "case_records": [
                {
                    "case_id": "single-core:prefill",
                    "run_id": "run-prefill-single",
                    "run_root": "tmp/run-prefill-single",
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "schedule_kind": "single-core",
                    "target_profile_name": "riscv_npu_single_core_v1",
                    "closure_report_path": "reports/memory_planner_closure_report.json",
                    "closure_status": "ready_for_acceptance",
                    "planner_closure_status": "ready_for_acceptance",
                    "planner_remaining_gaps": [],
                    "downstream_closure_status": "ready_for_acceptance",
                    "downstream_remaining_gaps": [],
                    "downstream_missing_consumers": [],
                    "verified_required_consumer_count": 5,
                    "required_consumer_count": 5,
                    "remaining_gaps": [],
                },
                {
                    "case_id": "dual-core:decode",
                    "run_id": "run-decode-dual-a",
                    "run_root": "tmp/run-decode-dual-a",
                    "scenario_name": "decode_token1_kv2048",
                    "mode": "decode",
                    "schedule_kind": "dual-core",
                    "target_profile_name": "riscv_npu_dual_core_v1",
                    "closure_report_path": "reports/memory_planner_closure_report.json",
                    "closure_status": "in_progress",
                    "planner_closure_status": "in_progress",
                    "planner_remaining_gaps": [
                        "unresolved address diagnostics remain",
                    ],
                    "downstream_closure_status": "in_progress",
                    "downstream_remaining_gaps": ["required downstream evidence missing"],
                    "downstream_missing_consumers": ["visualization_packaging"],
                    "verified_required_consumer_count": 4,
                    "required_consumer_count": 5,
                    "remaining_gaps": [
                        "planner_closure: unresolved address diagnostics remain",
                        "required downstream evidence missing",
                    ],
                },
            ],
            "issues": [
                {
                    "code": "missing_case",
                    "case_id": "single-core:decode",
                    "message": "single-core:decode is missing from the canonical Phase C matrix",
                },
                {
                    "code": "duplicate_case",
                    "case_id": "dual-core:decode",
                    "message": "dual-core:decode appears more than once in the canonical Phase C matrix",
                },
                {
                    "code": "closure_gap",
                    "case_id": "dual-core:decode",
                    "run_id": "run-decode-dual-a",
                    "message": "run-decode-dual-a is still missing visualization_packaging consumer evidence",
                },
            ],
            "remaining_gaps": [
                "missing canonical case: single-core:decode",
                "duplicate canonical case: dual-core:decode",
                "dual-core:decode (run-decode-dual-a): visualization_packaging consumer evidence is missing",
            ],
        }
    )

    assert report.matrix_coverage.missing_case_ids == ["single-core:decode"]
    assert report.matrix_coverage.duplicate_case_ids == ["dual-core:decode"]
    assert report.matrix_coverage.planner_blocked_case_count == 1
    assert report.matrix_coverage.downstream_blocked_case_count == 1
    assert report.case_records[1].planner_closure_status == "in_progress"
    assert report.case_records[1].planner_remaining_gaps == [
        "unresolved address diagnostics remain"
    ]
    assert report.case_records[1].downstream_closure_status == "in_progress"
    assert report.case_records[1].downstream_remaining_gaps == ["required downstream evidence missing"]
    assert report.case_records[1].downstream_missing_consumers == ["visualization_packaging"]
    assert report.issues[2].run_id == "run-decode-dual-a"
    assert "visualization_packaging" in report.remaining_gaps[2]
