import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_tile_planning_writes_tiling_plan_artifact(tmp_path: Path) -> None:
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact
    from llm_sched.pipeline import run_frontend_analysis, run_memory_planning, run_tile_planning

    repo_root = Path(__file__).resolve().parents[3]
    run_root = tmp_path / "run-tile-plan-unit-001"
    _write_initialized_run(
        run_root,
        repo_root,
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )

    frontend_result = run_frontend_analysis(run_root)
    assert frontend_result.status == "completed"
    memory_result = run_memory_planning(run_root)
    assert memory_result.status == "completed"

    result = run_tile_planning(run_root)

    assert result.status == "completed"
    assert result.tiling_plan_path == run_root / "artifacts" / "tiling_plan.json"

    artifact = TilingPlanArtifact.model_validate_json(result.tiling_plan_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert artifact.candidates
    assert artifact.candidates[0].rank >= 1
    assert artifact.candidates[0].ranking_reason
    assert artifact.candidates[0].resource_summary is not None
    assert "tiling_plan" in manifest.artifact_index
    assert summary.status == "completed"
    assert summary.exit_code == 0


def _write_initialized_run(
    run_root: Path,
    repo_root: Path,
    *,
    scenario_relative_path: str,
) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    for relative in ("artifacts", "reports", "logs", "dumps"):
        (run_root / relative).mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_root.name,
        contract_version="phase-a.v1",
        status="initialized",
        model_path=str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
        target_profile_path=str((repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()),
        scenario_profile_path=str((repo_root / scenario_relative_path).resolve()),
        artifact_index={
            "manifest": "manifest.json",
            "artifacts_dir": "artifacts",
            "reports_dir": "reports",
            "logs_dir": "logs",
            "dumps_dir": "dumps",
        },
    )
    (run_root / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(
            RunSummary(
                run_id=run_root.name,
                status="initialized",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )
