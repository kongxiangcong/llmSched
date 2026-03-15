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
            marks=pytest.mark.local_smoke,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "dual-core",
            marks=pytest.mark.milestone_matrix,
        ),
    ],
)
def test_phase_d_prefill_foundation_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    schedule_kind: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-prefill-eval",
        target_relative_path=target_profile,
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    result = run_cli("run-prefill-evaluation", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    report = json.loads((run_root / "reports" / "prefill_evaluation_report.json").read_text(encoding="utf-8"))

    assert report["scenario_name"] == "prefill_seq128"
    assert report["schedule_kind"] == schedule_kind
    assert report["throughput"]["total_tokens"] == 128
    assert report["throughput"]["estimated_cycles"] > 0.0
    assert report["throughput"]["fitted_work_cycles"] >= report["throughput"]["estimated_cycles"]
    assert report["throughput"]["projection_fitted_work_cycles"] >= 0.0
    assert "memory_hotspot" in report
    assert report["memory_hotspot"]["hottest_region_utilization"] >= 0.0
    assert report["macro_hotspots"]
