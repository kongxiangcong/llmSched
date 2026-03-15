import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_memory_planning_writes_memory_plan_artifact(tmp_path: Path) -> None:
    from llm_sched.contracts.memory_plan import MemoryPlanArtifact
    from llm_sched.pipeline import run_frontend_analysis, run_memory_planning

    repo_root = Path(__file__).resolve().parents[3]
    run_root = tmp_path / "run-memory-plan-unit-001"
    _write_initialized_run(
        run_root,
        repo_root,
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
    )

    frontend_result = run_frontend_analysis(run_root)
    assert frontend_result.status == "completed"

    result = run_memory_planning(run_root)

    assert result.status == "completed"
    assert result.memory_plan_path == run_root / "artifacts" / "memory_plan.json"

    artifact = MemoryPlanArtifact.model_validate_json(result.memory_plan_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert artifact.allocations
    assert artifact.storage_bindings
    assert artifact.kv_formulas == []
    assert artifact.address_diagnostics
    assert artifact.allocations[0].lifetime_bucket in {"preload", "compute", "store", "persist"}
    assert artifact.allocations[0].backing_store in {"vmem-local", "ddr-backed-staged", "ddr-persistent"}
    assert any(allocation.storage_binding_id for allocation in artifact.allocations if allocation.backing_store != "vmem-local")
    assert all(diagnostic.status == "bound" for diagnostic in artifact.address_diagnostics)
    assert "peak_lifetime_bucket" in artifact.region_summaries["ping"].model_dump(mode="json")
    assert "peak_bytes_by_memory_class" in artifact.region_summaries["ping"].model_dump(mode="json")
    assert "required_bytes_by_backing_store" in artifact.diagnostics[0].model_dump(mode="json")
    assert "memory_plan" in manifest.artifact_index
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
