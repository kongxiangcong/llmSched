from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.performance_diagnostics_report import PerformanceDiagnosticsReport


def test_run_diagnosis_analysis_writes_performance_diagnostics_report_when_perf_inputs_exist(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis, run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-performance-diagnostics",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"

    result = run_diagnosis_analysis(run_root)

    assert result.status == "completed"
    report_path = run_root / "reports" / "diagnosis" / "performance_diagnostics_report.json"
    assert report_path.is_file()

    report = PerformanceDiagnosticsReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    assert len(report.node_hotspots) > 0
    assert report.node_hotspots[0].graph_node_id
    assert report.node_hotspots[0].structure_id
    assert report.node_hotspots[0].phase
    assert report.node_hotspots[0].macro_op
    assert report.node_hotspots[0].bound_kind in {
        "compute_bound",
        "bandwidth_bound",
        "vmem_bound",
        "sync_bound",
        "fallback_bound",
    }
    assert report.bottleneck_classification.dominant_bottleneck in {
        "compute_bound",
        "bandwidth_bound",
        "vmem_bound",
        "sync_bound",
        "fallback_bound",
        "",
    }

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert (
        manifest.artifact_index["performance_diagnostics_report"]
        == "reports/diagnosis/performance_diagnostics_report.json"
    )
