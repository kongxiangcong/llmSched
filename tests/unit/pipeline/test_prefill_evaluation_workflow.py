from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_prefill_evaluation_writes_report_and_updates_manifest(
    tmp_path: Path,
    minimal_performance_run_root_factory,
) -> None:
    from llm_sched.contracts.prefill_report import PrefillEvaluationReport
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = minimal_performance_run_root_factory(
        target_run_root=tmp_path / "run-prefill-eval",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )

    result = run_prefill_evaluation(run_root)

    assert result.status == "completed"
    assert result.report_path == run_root / "reports" / "prefill_evaluation_report.json"

    report = PrefillEvaluationReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert report.scenario_name == "prefill_seq128"
    assert report.throughput.estimated_cycles > 0.0
    assert report.throughput.critical_path_cycles > 0.0
    assert report.throughput.projection_bytes > 0.0
    assert report.throughput.attention_bytes >= 0.0
    assert report.throughput.other_bytes >= 0.0
    assert report.throughput.tokens_per_critical_path_cycle > 0.0
    assert report.throughput.phase_attribution["projection"].cycles_per_token > 0.0
    assert report.throughput.phase_attribution["attention"].bytes_per_token >= 0.0
    assert report.throughput.phase_attribution["projection"].occupied_slots > 0.0
    assert report.throughput.phase_attribution["other"].occupied_slots_per_token >= 0.0
    assert report.memory_hotspot.hottest_region is not None
    assert report.memory_hotspot.hottest_region_utilization >= 0.0
    assert report.memory_hotspot.hottest_region_peak_bytes_by_backing_store == {}
    assert report.memory_hotspot.hottest_region_peak_bytes_by_memory_class == {"ACTIVATION": 49152}
    assert report.node_hotspots
    assert report.node_hotspots[0].estimated_cycles > 0.0
    assert report.layer_breakdown
    assert report.layer_breakdown[0].estimated_cycles > 0.0
    assert manifest.artifact_index["prefill_evaluation_report"] == "reports/prefill_evaluation_report.json"
    assert summary.status == "completed"
    assert summary.exit_code == 0


def test_run_prefill_evaluation_rejects_decode_scenario(
    tmp_path: Path,
    minimal_performance_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = minimal_performance_run_root_factory(
        target_run_root=tmp_path / "run-prefill-eval-decode",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
    )

    result = run_prefill_evaluation(run_root)

    assert result.status == "failed"
    assert result.report_path is None
    assert "prefill" in result.diagnostics[0].message.lower()
