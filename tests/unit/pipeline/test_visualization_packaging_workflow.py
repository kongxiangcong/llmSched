import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_visualization_packaging_writes_bundle_and_updates_manifest(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.contracts.visualization_bundle import VisualizationBundle
    from llm_sched.pipeline import run_decode_evaluation, run_visualization_packaging

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-viz-decode",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )
    assert run_decode_evaluation(run_root).status == "completed"

    sweep_root = tmp_path / "sweep-phase-d"
    (sweep_root / "reports").mkdir(parents=True, exist_ok=True)
    (sweep_root / "reports" / "sweep_delta_report.json").write_text(
        json.dumps(_sweep_report().model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (sweep_root / "reports" / "phase_d_compare_report.json").write_text(
        json.dumps(_phase_d_compare_report().model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    result = run_visualization_packaging(run_root, sweep_root=sweep_root)

    assert result.status == "completed"
    assert result.bundle_path == run_root / "reports" / "visualization_bundle.json"

    bundle = VisualizationBundle.model_validate_json(result.bundle_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert bundle.metadata.mode == "decode"
    assert bundle.sweep_view is not None
    assert bundle.sweep_view.comparisons[0].compare_summary is not None
    assert bundle.sweep_view.comparisons[0].compare_summary.candidate_schedule_kind == "dual-core"
    assert bundle.sweep_view.comparisons[0].compare_summary.scalar_deltas[0].metric_name == (
        "estimated_cycles"
    )
    metric_names = [
        scalar.metric_name for scalar in bundle.sweep_view.comparisons[0].compare_summary.scalar_deltas
    ]
    assert set(metric_names) >= {
        "estimated_cycles",
        "critical_path_cycles",
        "critical_path_cycles_per_token",
        "projection_cycles",
        "projection_cycle_share",
        "kv_io_cycles",
        "kv_io_cycle_share",
        "attention_cycles",
        "attention_cycle_share",
        "other_cycles",
        "other_cycle_share",
        "sync_cycle_share",
    }
    assert metric_names.count("sync_cycles") == 1
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].delta_cycles == -128.0
    assert bundle.vmem_view.regions[0].peak_bytes_by_memory_class
    assert "vmem-local" in bundle.vmem_view.regions[0].peak_bytes_by_backing_store
    assert bundle.coverage_view.packed_record_count > 0
    assert bundle.coverage_view.packed_stream_total_bytes >= bundle.coverage_view.packed_record_count * 64
    assert "core_link_transfer_v1" in bundle.coverage_view.packed_layout_template_counts
    assert bundle.coverage_view.packed_field_name_counts["transfer_kind"] >= 1
    assert manifest.artifact_index["visualization_bundle"] == "reports/visualization_bundle.json"
    assert summary.status == "completed"
    assert summary.exit_code == 0


def test_run_visualization_packaging_rejects_missing_manifest(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_visualization_packaging

    run_root = tmp_path / "missing-manifest"
    run_root.mkdir(parents=True, exist_ok=True)

    result = run_visualization_packaging(run_root)

    assert result.status == "failed"
    assert result.bundle_path is None
    assert "manifest" in result.diagnostics[0].message.lower()


def _sweep_report():
    from llm_sched.contracts.sweep_report import SweepDeltaReport

    return SweepDeltaReport.model_validate(
        {
            "sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 2,
            "failed_run_count": 0,
            "run_records": [],
            "comparisons": [
                {
                    "scenario_name": "decode_token1_kv2048",
                    "mode": "decode",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "metric_deltas": [
                        {
                            "metric_name": "estimated_cycles",
                            "baseline_value": 768.0,
                            "candidate_value": 512.0,
                            "delta_value": -256.0,
                            "delta_ratio": -0.3333333333,
                        }
                    ],
                    "macro_deltas": [],
                    "layer_deltas": [
                        {
                            "layer_id": 0,
                            "baseline_cycles": 384.0,
                            "candidate_cycles": 256.0,
                            "delta_cycles": -128.0,
                            "baseline_bytes": 8192.0,
                            "candidate_bytes": 6144.0,
                            "delta_bytes": -2048.0,
                        }
                    ],
                }
            ],
            "issues": [],
        }
    )


def _phase_d_compare_report():
    from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport

    return PhaseDCompareReport.model_validate(
        {
            "report_name": "phase-d-compare.phase-d-foundation",
            "source_sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 2,
            "failed_run_count": 0,
            "comparison_count": 1,
            "prefill_compare_count": 0,
            "decode_compare_count": 1,
            "prefill_compares": [],
            "decode_compares": [
                {
                    "scenario_name": "decode_token1_kv2048",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "layer_delta_count": 1,
                    "estimated_cycles": {
                        "baseline_value": 768.0,
                        "candidate_value": 512.0,
                        "delta_value": -256.0,
                        "delta_ratio": -0.3333333333,
                    },
                    "critical_path_cycles": {
                        "baseline_value": 704.0,
                        "candidate_value": 448.0,
                        "delta_value": -256.0,
                        "delta_ratio": -0.3636363636,
                    },
                    "projection_cycles": {
                        "baseline_value": 200.0,
                        "candidate_value": 128.0,
                        "delta_value": -72.0,
                        "delta_ratio": -0.36,
                    },
                    "projection_cycle_share": {
                        "baseline_value": 0.2604166667,
                        "candidate_value": 0.25,
                        "delta_value": -0.0104166667,
                        "delta_ratio": -0.04,
                    },
                    "kv_io_cycles": {
                        "baseline_value": 256.0,
                        "candidate_value": 192.0,
                        "delta_value": -64.0,
                        "delta_ratio": -0.25,
                    },
                    "kv_io_cycle_share": {
                        "baseline_value": 0.3333333333,
                        "candidate_value": 0.375,
                        "delta_value": 0.0416666667,
                        "delta_ratio": 0.1250000001,
                    },
                    "attention_cycles": {
                        "baseline_value": 160.0,
                        "candidate_value": 128.0,
                        "delta_value": -32.0,
                        "delta_ratio": -0.2,
                    },
                    "attention_cycle_share": {
                        "baseline_value": 0.2083333333,
                        "candidate_value": 0.25,
                        "delta_value": 0.0416666667,
                        "delta_ratio": 0.2000000002,
                    },
                    "other_cycles": {
                        "baseline_value": 48.0,
                        "candidate_value": 32.0,
                        "delta_value": -16.0,
                        "delta_ratio": -0.3333333333,
                    },
                    "other_cycle_share": {
                        "baseline_value": 0.0625,
                        "candidate_value": 0.0625,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "cycles_per_token": {
                        "baseline_value": 768.0,
                        "candidate_value": 512.0,
                        "delta_value": -256.0,
                        "delta_ratio": -0.3333333333,
                    },
                    "critical_path_cycles_per_token": {
                        "baseline_value": 704.0,
                        "candidate_value": 448.0,
                        "delta_value": -256.0,
                        "delta_ratio": -0.3636363636,
                    },
                    "kv_related_cycle_share": {
                        "baseline_value": 0.5,
                        "candidate_value": 0.375,
                        "delta_value": -0.125,
                        "delta_ratio": -0.25,
                    },
                    "kv_related_bytes": {
                        "baseline_value": 16384.0,
                        "candidate_value": 12288.0,
                        "delta_value": -4096.0,
                        "delta_ratio": -0.25,
                    },
                    "sync_cycles": {
                        "baseline_value": 64.0,
                        "candidate_value": 32.0,
                        "delta_value": -32.0,
                        "delta_ratio": -0.5,
                    },
                    "sync_cycle_share": {
                        "baseline_value": 0.0833333333,
                        "candidate_value": 0.0625,
                        "delta_value": -0.0208333333,
                        "delta_ratio": -0.25,
                    },
                }
            ],
            "issues": [],
        }
    )
