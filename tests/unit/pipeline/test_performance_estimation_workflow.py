from pathlib import Path
import json
from unittest.mock import patch

import pytest

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.tiling_plan import TilingPlanArtifact


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
    summary_report_payload = result.summary_report_path.read_text(encoding="utf-8")
    summary_report = PerfSummaryReport.model_validate_json(summary_report_payload)
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
    assert summary_report.bandwidth_pressure_summary.peak_bandwidth_pressure >= 0.0
    assert summary_report.vmem_pressure_summary.hottest_region is not None
    if schedule_kind == "dual-core":
        assert summary_report.vmem_region_peak_bytes_by_memory_class["ping"]["ACTIVATION"] > 0
    else:
        assert summary_report.vmem_region_peak_bytes_by_memory_class["weight"]["WEIGHT"] > 0
    assert summary_report.totals["estimated_cycles"] > 0.0
    assert summary_report.totals["fitted_work_cycles"] >= summary_report.totals["estimated_cycles"]
    assert summary_report.totals["critical_path_cycles"] > 0.0
    assert summary_report.totals["critical_path_cycles"] == float(summary_report.schedule_makespan_slots)
    assert summary_report.fit_gap_summary.total_fit_gap_cycles >= 0.0
    assert summary_report.fit_gap_summary.dominant_fit_gap_phase in {
        "projection",
        "kv_io",
        "attention",
        "sync",
        "other",
        "",
    }
    assert summary_report.critical_path_fit_gap_summary.dominant_phase_vs_estimated in {
        "projection",
        "kv_io",
        "attention",
        "sync",
        "other",
        "",
    }
    assert summary_report.critical_path_fit_gap_summary.dominant_phase_vs_fitted in {
        "projection",
        "kv_io",
        "attention",
        "sync",
        "other",
        "",
    }
    assert summary_report.critical_path_fit_gap_summary.critical_path_minus_fitted_cycles <= 0.0
    assert summary_report.fit_floor_source_summary.schedule_floor_gap_cycles >= 0.0
    assert summary_report.fit_floor_source_summary.external_bandwidth_gap_cycles >= 0.0
    assert summary_report.fit_floor_source_summary.dominant_floor_source in {
        "estimated",
        "schedule_floor",
        "external_bandwidth",
        "",
    }
    assert summary_report.fit_floor_source_summary.dominant_floor_phase in {
        "projection",
        "kv_io",
        "attention",
        "sync",
        "other",
        "",
    }
    assert '"fit_gap_summary"' in summary_report_payload
    assert '"critical_path_fit_gap_summary"' in summary_report_payload
    assert '"fit_floor_source_summary"' in summary_report_payload
    assert summary_report.phase_attribution
    assert "other" in summary_report.phase_attribution
    assert summary_report.phase_attribution["other"].fitted_work_cycles >= 0.0
    assert summary_report.phase_attribution["other"].cycles_per_token >= 0.0
    assert summary_report.phase_attribution["other"].bytes_per_token >= 0.0
    assert summary_report.phase_attribution["other"].compute_cycles >= 0.0
    assert summary_report.phase_attribution["other"].memory_cycles >= 0.0
    assert summary_report.phase_attribution["other"].sync_cycles >= 0.0
    assert summary_report.phase_attribution["other"].schedule_compression_cycles >= 0.0
    assert summary_report.phase_attribution["other"].schedule_compression_ratio >= 0.0
    assert summary_report.phase_attribution["other"].schedule_overhang_cycles >= 0.0
    assert summary_report.phase_attribution["other"].occupied_slots >= 0.0
    assert summary_report.phase_attribution["other"].occupied_slots_per_token >= 0.0
    expected_core_keys = ["0", "1"] if schedule_kind == "dual-core" else ["0"]
    assert list(summary_report.phase_attribution["other"].per_core_occupied_slots) == expected_core_keys
    assert list(summary_report.phase_attribution["other"].per_core_span_slots) == expected_core_keys
    assert summary_report.phase_attribution["other"].occupied_slot_imbalance_slots >= 0.0
    assert summary_report.phase_attribution["other"].occupied_slot_balance_ratio >= 0.0
    assert summary_report.phase_attribution["other"].span_imbalance_slots >= 0.0
    assert summary_report.phase_attribution["other"].span_balance_ratio >= 0.0
    assert isinstance(summary_report.phase_attribution["other"].read_bytes_by_address_space, dict)
    assert isinstance(summary_report.phase_attribution["other"].write_bytes_by_address_space, dict)
    assert isinstance(summary_report.phase_attribution["other"].read_bytes_by_backing_store, dict)
    assert isinstance(summary_report.phase_attribution["other"].write_bytes_by_backing_store, dict)
    assert isinstance(summary_report.phase_attribution["other"].read_bytes_by_memory_class, dict)
    assert isinstance(summary_report.phase_attribution["other"].write_bytes_by_memory_class, dict)
    assert summary_report.per_node_cycles
    assert summary_report.per_node_fitted_work_cycles
    assert summary_report.per_node_bytes
    assert summary_report.per_layer_cycles
    assert summary_report.per_layer_fitted_work_cycles
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


