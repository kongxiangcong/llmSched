import json
from pathlib import Path


def test_run_sweep_analysis_writes_delta_report(tmp_path: Path) -> None:
    from llm_sched.contracts.sweep_report import SweepDeltaReport
    from llm_sched.pipeline import run_sweep_analysis

    repo_root = Path(__file__).resolve().parents[3]
    sweep_root = tmp_path / "sweep-phase-d"
    sweep_spec_path = tmp_path / "sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "phase-d-foundation",
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str(
                    (repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()
                ),
                "target_profiles": [
                    str((repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()),
                    str((repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json").resolve()),
                ],
                "scenario_profiles": [
                    str((repo_root / "profiles" / "scenarios" / "prefill_seq128.json").resolve()),
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_sweep_analysis(sweep_spec_path, sweep_root)

    assert result.status == "completed"
    assert result.report_path == sweep_root / "reports" / "sweep_delta_report.json"
    assert len(result.run_roots) == 2

    report = SweepDeltaReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))
    assert report.sweep_name == "phase-d-foundation"
    assert report.completed_run_count == 2
    assert report.failed_run_count == 0
    assert len(report.comparisons) == 1
    assert report.run_records[0].layer_breakdown
    assert report.comparisons[0].layer_deltas
    assert report.comparisons[0].prefill_compare is not None
    assert report.comparisons[0].decode_compare is None
    metric_delta = next(
        delta for delta in report.comparisons[0].metric_deltas if delta.metric_name == "estimated_cycles"
    )
    assert report.comparisons[0].prefill_compare.estimated_cycles.delta_value == metric_delta.delta_value


def test_run_sweep_analysis_rejects_invalid_baseline_spec(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_sweep_analysis

    repo_root = Path(__file__).resolve().parents[3]
    sweep_root = tmp_path / "sweep-invalid"
    sweep_spec_path = tmp_path / "invalid-sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "invalid-sweep",
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str(
                    (repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()
                ),
                "target_profiles": [
                    str((repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json").resolve()),
                ],
                "scenario_profiles": [
                    str((repo_root / "profiles" / "scenarios" / "prefill_seq128.json").resolve()),
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_sweep_analysis(sweep_spec_path, sweep_root)

    assert result.status == "failed"
    assert result.report_path is None
    assert "baseline" in result.diagnostics[0].message.lower()
