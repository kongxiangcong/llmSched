from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_memory_planner_closure_writes_report_and_updates_manifest(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.contracts.memory_planner_closure_report import MemoryPlannerClosureReport
    from llm_sched.pipeline import (
        run_decode_evaluation,
        run_memory_planner_closure,
        run_visualization_packaging,
        run_visualization_workbench,
    )

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-memory-closure",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )
    assert run_decode_evaluation(run_root).status == "completed"
    assert run_visualization_packaging(run_root).status == "completed"
    assert run_visualization_workbench(run_root).status == "completed"

    result = run_memory_planner_closure(run_root)

    assert result.status == "completed"
    assert result.report_path == run_root / "reports" / "memory_planner_closure_report.json"

    report = MemoryPlannerClosureReport.model_validate_json(
        result.report_path.read_text(encoding="utf-8")
    )
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert report.planner_closure.status == "ready_for_acceptance"
    assert report.acceptance.status == "ready_for_acceptance"
    assert any(
        consumer.consumer_id == "visualization_workbench" and not consumer.required_for_acceptance
        for consumer in report.downstream_consumers
    )
    assert manifest.artifact_index["memory_planner_closure_report"] == "reports/memory_planner_closure_report.json"
    assert summary.status == "completed"
    assert summary.exit_code == 0


def test_run_memory_planner_closure_rejects_missing_manifest(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_memory_planner_closure

    run_root = tmp_path / "missing-manifest"
    run_root.mkdir(parents=True, exist_ok=True)

    result = run_memory_planner_closure(run_root)

    assert result.status == "failed"
    assert result.report_path is None
    assert "manifest" in result.diagnostics[0].message.lower()
