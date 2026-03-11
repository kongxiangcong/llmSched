from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_prepared_run_root_factory_clones_cached_stage_and_rewrites_run_identity(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-cache-clone-a",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="tile",
    )

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert (run_root / "artifacts" / "tiling_plan.json").is_file()
    assert manifest.run_id == "run-cache-clone-a"
    assert summary.run_id == "run-cache-clone-a"


def test_prepared_run_root_factory_supports_multiple_clones_of_one_cached_root(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    first = prepared_run_root_factory(
        target_run_root=tmp_path / "run-cache-clone-b1",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="tile",
    )
    second = prepared_run_root_factory(
        target_run_root=tmp_path / "run-cache-clone-b2",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="tile",
    )

    first_manifest = RunManifest.model_validate_json((first / "manifest.json").read_text(encoding="utf-8"))
    second_manifest = RunManifest.model_validate_json((second / "manifest.json").read_text(encoding="utf-8"))

    assert (first / "artifacts" / "tiling_plan.json").is_file()
    assert (second / "artifacts" / "tiling_plan.json").is_file()
    assert first_manifest.run_id == "run-cache-clone-b1"
    assert second_manifest.run_id == "run-cache-clone-b2"
