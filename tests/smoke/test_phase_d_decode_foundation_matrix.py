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
    ("target_profile", "schedule_kind"),
    [
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "single-core",
            marks=pytest.mark.milestone_matrix,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "dual-core",
            marks=pytest.mark.local_smoke,
        ),
    ],
)
def test_phase_d_decode_foundation_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    schedule_kind: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-decode-eval",
        target_relative_path=target_profile,
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )
    result = run_cli("run-decode-evaluation", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    report = json.loads((run_root / "reports" / "decode_evaluation_report.json").read_text(encoding="utf-8"))

    assert report["scenario_name"] == "decode_token1_kv2048"
    assert report["schedule_kind"] == schedule_kind
    assert report["kv_len"] == 2048
    assert report["sdpa_decode_present"] is True
    assert report["token_latency"]["estimated_cycles"] > 0.0
    assert report["token_latency"]["fitted_work_cycles"] >= report["token_latency"]["estimated_cycles"]
    assert report["token_latency"]["kv_io_fitted_work_cycles"] >= 0.0
    assert report["kv_summary"]["kv_related_fitted_work_cycle_share"] >= 0.0
    assert "memory_hotspot" in report
    assert report["memory_hotspot"]["hottest_region_utilization"] >= 0.0
    assert report["bandwidth_pressure_summary"]["peak_bandwidth_pressure"] >= 0.0
    assert report["vmem_pressure_summary"]["hottest_region"] is not None
    assert report["macro_hotspots"]
    assert report["node_hotspots"]
    assert report["node_hotspots"][0]["fitted_work_cycles"] >= report["node_hotspots"][0]["estimated_cycles"]
    assert report["node_hotspots"][0]["fitted_cycle_share"] >= 0.0
    assert report["layer_breakdown"]
    assert report["layer_breakdown"][0]["fitted_work_cycles"] >= report["layer_breakdown"][0]["estimated_cycles"]
    assert report["layer_breakdown"][0]["fitted_cycle_share"] >= 0.0
