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
def test_phase_e_visualization_workbench_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    schedule_kind: str,
    mode: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}-workbench",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
        final_stage="visualization_bundle",
    )
    result = run_cli("run-visualization-workbench", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    workbench = json.loads((run_root / "workbench" / "workbench_manifest.json").read_text(encoding="utf-8"))

    assert workbench["metadata"]["mode"] == mode
    assert workbench["metadata"]["schedule_kind"] == schedule_kind
    assert workbench["default_panel"] == "summary"
    assert "graph" in workbench["available_panels"]
    assert "memory" in workbench["available_panels"]
    assert (run_root / "workbench" / "index.html").is_file()
