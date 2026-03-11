import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_visualization_packaging_writes_bundle_and_updates_manifest(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.contracts.sweep_report import SweepDeltaReport
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

    result = run_visualization_packaging(run_root, sweep_root=sweep_root)

    assert result.status == "completed"
    assert result.bundle_path == run_root / "reports" / "visualization_bundle.json"

    bundle = VisualizationBundle.model_validate_json(result.bundle_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert bundle.metadata.mode == "decode"
    assert bundle.sweep_view is not None
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
                }
            ],
            "issues": [],
        }
    )
