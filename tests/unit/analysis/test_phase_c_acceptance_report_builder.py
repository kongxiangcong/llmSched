from llm_sched.contracts.phase_c_acceptance_report import PhaseCAcceptanceCaseRecord


def test_build_phase_c_acceptance_report_marks_canonical_matrix_ready() -> None:
    from llm_sched.analysis import build_phase_c_acceptance_report

    report = build_phase_c_acceptance_report(
        report_name="phase-c-canonical-matrix",
        case_records=[
            _case_record("single-core", "prefill", "run-prefill-single"),
            _case_record("single-core", "decode", "run-decode-single"),
            _case_record("dual-core", "prefill", "run-prefill-dual"),
            _case_record("dual-core", "decode", "run-decode-dual"),
        ],
    )

    assert report.status == "ready_for_acceptance"
    assert report.matrix_coverage.present_case_ids == [
        "single-core:prefill",
        "single-core:decode",
        "dual-core:prefill",
        "dual-core:decode",
    ]
    assert report.matrix_coverage.missing_case_ids == []
    assert report.matrix_coverage.duplicate_case_ids == []
    assert report.matrix_coverage.ready_case_count == 4
    assert report.matrix_coverage.blocked_case_count == 0
    assert report.matrix_coverage.planner_blocked_case_count == 0
    assert report.matrix_coverage.downstream_blocked_case_count == 0
    assert report.remaining_gaps == []
    assert all(case.planner_closure_status == "ready_for_acceptance" for case in report.case_records)
    assert all(case.downstream_closure_status == "ready_for_acceptance" for case in report.case_records)


def test_build_phase_c_acceptance_report_surfaces_missing_duplicate_and_blocked_cases() -> None:
    from llm_sched.analysis import build_phase_c_acceptance_report

    report = build_phase_c_acceptance_report(
        report_name="phase-c-canonical-matrix",
        case_records=[
            _case_record("single-core", "prefill", "run-prefill-single"),
            _case_record("dual-core", "prefill", "run-prefill-dual"),
            _case_record(
                "dual-core",
                "decode",
                "run-decode-dual-a",
                closure_status="in_progress",
                planner_closure_status="in_progress",
                planner_remaining_gaps=["unresolved address diagnostics remain"],
                downstream_closure_status="in_progress",
                downstream_remaining_gaps=["visualization_packaging consumer evidence is missing"],
                verified_required_consumer_count=4,
                remaining_gaps=[
                    "planner_closure: unresolved address diagnostics remain",
                    "visualization_packaging consumer evidence is missing",
                ],
            ),
            _case_record("dual-core", "decode", "run-decode-dual-b"),
        ],
    )

    assert report.status == "in_progress"
    assert report.matrix_coverage.missing_case_ids == ["single-core:decode"]
    assert report.matrix_coverage.duplicate_case_ids == ["dual-core:decode"]
    assert report.matrix_coverage.ready_case_count == 3
    assert report.matrix_coverage.blocked_case_count == 1
    assert report.matrix_coverage.planner_blocked_case_count == 1
    assert report.matrix_coverage.downstream_blocked_case_count == 1
    assert any(issue.code == "missing_case" for issue in report.issues)
    assert any(issue.code == "duplicate_case" for issue in report.issues)
    assert any(issue.code == "closure_gap" for issue in report.issues)
    blocked_case = next(case for case in report.case_records if case.run_id == "run-decode-dual-a")
    assert blocked_case.planner_closure_status == "in_progress"
    assert blocked_case.planner_remaining_gaps == ["unresolved address diagnostics remain"]
    assert blocked_case.downstream_closure_status == "in_progress"
    assert blocked_case.downstream_remaining_gaps == [
        "visualization_packaging consumer evidence is missing"
    ]
    assert "missing canonical case: single-core:decode" in report.remaining_gaps
    assert (
        "dual-core:decode (run-decode-dual-a): planner_closure: unresolved address diagnostics remain"
        in report.remaining_gaps
    )
    assert (
        "dual-core:decode (run-decode-dual-a): visualization_packaging consumer evidence is missing"
        in report.remaining_gaps
    )


def _case_record(
    schedule_kind: str,
    mode: str,
    run_id: str,
    *,
    closure_status: str = "ready_for_acceptance",
    planner_closure_status: str = "ready_for_acceptance",
    planner_remaining_gaps: list[str] | None = None,
    downstream_closure_status: str = "ready_for_acceptance",
    downstream_remaining_gaps: list[str] | None = None,
    verified_required_consumer_count: int = 5,
    required_consumer_count: int = 5,
    remaining_gaps: list[str] | None = None,
) -> PhaseCAcceptanceCaseRecord:
    return PhaseCAcceptanceCaseRecord(
        case_id=f"{schedule_kind}:{mode}",
        run_id=run_id,
        run_root=f"tmp/{run_id}",
        scenario_name="prefill_seq128" if mode == "prefill" else "decode_token1_kv2048",
        mode=mode,
        schedule_kind=schedule_kind,
        target_profile_name=(
            "riscv_npu_single_core_v1"
            if schedule_kind == "single-core"
            else "riscv_npu_dual_core_v1"
        ),
        closure_report_path="reports/memory_planner_closure_report.json",
        closure_status=closure_status,
        planner_closure_status=planner_closure_status,
        planner_remaining_gaps=planner_remaining_gaps or [],
        downstream_closure_status=downstream_closure_status,
        downstream_remaining_gaps=downstream_remaining_gaps or [],
        verified_required_consumer_count=verified_required_consumer_count,
        required_consumer_count=required_consumer_count,
        remaining_gaps=remaining_gaps or [],
    )
