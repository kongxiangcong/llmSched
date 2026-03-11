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


def test_run_sweep_analysis_writes_delta_report(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sweep_root = tmp_path / "sweep-cli"
    sweep_spec_path = tmp_path / "sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "cli-sweep",
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str(
                    (repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()
                ),
                "target_profiles": [
                    str((repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()),
                    str((repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json").resolve()),
                ],
                "scenario_profiles": [
                    str((repo_root / "profiles" / "scenarios" / "prefill_seq128.json").resolve()),
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
    assert "Sweep analysis completed" in result.stdout

    report = json.loads((sweep_root / "reports" / "sweep_delta_report.json").read_text(encoding="utf-8"))
    assert report["sweep_name"] == "cli-sweep"
    assert report["completed_run_count"] == 2
    assert report["failed_run_count"] == 0
    assert len(report["comparisons"]) == 1


def test_run_sweep_analysis_rejects_invalid_baseline_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sweep_root = tmp_path / "invalid-baseline"
    sweep_spec_path = tmp_path / "invalid-sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "invalid-cli-sweep",
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str(
                    (repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()
                ),
                "target_profiles": [
                    str((repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json").resolve()),
                ],
                "scenario_profiles": [
                    str((repo_root / "profiles" / "scenarios" / "prefill_seq128.json").resolve()),
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

    assert result.returncode == 1
    assert "Sweep analysis: ERROR" in result.stdout
    assert "baseline" in result.stdout.lower()
    assert "Traceback" not in result.stderr
