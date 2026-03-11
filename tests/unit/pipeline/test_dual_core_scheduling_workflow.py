from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_dual_core_scheduling_writes_schedule_ir(
    tmp_path: Path,
    minimal_tile_run_root_factory,
) -> None:
    from llm_sched.ir.schedule_ir import ScheduleIR
    from llm_sched.pipeline import run_dual_core_scheduling

    run_root = minimal_tile_run_root_factory(
        target_run_root=tmp_path / "run-dual-core-schedule-unit-001",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
    )

    result = run_dual_core_scheduling(run_root)

    assert result.status == "completed"
    assert result.schedule_ir_path == run_root / "artifacts" / "dual_core_schedule_ir.json"

    schedule = ScheduleIR.model_validate_json(result.schedule_ir_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert any(block.stage == "transfer" for block in schedule.blocks)
    assert any(block.issue_slot > 0 for block in schedule.blocks)
    transfer_blocks = [block for block in schedule.blocks if block.stage == "transfer"]
    assert transfer_blocks
    assert all(block.depends_on for block in transfer_blocks)
    assert all(block.duration_slots > 0 for block in transfer_blocks)
    assert all(block.sync_cost_cycles > 0 for block in transfer_blocks)
    assert "dual_core_schedule_ir" in manifest.artifact_index
    assert summary.status == "completed"
    assert summary.exit_code == 0
