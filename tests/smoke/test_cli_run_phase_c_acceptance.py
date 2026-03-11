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


def test_run_phase_c_acceptance_accepts_explicit_run_roots(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    report_root = tmp_path / "phase-c-cli-report"
    run_roots = [
        prepared_smoke_run_root_factory(
            target_run_root=tmp_path / "single-prefill",
            target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_relative_path="profiles/scenarios/prefill_seq128.json",
            final_stage="visualization_bundle",
        ),
        prepared_smoke_run_root_factory(
            target_run_root=tmp_path / "single-decode",
            target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
            final_stage="visualization_bundle",
        ),
        prepared_smoke_run_root_factory(
            target_run_root=tmp_path / "dual-prefill",
            target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
            scenario_relative_path="profiles/scenarios/prefill_seq128.json",
            final_stage="visualization_bundle",
        ),
        prepared_smoke_run_root_factory(
            target_run_root=tmp_path / "dual-decode",
            target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
            scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
            final_stage="visualization_bundle",
        ),
    ]

    result = run_cli(
        "run-phase-c-acceptance",
        "--report-root",
        str(report_root),
        "--run-root",
        str(run_roots[0]),
        "--run-root",
        str(run_roots[1]),
        "--run-root",
        str(run_roots[2]),
        "--run-root",
        str(run_roots[3]),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Phase C acceptance completed" in result.stdout
    assert "phase_c_acceptance_report.json" in result.stdout
    assert "Matrix summary: status=ready_for_acceptance" in result.stdout
    assert "planner_blocked=0" in result.stdout
    assert "downstream_blocked=0" in result.stdout
    assert "Traceback" not in result.stderr

    report = json.loads((report_root / "reports" / "phase_c_acceptance_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "ready_for_acceptance"
    assert report["matrix_coverage"]["planner_blocked_case_count"] == 0
    assert report["matrix_coverage"]["downstream_blocked_case_count"] == 0


def test_run_phase_c_acceptance_rejects_empty_workspace_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = tmp_path / "empty-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    result = run_cli(
        "run-phase-c-acceptance",
        "--report-root",
        str(workspace_root),
        "--workspace-root",
        str(workspace_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Phase C acceptance: ERROR" in result.stdout
    assert "no run roots" in result.stdout.lower()
    assert "Traceback" not in result.stderr
