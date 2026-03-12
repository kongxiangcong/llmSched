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


def test_run_performance_estimation_writes_artifacts_for_single_core(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-perf-cli-single",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="descriptor",
    )

    result = run_cli("run-performance-estimation", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    analysis_ir = json.loads((run_root / "artifacts" / "perf_analysis_ir.json").read_text(encoding="utf-8"))
    perf_report = json.loads((run_root / "reports" / "perf_summary_report.json").read_text(encoding="utf-8"))

    assert manifest["artifact_index"]["perf_analysis_ir"] == "artifacts/perf_analysis_ir.json"
    assert manifest["artifact_index"]["perf_summary_report"] == "reports/perf_summary_report.json"
    assert analysis_ir["records"]
    assert perf_report["totals"]["estimated_cycles"] > 0.0
    assert perf_report["totals"]["critical_path_cycles"] > 0.0
    assert perf_report["totals"]["critical_path_cycles"] == perf_report["schedule_makespan_slots"]
    assert perf_report["phase_attribution"]["projection"]["cycles_per_token"] >= 0.0
    assert perf_report["phase_attribution"]["other"]["bytes_per_token"] >= 0.0
    assert perf_report["phase_attribution"]["projection"]["occupied_slots"] >= 0.0
    assert perf_report["phase_attribution"]["other"]["occupied_slots_per_token"] >= 0.0


def test_run_performance_estimation_rejects_missing_descriptor_without_traceback(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-perf-missing-descriptor",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="schedule",
    )

    result = run_cli(
        "run-performance-estimation",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Performance estimation: ERROR" in result.stdout
    assert "descriptor" in result.stdout.lower()
    assert "Traceback" not in result.stderr
