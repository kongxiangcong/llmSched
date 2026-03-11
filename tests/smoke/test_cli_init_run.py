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


def test_init_run_creates_run_root_and_manifest(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-001"

    result = run_cli(
        "init-run",
        "--run-root",
        str(run_root),
        "--model-path",
        "models/gemma3_1b/model_q4f16.onnx",
        "--target-profile",
        "profiles/targets/riscv_npu_single_core_v1.json",
        "--scenario-profile",
        "profiles/scenarios/prefill_seq128.json",
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert (run_root / "artifacts").is_dir()
    assert (run_root / "reports").is_dir()
    assert (run_root / "logs").is_dir()
    assert (run_root / "dumps").is_dir()
    assert (run_root / "manifest.json").is_file()
    assert (run_root / "run-summary.json").is_file()

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "initialized"
    assert manifest["target_profile_path"].endswith("riscv_npu_single_core_v1.json")

    summary = json.loads((run_root / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["exit_code"] == 0
    assert summary["status"] == "initialized"
