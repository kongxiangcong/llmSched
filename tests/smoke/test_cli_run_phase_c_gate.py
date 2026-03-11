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
def test_run_phase_c_gate_passes_ready_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = tmp_path / "phase-c-gate-workspace"
    runs_root = workspace_root / "runs"

    prepared_smoke_run_root_factory(
        target_run_root=runs_root / "single-prefill",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="visualization_bundle",
    )
    prepared_smoke_run_root_factory(
        target_run_root=runs_root / "single-decode",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="visualization_bundle",
    )
    prepared_smoke_run_root_factory(
        target_run_root=runs_root / "dual-prefill",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="visualization_bundle",
    )
    prepared_smoke_run_root_factory(
        target_run_root=runs_root / "dual-decode",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="visualization_bundle",
    )

    result = run_cli(
        "run-phase-c-gate",
        "--report-root",
        str(workspace_root),
        "--workspace-root",
        str(workspace_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Phase C gate completed" in result.stdout
    assert "Matrix summary: status=ready_for_acceptance" in result.stdout
    assert "Phase C gate: PASS" in result.stdout
    assert "Traceback" not in result.stderr

    report = json.loads((workspace_root / "reports" / "phase_c_acceptance_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "ready_for_acceptance"


def test_run_phase_c_gate_blocks_incomplete_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = tmp_path / "phase-c-gate-incomplete-workspace"
    runs_root = workspace_root / "runs"

    prepared_smoke_run_root_factory(
        target_run_root=runs_root / "single-prefill",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="visualization_bundle",
    )
    prepared_smoke_run_root_factory(
        target_run_root=runs_root / "single-decode",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="visualization_bundle",
    )
    prepared_smoke_run_root_factory(
        target_run_root=runs_root / "dual-prefill",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="visualization_bundle",
    )

    result = run_cli(
        "run-phase-c-gate",
        "--report-root",
        str(workspace_root),
        "--workspace-root",
        str(workspace_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Phase C gate completed" in result.stdout
    assert "Matrix summary: status=in_progress" in result.stdout
    assert "missing=1" in result.stdout
    assert "Phase C gate: BLOCKED" in result.stdout
    assert "Traceback" not in result.stderr

    report = json.loads((workspace_root / "reports" / "phase_c_acceptance_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "in_progress"
    assert report["matrix_coverage"]["missing_case_ids"] == ["dual-core:decode"]
