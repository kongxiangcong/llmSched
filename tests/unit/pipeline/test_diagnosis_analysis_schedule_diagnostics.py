from pathlib import Path

from llm_sched.contracts.manifest import RunManifest


def test_run_diagnosis_analysis_writes_schedule_diagnostics_report_when_schedule_inputs_exist(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-schedule-diagnostics",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="descriptor",
    )

    result = run_diagnosis_analysis(run_root)

    assert result.status == "completed"
    report_path = run_root / "reports" / "diagnosis" / "schedule_diagnostics_report.json"
    assert report_path.is_file()

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert (
        manifest.artifact_index["schedule_diagnostics_report"]
        == "reports/diagnosis/schedule_diagnostics_report.json"
    )