def test_run_performance_estimation_passes_schedule_memory_and_tiling_context_to_estimator(
    tmp_path: Path,
    minimal_descriptor_run_root_factory,
) -> None:
    from llm_sched.contracts.perf_report import PerfSummaryReport
    from llm_sched.ir.analysis_ir import AnalysisIR
    from llm_sched.pipeline import run_performance_estimation

    run_root = minimal_descriptor_run_root_factory(
        target_run_root=tmp_path / "run-perf-forwarding",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )
    tiling_plan = TilingPlanArtifact.model_validate(
        {
            "graph_id": "workflow-minimal::riscv_npu_single_core_v1::prefill_seq128",
            "scenario_name": "prefill_seq128",
            "core_mode": "single-core",
            "candidates": [],
        }
    )
    tiling_plan_path = run_root / "artifacts" / "tiling_plan.json"
    tiling_plan_path.write_text(json.dumps(tiling_plan.model_dump(mode="json"), indent=2), encoding="utf-8")
    manifest_path = run_root / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    manifest_path.write_text(
        json.dumps(
            manifest.model_copy(
                update={
                    "artifact_index": {
                        **manifest.artifact_index,
                        "tiling_plan": "artifacts/tiling_plan.json",
                    }
                },
                deep=True,
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def fake_estimate_descriptor_analysis(
        descriptor_ir,
        coverage_report,
        hardware,
        scenario,
        *,
        schedule_ir,
        memory_plan,
        tiling_plan,
    ):
        captured["schedule_ir"] = schedule_ir
        captured["memory_plan"] = memory_plan
        captured["tiling_plan"] = tiling_plan
        return AnalysisIR(
            ir_version=descriptor_ir.ir_version,
            graph_id=descriptor_ir.graph_id,
            records=[],
        )

    def fake_build_perf_summary_report(
        run_id,
        descriptor_ir,
        analysis_ir,
        coverage_report,
        *,
        scenario=None,
        schedule_ir=None,
        memory_plan=None,
    ):
        return PerfSummaryReport(
            run_id=run_id,
            graph_id=analysis_ir.graph_id,
            schedule_kind=coverage_report.schedule_kind,
            totals={"estimated_cycles": 0.0, "fitted_work_cycles": 0.0, "critical_path_cycles": 0.0},
        )

    with (
        patch(
            "llm_sched.pipeline.performance_estimation.estimate_descriptor_analysis",
            side_effect=fake_estimate_descriptor_analysis,
        ),
        patch(
            "llm_sched.pipeline.performance_estimation.build_perf_summary_report",
            side_effect=fake_build_perf_summary_report,
        ),
    ):
        result = run_performance_estimation(run_root)

    assert result.status == "completed"
    assert captured["schedule_ir"] is not None
    assert captured["memory_plan"] is not None
    assert captured["tiling_plan"] is not None


def test_run_performance_estimation_serializes_residual_external_stall_metrics(
    tmp_path: Path,
    minimal_descriptor_run_root_factory,
) -> None:
    from llm_sched.contracts.perf_report import PerfSummaryReport
    from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
    from llm_sched.ir.common import AuditRef
    from llm_sched.pipeline import run_performance_estimation

    run_root = minimal_descriptor_run_root_factory(
        target_run_root=tmp_path / "run-perf-residual-stall",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )

    residual_analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="workflow-minimal::riscv_npu_single_core_v1::prefill_seq128",
        records=[
            AnalysisRecord(
                record_id="analysis.record.residual.compute",
                subject_id="sched.block.linear.compute",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 112.0,
                    "schedule_floor_cycles": 64.0,
                    "external_read_floor_cycles": 96.0,
                    "external_write_floor_cycles": 0.0,
                    "external_bandwidth_floor_cycles": 96.0,
                    "fit_floor_gap_cycles": 64.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.linear.compute"],
                    descriptor_ids=["desc.linear.compute"],
                ),
            )
        ],
    )
    residual_summary_report = PerfSummaryReport(
        run_id="run-perf-residual-stall",
        graph_id=residual_analysis_ir.graph_id,
        schedule_kind="single-core",
        totals={
            "estimated_cycles": 48.0,
            "fitted_work_cycles": 112.0,
            "critical_path_cycles": 64.0,
        },
        fit_gap_summary={
            "total_fit_gap_cycles": 64.0,
            "total_fit_gap_ratio": 64.0 / 48.0,
            "critical_path_gap_cycles": 16.0,
            "critical_path_ratio_vs_estimated": 64.0 / 48.0,
            "dominant_fit_gap_phase": "projection",
            "dominant_fit_gap_macro": "WDQ_GEMM",
        },
        fit_floor_source_summary={
            "schedule_floor_gap_cycles": 0.0,
            "external_bandwidth_gap_cycles": 64.0,
            "estimated_dominant_subject_count": 0,
            "schedule_floor_dominant_subject_count": 0,
            "external_bandwidth_dominant_subject_count": 1,
            "dominant_floor_source": "external_bandwidth",
            "dominant_floor_phase": "projection",
            "dominant_floor_macro": "WDQ_GEMM",
        },
        fit_floor_direction_summary={
            "external_read_gap_cycles": 96.0,
            "external_write_gap_cycles": 0.0,
            "dominant_external_direction": "read",
            "dominant_external_phase": "projection",
            "dominant_external_macro": "WDQ_GEMM",
        },
    )

    with (
        patch(
            "llm_sched.pipeline.performance_estimation.estimate_descriptor_analysis",
            return_value=residual_analysis_ir,
        ),
        patch(
            "llm_sched.pipeline.performance_estimation.build_perf_summary_report",
            return_value=residual_summary_report,
        ),
    ):
        result = run_performance_estimation(run_root)

    assert result.status == "completed"
    analysis_payload = json.loads(result.analysis_ir_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(result.summary_report_path.read_text(encoding="utf-8"))

    assert analysis_payload["records"][0]["metrics"]["fitted_work_cycles"] == pytest.approx(112.0)
    assert analysis_payload["records"][0]["metrics"]["fit_floor_gap_cycles"] == pytest.approx(64.0)
    assert summary_payload["totals"]["fitted_work_cycles"] == pytest.approx(112.0)
    assert summary_payload["fit_gap_summary"]["total_fit_gap_cycles"] == pytest.approx(64.0)
    assert summary_payload["fit_floor_source_summary"]["external_bandwidth_gap_cycles"] == pytest.approx(64.0)
    assert summary_payload["fit_floor_direction_summary"]["external_read_gap_cycles"] == pytest.approx(96.0)
    assert summary_payload["fit_floor_direction_summary"]["external_write_gap_cycles"] == pytest.approx(0.0)


def test_run_performance_estimation_serializes_bidirectional_shared_dma_stall_metrics(
    tmp_path: Path,
    minimal_descriptor_run_root_factory,
) -> None:
    from llm_sched.contracts.perf_report import PerfSummaryReport
    from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
    from llm_sched.ir.common import AuditRef
    from llm_sched.pipeline import run_performance_estimation

    run_root = minimal_descriptor_run_root_factory(
        target_run_root=tmp_path / "run-perf-bidirectional-stall",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )

    bidirectional_analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="workflow-minimal::riscv_npu_single_core_v1::prefill_seq128",
        records=[
            AnalysisRecord(
                record_id="analysis.record.bidirectional.compute",
                subject_id="sched.block.linear.compute",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 128.0,
                    "schedule_floor_cycles": 64.0,
                    "external_read_floor_cycles": 96.0,
                    "external_write_floor_cycles": 32.0,
                    "external_bandwidth_floor_cycles": 128.0,
                    "fit_floor_gap_cycles": 80.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.linear.compute"],
                    descriptor_ids=["desc.linear.compute"],
                ),
            )
        ],
    )
    bidirectional_summary_report = PerfSummaryReport(
        run_id="run-perf-bidirectional-stall",
        graph_id=bidirectional_analysis_ir.graph_id,
        schedule_kind="single-core",
        totals={
            "estimated_cycles": 48.0,
            "fitted_work_cycles": 128.0,
            "critical_path_cycles": 64.0,
        },
        fit_gap_summary={
            "total_fit_gap_cycles": 80.0,
            "total_fit_gap_ratio": 80.0 / 48.0,
            "critical_path_gap_cycles": 16.0,
            "critical_path_ratio_vs_estimated": 64.0 / 48.0,
            "dominant_fit_gap_phase": "projection",
            "dominant_fit_gap_macro": "WDQ_GEMM",
        },
        fit_floor_source_summary={
            "schedule_floor_gap_cycles": 0.0,
            "external_bandwidth_gap_cycles": 80.0,
            "estimated_dominant_subject_count": 0,
            "schedule_floor_dominant_subject_count": 0,
            "external_bandwidth_dominant_subject_count": 1,
            "dominant_floor_source": "external_bandwidth",
            "dominant_floor_phase": "projection",
            "dominant_floor_macro": "WDQ_GEMM",
        },
        fit_floor_direction_summary={
            "external_read_gap_cycles": 96.0,
            "external_write_gap_cycles": 32.0,
            "dominant_external_direction": "read",
            "dominant_external_phase": "projection",
            "dominant_external_macro": "WDQ_GEMM",
        },
    )

    with (
        patch(
            "llm_sched.pipeline.performance_estimation.estimate_descriptor_analysis",
            return_value=bidirectional_analysis_ir,
        ),
        patch(
            "llm_sched.pipeline.performance_estimation.build_perf_summary_report",
            return_value=bidirectional_summary_report,
        ),
    ):
        result = run_performance_estimation(run_root)

    assert result.status == "completed"
    analysis_payload = json.loads(result.analysis_ir_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(result.summary_report_path.read_text(encoding="utf-8"))

    assert analysis_payload["records"][0]["metrics"]["fitted_work_cycles"] == pytest.approx(128.0)
    assert analysis_payload["records"][0]["metrics"]["fit_floor_gap_cycles"] == pytest.approx(80.0)
    assert analysis_payload["records"][0]["metrics"]["external_bandwidth_floor_cycles"] == pytest.approx(128.0)
    assert summary_payload["totals"]["fitted_work_cycles"] == pytest.approx(128.0)
    assert summary_payload["fit_gap_summary"]["total_fit_gap_cycles"] == pytest.approx(80.0)
    assert summary_payload["fit_floor_source_summary"]["external_bandwidth_gap_cycles"] == pytest.approx(80.0)
    assert summary_payload["fit_floor_direction_summary"]["external_read_gap_cycles"] == pytest.approx(96.0)
    assert summary_payload["fit_floor_direction_summary"]["external_write_gap_cycles"] == pytest.approx(32.0)


def test_run_performance_estimation_serializes_external_write_drain_metrics(
    tmp_path: Path,
    minimal_descriptor_run_root_factory,
) -> None:
    from llm_sched.contracts.perf_report import PerfSummaryReport
    from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
    from llm_sched.ir.common import AuditRef
    from llm_sched.pipeline import run_performance_estimation

    run_root = minimal_descriptor_run_root_factory(
        target_run_root=tmp_path / "run-perf-write-drain",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )

    write_drain_analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="workflow-minimal::riscv_npu_single_core_v1::prefill_seq128",
        records=[
            AnalysisRecord(
                record_id="analysis.record.write.drain.compute",
                subject_id="sched.block.linear.compute",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 80.0,
                    "schedule_floor_cycles": 48.0,
                    "external_read_floor_cycles": 0.0,
                    "external_write_floor_cycles": 32.0,
                    "external_bandwidth_floor_cycles": 32.0,
                    "fit_floor_gap_cycles": 32.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.linear.compute"],
                    descriptor_ids=["desc.linear.compute"],
                ),
            )
        ],
    )
    write_drain_summary_report = PerfSummaryReport(
        run_id="run-perf-write-drain",
        graph_id=write_drain_analysis_ir.graph_id,
        schedule_kind="single-core",
        totals={
            "estimated_cycles": 48.0,
            "fitted_work_cycles": 80.0,
            "critical_path_cycles": 48.0,
        },
        fit_gap_summary={
            "total_fit_gap_cycles": 32.0,
            "total_fit_gap_ratio": 32.0 / 48.0,
            "critical_path_gap_cycles": 0.0,
            "critical_path_ratio_vs_estimated": 1.0,
            "dominant_fit_gap_phase": "projection",
            "dominant_fit_gap_macro": "WDQ_GEMM",
        },
        fit_floor_source_summary={
            "schedule_floor_gap_cycles": 0.0,
            "external_bandwidth_gap_cycles": 32.0,
            "estimated_dominant_subject_count": 0,
            "schedule_floor_dominant_subject_count": 0,
            "external_bandwidth_dominant_subject_count": 1,
            "dominant_floor_source": "external_bandwidth",
            "dominant_floor_phase": "projection",
            "dominant_floor_macro": "WDQ_GEMM",
        },
        fit_floor_direction_summary={
            "external_read_gap_cycles": 0.0,
            "external_write_gap_cycles": 32.0,
            "dominant_external_direction": "write",
            "dominant_external_phase": "projection",
            "dominant_external_macro": "WDQ_GEMM",
        },
    )

    with (
        patch(
            "llm_sched.pipeline.performance_estimation.estimate_descriptor_analysis",
            return_value=write_drain_analysis_ir,
        ),
        patch(
            "llm_sched.pipeline.performance_estimation.build_perf_summary_report",
            return_value=write_drain_summary_report,
        ),
    ):
        result = run_performance_estimation(run_root)

    assert result.status == "completed"
    analysis_payload = json.loads(result.analysis_ir_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(result.summary_report_path.read_text(encoding="utf-8"))

    assert analysis_payload["records"][0]["metrics"]["fitted_work_cycles"] == pytest.approx(80.0)
    assert analysis_payload["records"][0]["metrics"]["external_write_floor_cycles"] == pytest.approx(32.0)
    assert summary_payload["totals"]["fitted_work_cycles"] == pytest.approx(80.0)
    assert summary_payload["fit_gap_summary"]["total_fit_gap_cycles"] == pytest.approx(32.0)
    assert summary_payload["fit_floor_direction_summary"]["external_read_gap_cycles"] == pytest.approx(0.0)
    assert summary_payload["fit_floor_direction_summary"]["external_write_gap_cycles"] == pytest.approx(32.0)


def test_run_performance_estimation_serializes_schedule_slack_absorbed_write_drain_metrics(
    tmp_path: Path,
    minimal_descriptor_run_root_factory,
) -> None:
    from llm_sched.contracts.perf_report import PerfSummaryReport
    from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
    from llm_sched.ir.common import AuditRef
    from llm_sched.pipeline import run_performance_estimation

    run_root = minimal_descriptor_run_root_factory(
        target_run_root=tmp_path / "run-perf-write-slack",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )

    write_slack_analysis_ir = AnalysisIR(
        ir_version="phase-a.v1",
        graph_id="workflow-minimal::riscv_npu_single_core_v1::prefill_seq128",
        records=[
            AnalysisRecord(
                record_id="analysis.record.write.slack.compute",
                subject_id="sched.block.linear.compute",
                metrics={
                    "read_bytes": 20480.0,
                    "write_bytes": 12288.0,
                    "total_bytes": 32768.0,
                    "estimated_cycles": 48.0,
                    "fitted_work_cycles": 80.0,
                    "schedule_floor_cycles": 64.0,
                    "external_read_floor_cycles": 0.0,
                    "external_write_floor_cycles": 32.0,
                    "external_bandwidth_floor_cycles": 32.0,
                    "fit_floor_gap_cycles": 32.0,
                    "sync_cycles": 0.0,
                    "bandwidth_pressure": 682.6666666666666,
                },
                tags=["descriptor-analysis", "compute-bound", "fit-floor:external_bandwidth"],
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.linear.compute"],
                    descriptor_ids=["desc.linear.compute"],
                ),
            )
        ],
    )
    write_slack_summary_report = PerfSummaryReport(
        run_id="run-perf-write-slack",
        graph_id=write_slack_analysis_ir.graph_id,
        schedule_kind="single-core",
        totals={
            "estimated_cycles": 48.0,
            "fitted_work_cycles": 80.0,
            "critical_path_cycles": 64.0,
        },
        fit_gap_summary={
            "total_fit_gap_cycles": 32.0,
            "total_fit_gap_ratio": 32.0 / 48.0,
            "critical_path_gap_cycles": 16.0,
            "critical_path_ratio_vs_estimated": 64.0 / 48.0,
            "dominant_fit_gap_phase": "projection",
            "dominant_fit_gap_macro": "WDQ_GEMM",
        },
        fit_floor_source_summary={
            "schedule_floor_gap_cycles": 0.0,
            "external_bandwidth_gap_cycles": 32.0,
            "estimated_dominant_subject_count": 0,
            "schedule_floor_dominant_subject_count": 0,
            "external_bandwidth_dominant_subject_count": 1,
            "dominant_floor_source": "external_bandwidth",
            "dominant_floor_phase": "projection",
            "dominant_floor_macro": "WDQ_GEMM",
        },
        fit_floor_direction_summary={
            "external_read_gap_cycles": 0.0,
            "external_write_gap_cycles": 32.0,
            "dominant_external_direction": "write",
            "dominant_external_phase": "projection",
            "dominant_external_macro": "WDQ_GEMM",
        },
    )

    with (
        patch(
            "llm_sched.pipeline.performance_estimation.estimate_descriptor_analysis",
            return_value=write_slack_analysis_ir,
        ),
        patch(
            "llm_sched.pipeline.performance_estimation.build_perf_summary_report",
            return_value=write_slack_summary_report,
        ),
    ):
        result = run_performance_estimation(run_root)

    assert result.status == "completed"
    analysis_payload = json.loads(result.analysis_ir_path.read_text(encoding="utf-8"))
    summary_payload = json.loads(result.summary_report_path.read_text(encoding="utf-8"))

    assert analysis_payload["records"][0]["metrics"]["schedule_floor_cycles"] == pytest.approx(64.0)
    assert analysis_payload["records"][0]["metrics"]["fitted_work_cycles"] == pytest.approx(80.0)
    assert summary_payload["totals"]["fitted_work_cycles"] == pytest.approx(80.0)
    assert summary_payload["fit_gap_summary"]["total_fit_gap_cycles"] == pytest.approx(32.0)
    assert summary_payload["fit_floor_direction_summary"]["external_write_gap_cycles"] == pytest.approx(32.0)
