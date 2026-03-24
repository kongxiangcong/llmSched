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


def test_run_diagnosis_analysis_writes_reserved_output_directory(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-cli",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="frontend",
    )

    result = run_cli(
        "run-diagnosis-analysis",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Diagnosis analysis completed" in result.stdout

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    diagnosis_dir = run_root / "reports" / "diagnosis"
    assert diagnosis_dir.is_dir()
    assert (diagnosis_dir / "trace").is_dir()
    assert (diagnosis_dir / "dataset").is_dir()
    assert manifest["artifact_index"]["diagnosis_reports_dir"] == "reports/diagnosis"


def test_run_diagnosis_analysis_rejects_missing_manifest_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-diagnosis-cli-missing-manifest"
    run_root.mkdir(parents=True, exist_ok=True)

    result = run_cli(
        "run-diagnosis-analysis",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Diagnosis analysis: ERROR" in result.stdout
    assert "manifest" in result.stdout.lower()
    assert "Traceback" not in result.stderr
