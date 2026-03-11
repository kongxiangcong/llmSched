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


def test_run_single_core_scheduling_writes_schedule_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-single-core-schedule-001"

    for args in [
        (
            "init-run",
            "--run-root",
            str(run_root),
            "--model-path",
            "models/gemma3_1b/model_q4f16.onnx",
            "--target-profile",
            "profiles/targets/riscv_npu_single_core_v1.json",
            "--scenario-profile",
            "profiles/scenarios/prefill_seq128.json",
        ),
        ("run-frontend-analysis", "--run-root", str(run_root)),
        ("run-memory-planning", "--run-root", str(run_root)),
        ("run-tile-planning", "--run-root", str(run_root)),
        ("run-single-core-scheduling", "--run-root", str(run_root)),
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    schedule_ir = json.loads((run_root / "artifacts" / "schedule_ir.json").read_text(encoding="utf-8"))
    summary = json.loads((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["schedule_ir"] == "artifacts/schedule_ir.json"
    assert schedule_ir["blocks"]
    assert summary["status"] == "completed"
    assert summary["exit_code"] == 0


def test_run_single_core_scheduling_rejects_dual_core_target_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-single-core-reject-dual"

    for args in [
        (
            "init-run",
            "--run-root",
            str(run_root),
            "--model-path",
            "models/gemma3_1b/model_q4f16.onnx",
            "--target-profile",
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "--scenario-profile",
            "profiles/scenarios/decode_token1_kv2048.json",
        ),
        ("run-frontend-analysis", "--run-root", str(run_root)),
        ("run-memory-planning", "--run-root", str(run_root)),
        ("run-tile-planning", "--run-root", str(run_root)),
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    result = run_cli(
        "run-single-core-scheduling",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Single-core scheduling: ERROR" in result.stdout
    assert "single-core target profile" in result.stdout
    assert "Traceback" not in result.stderr
