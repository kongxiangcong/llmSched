from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_diagnosis_packaging_writes_bundle_and_updates_manifest(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle
    from llm_sched.pipeline import (
        run_diagnosis_analysis,
        run_diagnosis_packaging,
        run_prefill_evaluation,
    )

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-packaging",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"
    assert run_diagnosis_analysis(run_root).status == "completed"

    result = run_diagnosis_packaging(run_root)

    assert result.status == "completed"
    assert result.bundle_path == run_root / "reports" / "diagnosis_bundle.json"

    bundle = DiagnosisBundle.model_validate_json(result.bundle_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert bundle.metadata.run_id == "run-diagnosis-packaging"
    assert bundle.report_references["roofline_report"] == "reports/diagnosis/roofline_report.json"
    assert "assessment" in bundle.available_panels
    assert manifest.artifact_index["diagnosis_bundle"] == "reports/diagnosis_bundle.json"
    assert summary.status == "completed"
    assert summary.exit_code == 0


def test_run_diagnosis_packaging_rejects_missing_diagnosis_reports(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_diagnosis_packaging

    run_root = tmp_path / "run-diagnosis-packaging-missing"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "manifest.json").write_text(
        RunManifest(
            run_id="run-diagnosis-packaging-missing",
            contract_version="phase-a.v1",
            status="initialized",
            model_path="model.onnx",
            target_profile_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_profile_path="profiles/scenarios/prefill_seq128.json",
            artifact_index={"reports_dir": "reports"},
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )

    result = run_diagnosis_packaging(run_root)

    assert result.status == "failed"
    assert result.bundle_path is None
    assert "diagnosis" in result.diagnostics[0].message.lower()
