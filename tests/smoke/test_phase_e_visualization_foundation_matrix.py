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
    ("target_profile", "scenario_profile", "schedule_kind", "mode"),
    [
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "single-core",
            "prefill",
            marks=pytest.mark.local_smoke,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "single-core",
            "decode",
            marks=pytest.mark.milestone_matrix,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "dual-core",
            "prefill",
            marks=pytest.mark.milestone_matrix,
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "dual-core",
            "decode",
            marks=pytest.mark.local_smoke,
        ),
    ],
)
def test_phase_e_visualization_foundation_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    schedule_kind: str,
    mode: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    final_stage = "prefill_eval" if mode == "prefill" else "decode_eval"
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}-viz",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
        final_stage=final_stage,
    )
    result = run_cli("run-visualization-packaging", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    bundle = json.loads((run_root / "reports" / "visualization_bundle.json").read_text(encoding="utf-8"))

    assert bundle["metadata"]["mode"] == mode
    assert bundle["metadata"]["schedule_kind"] == schedule_kind
    assert bundle["graph_view"]["node_count"] > 0
    assert bundle["timeline_view"]["total_block_count"] > 0
    assert bundle["coverage_view"]["mapped_descriptor_count"] > 0
    assert bundle["vmem_view"]["regions"]
    if mode == "decode":
        assert bundle["kv_view"]["kv_len"] == 2048
    else:
        assert bundle["report_summary"]["report_kind"] == "prefill"
