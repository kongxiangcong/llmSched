from pathlib import Path

from llm_sched.contracts.architecture_assessment_report import ArchitectureAssessmentReport
from llm_sched.contracts.manifest import RunManifest


def test_run_diagnosis_analysis_writes_architecture_assessment_report_when_inputs_exist(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis, run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-architecture-assessment",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"

    result = run_diagnosis_analysis(run_root)

    assert result.status == "completed"
    report_path = run_root / "reports" / "diagnosis" / "architecture_assessment_report.json"
    assert report_path.is_file()

    report = ArchitectureAssessmentReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    if report.overall_assessment.verdict == "unsupported":
        summary_lower = report.overall_assessment.summary.lower()
        assert "viable" not in summary_lower
        assert "runnable" not in summary_lower
    assert report.recommendations
    assert report.key_metrics
    assert report.top_realization_gaps
    assert report.recommendations[0].category in {"model", "schedule", "hardware", "compiler"}

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert (
        manifest.artifact_index["architecture_assessment_report"]
        == "reports/diagnosis/architecture_assessment_report.json"
    )
