from pathlib import Path

from llm_sched.contracts.manifest import RunManifest


def test_run_diagnosis_analysis_writes_resource_demand_report_when_memory_plan_exists(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-resource-demand",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="memory",
    )

    result = run_diagnosis_analysis(run_root)

    assert result.status == "completed"
    demand_report_path = run_root / "reports" / "diagnosis" / "resource_demand_report.json"
    assert demand_report_path.is_file()

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.artifact_index["resource_demand_report"] == "reports/diagnosis/resource_demand_report.json"
