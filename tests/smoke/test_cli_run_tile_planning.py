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


def test_run_tile_planning_writes_tiling_plan_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-tile-plan-001"

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
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    tiling_plan = json.loads((run_root / "artifacts" / "tiling_plan.json").read_text(encoding="utf-8"))
    summary = json.loads((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["tiling_plan"] == "artifacts/tiling_plan.json"
    assert tiling_plan["candidates"]
    assert summary["status"] == "completed"
    assert summary["exit_code"] == 0
