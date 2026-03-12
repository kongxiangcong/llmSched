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


def test_run_phase_d_compare_writes_report(
    tmp_path: Path,
    prepared_smoke_sweep_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sweep_root = prepared_smoke_sweep_root_factory(
        target_sweep_root=tmp_path / "phase-d-compare-cli",
        baseline_target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        target_relative_paths=[
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/targets/riscv_npu_dual_core_v1.json",
        ],
        scenario_relative_paths=["profiles/scenarios/prefill_seq128.json"],
        sweep_name="phase-d-compare-cli",
    )

    result = run_cli(
        "run-phase-d-compare",
        "--sweep-root",
        str(sweep_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Phase D compare completed" in result.stdout

    report = json.loads((sweep_root / "reports" / "phase_d_compare_report.json").read_text(encoding="utf-8"))
    assert report["source_sweep_name"] == "phase-d-compare-cli"
    assert report["prefill_compare_count"] == 1
    assert report["decode_compare_count"] == 0
    assert len(report["prefill_compares"]) == 1


def test_run_phase_d_compare_rejects_missing_sweep_report_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sweep_root = tmp_path / "phase-d-compare-missing"
    sweep_root.mkdir(parents=True, exist_ok=True)

    result = run_cli(
        "run-phase-d-compare",
        "--sweep-root",
        str(sweep_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Phase D compare: ERROR" in result.stdout
    assert "sweep_delta_report" in result.stdout
    assert "Traceback" not in result.stderr
