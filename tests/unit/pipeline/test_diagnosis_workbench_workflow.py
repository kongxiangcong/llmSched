import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_diagnosis_workbench_writes_assets_and_updates_manifest(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.contracts.diagnosis_workbench import DiagnosisWorkbenchArtifact
    from llm_sched.pipeline import (
        run_diagnosis_analysis,
        run_diagnosis_packaging,
        run_diagnosis_workbench,
        run_prefill_evaluation,
    )

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-workbench",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"
    assert run_diagnosis_analysis(run_root).status == "completed"
    assert run_diagnosis_packaging(run_root).status == "completed"

    result = run_diagnosis_workbench(run_root)

    assert result.status == "completed"
    assert result.entry_html_path == run_root / "diagnosis_workbench" / "index.html"
    assert result.workbench_manifest_path == run_root / "diagnosis_workbench" / "workbench_manifest.json"

    workbench = DiagnosisWorkbenchArtifact.model_validate_json(
        result.workbench_manifest_path.read_text(encoding="utf-8")
    )
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))
    app_js = (run_root / "diagnosis_workbench" / "assets" / "app.js").read_text(encoding="utf-8")

    assert workbench.bundle_path == "../reports/diagnosis_bundle.json"
    assert "roofline" in workbench.available_panels
    assert workbench.deep_links["assessment"] == "#/assessment"
    assert manifest.artifact_index["diagnosis_workbench_entry"] == "diagnosis_workbench/index.html"
    assert (
        manifest.artifact_index["diagnosis_workbench_manifest"]
        == "diagnosis_workbench/workbench_manifest.json"
    )
    assert summary.status == "completed"
    assert summary.exit_code == 0
    assert "function syncPanelFromHash" in app_js
    assert "function exportCurrentPanelJson" in app_js
    assert "function exportCurrentPanelSvg" in app_js


def test_run_diagnosis_workbench_rejects_missing_bundle(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_diagnosis_workbench

    run_root = tmp_path / "run-diagnosis-workbench-missing"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "manifest.json").write_text(
        RunManifest(
            run_id="run-diagnosis-workbench-missing",
            contract_version="phase-a.v1",
            status="initialized",
            model_path="model.onnx",
            target_profile_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_profile_path="profiles/scenarios/prefill_seq128.json",
            artifact_index={"reports_dir": "reports"},
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(
            RunSummary(
                run_id="run-diagnosis-workbench-missing",
                status="initialized",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_diagnosis_workbench(run_root)

    assert result.status == "failed"
    assert result.entry_html_path is None
    assert result.workbench_manifest_path is None
    assert "diagnosis_bundle" in result.diagnostics[0].message
