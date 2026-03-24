import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_diagnosis_analysis_reserves_diagnosis_output_directory(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-skeleton",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="frontend",
    )

    result = run_diagnosis_analysis(run_root)

    diagnosis_dir = run_root / "reports" / "diagnosis"
    trace_dir = diagnosis_dir / "trace"
    dataset_dir = diagnosis_dir / "dataset"
    assert result.status == "completed"
    assert result.diagnosis_reports_dir == diagnosis_dir
    assert diagnosis_dir.is_dir()
    assert trace_dir.is_dir()
    assert dataset_dir.is_dir()

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert manifest.status == "completed"
    assert manifest.artifact_index["diagnosis_reports_dir"] == "reports/diagnosis"
    assert manifest.artifact_index["diagnosis_trace_dir"] == "reports/diagnosis/trace"
    assert manifest.artifact_index["diagnosis_dataset_dir"] == "reports/diagnosis/dataset"
    assert manifest.artifact_index["model_structure_report"] == "reports/diagnosis/model_structure_report.json"
    assert (
        manifest.artifact_index["operator_representation_report"]
        == "reports/diagnosis/operator_representation_report.json"
    )
    assert (diagnosis_dir / "model_structure_report.json").is_file()
    assert (diagnosis_dir / "operator_representation_report.json").is_file()
    assert (trace_dir / "model_structure_report.json").is_file()
    assert (trace_dir / "operator_representation_report.json").is_file()
    root_model = json.loads((diagnosis_dir / "model_structure_report.json").read_text(encoding="utf-8"))
    trace_model = json.loads((trace_dir / "model_structure_report.json").read_text(encoding="utf-8"))
    assert root_model["node_index"] == []
    assert trace_model["node_index"]
    assert summary.status == "completed"
    assert summary.exit_code == 0


def test_run_diagnosis_analysis_rejects_missing_manifest(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis

    run_root = tmp_path / "run-diagnosis-missing-manifest"
    run_root.mkdir(parents=True, exist_ok=True)

    result = run_diagnosis_analysis(run_root)

    assert result.status == "failed"
    assert result.diagnosis_reports_dir is None
    assert "manifest" in result.diagnostics[0].message.lower()
