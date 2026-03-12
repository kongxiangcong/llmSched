from pathlib import Path

import pytest

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


@pytest.mark.parametrize(
    ("target_profile", "scenario_profile", "schedule_kind", "schedule_artifact_name"),
    [
        (
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "single-core",
            "schedule_ir",
        ),
        (
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "dual-core",
            "dual_core_schedule_ir",
        ),
    ],
)
def test_run_performance_estimation_writes_analysis_and_summary_artifacts(
    tmp_path: Path,
    minimal_descriptor_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    schedule_kind: str,
    schedule_artifact_name: str,
) -> None:
    from llm_sched.contracts.perf_report import PerfSummaryReport
    from llm_sched.ir.analysis_ir import AnalysisIR
    from llm_sched.pipeline import run_performance_estimation

    run_root = minimal_descriptor_run_root_factory(
        target_run_root=tmp_path / f"run-perf-{schedule_kind}",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
    )

    result = run_performance_estimation(run_root)

    assert result.status == "completed"
    assert result.analysis_ir_path == run_root / "artifacts" / "perf_analysis_ir.json"
    assert result.summary_report_path == run_root / "reports" / "perf_summary_report.json"

    analysis_ir = AnalysisIR.model_validate_json(result.analysis_ir_path.read_text(encoding="utf-8"))
    summary_report = PerfSummaryReport.model_validate_json(
        result.summary_report_path.read_text(encoding="utf-8")
    )
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert analysis_ir.records
    assert summary_report.schedule_kind == schedule_kind
    assert summary_report.schedule_makespan_slots > 0
    assert summary_report.per_core_makespan_slots
    assert summary_report.per_core_busy_slots
    assert summary_report.per_core_idle_slots
    assert summary_report.schedule_stage_slot_totals
    assert summary_report.data_movement_read_bytes_by_address_space
    assert summary_report.data_movement_write_bytes_by_address_space or schedule_kind == "single-core"
    assert summary_report.vmem_region_peak_bytes
    assert summary_report.vmem_region_peak_bytes_by_memory_class
    assert summary_report.vmem_region_capacity_bytes
    assert summary_report.vmem_region_peak_utilization
    if schedule_kind == "dual-core":
        assert summary_report.vmem_region_peak_bytes_by_memory_class["ping"]["ACTIVATION"] > 0
    else:
        assert summary_report.vmem_region_peak_bytes_by_memory_class["weight"]["WEIGHT"] > 0
    assert summary_report.totals["estimated_cycles"] > 0.0
    assert summary_report.totals["critical_path_cycles"] > 0.0
    assert summary_report.totals["critical_path_cycles"] == float(summary_report.schedule_makespan_slots)
    assert summary_report.phase_attribution
    assert "other" in summary_report.phase_attribution
    assert summary_report.phase_attribution["other"].cycles_per_token >= 0.0
    assert summary_report.phase_attribution["other"].bytes_per_token >= 0.0
    assert summary_report.per_node_cycles
    assert summary_report.per_node_bytes
    assert summary_report.per_layer_cycles
    assert summary_report.per_layer_bytes
    assert sum(summary_report.per_core_busy_slots.values()) > 0
    if schedule_kind == "dual-core":
        assert summary_report.schedule_transfer_slots > 0
        assert "transfer" in summary_report.schedule_stage_slot_totals
    else:
        assert summary_report.schedule_transfer_slots == 0
    assert schedule_artifact_name in manifest.artifact_index
    assert manifest.artifact_index["perf_analysis_ir"] == "artifacts/perf_analysis_ir.json"
    assert manifest.artifact_index["perf_summary_report"] == "reports/perf_summary_report.json"
    assert summary.status == "completed"
    assert summary.exit_code == 0
