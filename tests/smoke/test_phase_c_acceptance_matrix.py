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
@pytest.mark.milestone_matrix
def test_phase_c_acceptance_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = tmp_path / "phase-c-acceptance-workspace"
    runs_root = workspace_root / "runs"

    run_roots = [
        prepared_smoke_run_root_factory(
            target_run_root=runs_root / "single-prefill",
            target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_relative_path="profiles/scenarios/prefill_seq128.json",
            final_stage="visualization_bundle",
        ),
        prepared_smoke_run_root_factory(
            target_run_root=runs_root / "single-decode",
            target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
            final_stage="visualization_bundle",
        ),
        prepared_smoke_run_root_factory(
            target_run_root=runs_root / "dual-prefill",
            target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
            scenario_relative_path="profiles/scenarios/prefill_seq128.json",
            final_stage="visualization_bundle",
        ),
        prepared_smoke_run_root_factory(
            target_run_root=runs_root / "dual-decode",
            target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
            scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
            final_stage="visualization_bundle",
        ),
    ]

    result = run_cli(
        "run-phase-c-acceptance",
        "--report-root",
        str(workspace_root),
        "--workspace-root",
        str(workspace_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Phase C acceptance completed" in result.stdout
    assert "Matrix summary: status=ready_for_acceptance" in result.stdout
    assert "planner_blocked=0" in result.stdout
    assert "downstream_blocked=0" in result.stdout

    report_path = workspace_root / "reports" / "phase_c_acceptance_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "ready_for_acceptance"
    assert report["matrix_coverage"]["present_case_ids"] == [
        "single-core:prefill",
        "single-core:decode",
        "dual-core:prefill",
        "dual-core:decode",
    ]
    assert report["matrix_coverage"]["planner_blocked_case_count"] == 0
    assert report["matrix_coverage"]["downstream_blocked_case_count"] == 0
    assert report["remaining_gaps"] == []
    for run_root in run_roots:
        assert (run_root / "reports" / "memory_planner_closure_report.json").is_file()
