import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


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


@pytest.mark.local_smoke
def test_phase_d_sweep_local_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sweep_root = tmp_path / "phase-d-sweep-local"
    sweep_spec_path = tmp_path / "phase-d-sweep-local-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "phase-d-sweep-local",
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

    report = json.loads((sweep_root / "reports" / "sweep_delta_report.json").read_text(encoding="utf-8"))

    assert report["completed_run_count"] == 2
    assert report["failed_run_count"] == 0
    assert len(report["run_records"]) == 2
    assert len(report["comparisons"]) == 1
    assert {record["mode"] for record in report["run_records"]} == {"prefill"}
    assert {record["schedule_kind"] for record in report["run_records"]} == {"single-core", "dual-core"}
    assert not report["issues"]


@pytest.mark.milestone_matrix
def test_phase_d_sweep_foundation_matrix(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sweep_root = tmp_path / "phase-d-sweep-matrix"
    sweep_spec_path = tmp_path / "phase-d-sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "phase-d-sweep-foundation",
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

    report = json.loads((sweep_root / "reports" / "sweep_delta_report.json").read_text(encoding="utf-8"))

    assert report["completed_run_count"] == 4
    assert report["failed_run_count"] == 0
    assert len(report["run_records"]) == 4
    assert len(report["comparisons"]) == 2
    assert {record["mode"] for record in report["run_records"]} == {"prefill", "decode"}
    assert {record["schedule_kind"] for record in report["run_records"]} == {"single-core", "dual-core"}
    assert not report["issues"]
