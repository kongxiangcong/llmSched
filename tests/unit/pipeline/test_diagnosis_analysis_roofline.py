from pathlib import Path

from llm_sched.contracts.manifest import RunManifest


def test_run_diagnosis_analysis_writes_roofline_report_when_roofline_inputs_exist(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis, run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-roofline",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"

    result = run_diagnosis_analysis(run_root)

    assert result.status == "completed"
    report_path = run_root / "reports" / "diagnosis" / "roofline_report.json"
    assert report_path.is_file()

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.artifact_index["roofline_report"] == "reports/diagnosis/roofline_report.json"
