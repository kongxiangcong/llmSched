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


def test_run_memory_planning_writes_memory_plan_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-memory-plan-001"

    init_result = run_cli(
        "init-run",
        "--run-root",
        str(run_root),
        "--model-path",
        "models/gemma3_1b/model_q4f16.onnx",
        "--target-profile",
        "profiles/targets/riscv_npu_single_core_v1.json",
        "--scenario-profile",
        "profiles/scenarios/decode_token1_kv2048.json",
        cwd=repo_root,
    )
    assert init_result.returncode == 0

    frontend_result = run_cli(
        "run-frontend-analysis",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )
    assert frontend_result.returncode == 0

    memory_result = run_cli(
        "run-memory-planning",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert memory_result.returncode == 0
    assert (run_root / "artifacts" / "memory_plan.json").is_file()

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["memory_plan"] == "artifacts/memory_plan.json"

    summary = json.loads((run_root / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed"
    assert summary["exit_code"] == 0


def test_run_memory_planning_reports_missing_bound_nig_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "missing-bound-nig-run"

    init_result = run_cli(
        "init-run",
        "--run-root",
        str(run_root),
        "--model-path",
        "models/gemma3_1b/model_q4f16.onnx",
        "--target-profile",
        "profiles/targets/riscv_npu_single_core_v1.json",
        "--scenario-profile",
        "profiles/scenarios/decode_token1_kv2048.json",
        cwd=repo_root,
    )
    assert init_result.returncode == 0

    result = run_cli(
        "run-memory-planning",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Memory planning: ERROR" in result.stdout
    assert "bound_nig_ir not found" in result.stdout
    assert "Traceback" not in result.stderr
