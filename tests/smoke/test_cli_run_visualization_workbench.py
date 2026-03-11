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


def test_run_visualization_workbench_writes_static_assets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-workbench-cli"

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
        ("run-descriptor-generation", "--run-root", str(run_root)),
        ("run-performance-estimation", "--run-root", str(run_root)),
        ("run-prefill-evaluation", "--run-root", str(run_root)),
        ("run-visualization-packaging", "--run-root", str(run_root)),
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    result = run_cli(
        "run-visualization-workbench",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Visualization workbench completed" in result.stdout

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    workbench = json.loads((run_root / "workbench" / "workbench_manifest.json").read_text(encoding="utf-8"))

    assert (run_root / "workbench" / "index.html").is_file()
    assert manifest["artifact_index"]["visualization_workbench_entry"] == "workbench/index.html"
    assert manifest["artifact_index"]["visualization_workbench_manifest"] == "workbench/workbench_manifest.json"
    assert workbench["default_panel"] == "summary"


def test_run_visualization_workbench_rejects_missing_bundle_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-workbench-missing-bundle"

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

    result = run_cli(
        "run-visualization-workbench",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Visualization workbench: ERROR" in result.stdout
    assert "visualization_bundle" in result.stdout
    assert "Traceback" not in result.stderr
