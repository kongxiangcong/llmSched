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


@pytest.mark.parametrize(
    ("target_profile", "scenario_profile", "schedule_kind"),
    [
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "single-core",
            marks=pytest.mark.local_smoke,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "single-core",
            marks=pytest.mark.milestone_matrix,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "dual-core",
            marks=pytest.mark.milestone_matrix,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "dual-core",
            marks=pytest.mark.local_smoke,
        ),
    ],
)
def test_phase_d_perf_foundation_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    schedule_kind: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}-perf",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
        final_stage="descriptor",
    )
    result = run_cli("run-performance-estimation", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    analysis_ir = json.loads((run_root / "artifacts" / "perf_analysis_ir.json").read_text(encoding="utf-8"))
    perf_report = json.loads((run_root / "reports" / "perf_summary_report.json").read_text(encoding="utf-8"))

    assert analysis_ir["records"]
    assert perf_report["schedule_kind"] == schedule_kind
    assert perf_report["schedule_makespan_slots"] > 0
    assert perf_report["per_core_makespan_slots"]
    assert perf_report["data_movement_read_bytes_by_address_space"]
    assert perf_report["vmem_region_peak_bytes"]
    assert perf_report["vmem_region_capacity_bytes"]
    assert perf_report["vmem_region_peak_utilization"]
    assert perf_report["totals"]["estimated_cycles"] > 0.0
    assert perf_report["bottleneck_counts"].get("compute-bound", 0) > 0
    if schedule_kind == "dual-core":
        assert perf_report["bottleneck_counts"].get("sync-bound", 0) > 0
        assert perf_report["schedule_transfer_slots"] > 0
    else:
        assert perf_report["bottleneck_counts"].get("sync-bound", 0) == 0
        assert perf_report["schedule_transfer_slots"] == 0
