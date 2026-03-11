import json
import os
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(cwd / "src")
        if not existing_pythonpath
        else os.pathsep.join([str(cwd / "src"), existing_pythonpath])
    )
    return subprocess.run(
        [sys.executable, "-m", "llm_sched.cli.main", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_run_dual_core_scheduling_writes_schedule_artifact(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-dual-core-schedule-001",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="tile",
    )

    result = run_cli("run-dual-core-scheduling", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    schedule_ir = json.loads((run_root / "artifacts" / "dual_core_schedule_ir.json").read_text(encoding="utf-8"))
    summary = json.loads((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["dual_core_schedule_ir"] == "artifacts/dual_core_schedule_ir.json"
    assert any(block["stage"] == "transfer" for block in schedule_ir["blocks"])
    assert summary["status"] == "completed"
    assert summary["exit_code"] == 0


def test_run_dual_core_scheduling_rejects_single_core_target_without_traceback(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-dual-core-reject-single",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="tile",
    )

    result = run_cli(
        "run-dual-core-scheduling",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Dual-core scheduling: ERROR" in result.stdout
    assert "dual-core target profile" in result.stdout
    assert "Traceback" not in result.stderr
