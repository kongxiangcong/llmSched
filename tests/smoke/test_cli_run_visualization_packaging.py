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


def test_run_visualization_packaging_writes_bundle_with_optional_sweep(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-viz-cli-decode"

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
        ("run-dual-core-scheduling", "--run-root", str(run_root)),
        ("run-descriptor-generation", "--run-root", str(run_root)),
        ("run-performance-estimation", "--run-root", str(run_root)),
        ("run-decode-evaluation", "--run-root", str(run_root)),
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    sweep_root = tmp_path / "sweep-viz-cli"
    sweep_spec_path = tmp_path / "sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "viz-cli-sweep",
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str(
                    (repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()
                ),
                "target_profiles": [
                    str((repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()),
                    str((repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json").resolve()),
                ],
                "scenario_profiles": [
                    str((repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json").resolve()),
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    result = run_cli(
        "run-sweep-analysis",
        "--sweep-spec",
        str(sweep_spec_path),
        "--sweep-root",
        str(sweep_root),
        cwd=repo_root,
    )
    assert result.returncode == 0

    result = run_cli(
        "run-visualization-packaging",
        "--run-root",
        str(run_root),
        "--sweep-root",
        str(sweep_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Visualization packaging completed" in result.stdout

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    bundle = json.loads((run_root / "reports" / "visualization_bundle.json").read_text(encoding="utf-8"))

    assert manifest["artifact_index"]["visualization_bundle"] == "reports/visualization_bundle.json"
    assert bundle["metadata"]["mode"] == "decode"
    assert bundle["sweep_view"] is not None


def test_run_visualization_packaging_rejects_missing_top_level_report_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-viz-cli-missing-report"

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
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    result = run_cli(
        "run-visualization-packaging",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Visualization packaging: ERROR" in result.stdout
    assert "prefill" in result.stdout.lower()
    assert "Traceback" not in result.stderr
