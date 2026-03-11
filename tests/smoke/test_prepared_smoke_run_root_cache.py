from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.sweep_report import SweepDeltaReport


def test_prepared_smoke_run_root_factory_clones_cached_descriptor_stage(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "smoke-cache-clone-a",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="descriptor",
    )

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert (run_root / "artifacts" / "descriptor_ir.json").is_file()
    assert manifest.run_id == "smoke-cache-clone-a"
    assert summary.run_id == "smoke-cache-clone-a"


def test_prepared_smoke_run_root_factory_supports_multiple_clones(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    first = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "smoke-cache-clone-b1",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )
    second = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "smoke-cache-clone-b2",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )

    first_manifest = RunManifest.model_validate_json((first / "manifest.json").read_text(encoding="utf-8"))
    second_manifest = RunManifest.model_validate_json((second / "manifest.json").read_text(encoding="utf-8"))

    assert (first / "reports" / "perf_summary_report.json").is_file()
    assert (second / "reports" / "perf_summary_report.json").is_file()
    assert first_manifest.run_id == "smoke-cache-clone-b1"
    assert second_manifest.run_id == "smoke-cache-clone-b2"


def test_prepared_smoke_sweep_root_factory_clones_cached_sweep_root(
    tmp_path: Path,
    prepared_smoke_sweep_root_factory,
) -> None:
    first = prepared_smoke_sweep_root_factory(
        target_sweep_root=tmp_path / "smoke-sweep-clone-a",
        baseline_target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        target_relative_paths=[
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/targets/riscv_npu_dual_core_v1.json",
        ],
        scenario_relative_paths=["profiles/scenarios/prefill_seq128.json"],
    )
    second = prepared_smoke_sweep_root_factory(
        target_sweep_root=tmp_path / "smoke-sweep-clone-b",
        baseline_target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        target_relative_paths=[
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/targets/riscv_npu_dual_core_v1.json",
        ],
        scenario_relative_paths=["profiles/scenarios/prefill_seq128.json"],
    )

    first_report = SweepDeltaReport.model_validate_json(
        (first / "reports" / "sweep_delta_report.json").read_text(encoding="utf-8")
    )
    second_report = SweepDeltaReport.model_validate_json(
        (second / "reports" / "sweep_delta_report.json").read_text(encoding="utf-8")
    )

    assert (first / "reports" / "sweep_delta_report.json").is_file()
    assert (second / "reports" / "sweep_delta_report.json").is_file()
    assert first_report.completed_run_count == 2
    assert second_report.completed_run_count == 2
    assert all(Path(record.run_root).is_relative_to(first / "runs") for record in first_report.run_records)
    assert all(Path(record.run_root).is_relative_to(second / "runs") for record in second_report.run_records)
