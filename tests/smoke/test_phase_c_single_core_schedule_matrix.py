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
    ("scenario_profile", "expected_mode"),
    [
        pytest.param("profiles/scenarios/prefill_seq128.json", "prefill", id="single-core-prefill"),
        pytest.param("profiles/scenarios/decode_token1_kv2048.json", "decode", id="single-core-decode"),
    ],
)
def test_phase_c_single_core_schedule_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    scenario_profile: str,
    expected_mode: str,
) -> None:
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"single-core-{Path(scenario_profile).stem}",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path=scenario_profile,
        final_stage="schedule",
    )

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    schedule_ir = json.loads((run_root / "artifacts" / "schedule_ir.json").read_text(encoding="utf-8"))
    blocks = schedule_ir["blocks"]

    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["schedule_ir"] == "artifacts/schedule_ir.json"
    assert schedule_ir["core_mode"] == "single-core"
    assert blocks
    assert {block["core_id"] for block in blocks} == {0}
    assert all("Core Link" not in block["resource_set"] for block in blocks)
    assert all(not block["barrier_in"] and not block["barrier_out"] for block in blocks)
    assert all(block["duration_slots"] >= 1 for block in blocks)
    assert max(block["issue_slot"] for block in blocks) > 0

    if expected_mode == "prefill":
        compute_blocks = [block for block in blocks if block["stage"] == "compute"]
        assert compute_blocks
        assert any(block["macro_op"] == "WDQ_GEMM" for block in compute_blocks)
        assert any(block["macro_op"] == "SDPA" for block in compute_blocks)
        helper_compute_blocks = [block for block in compute_blocks if block["macro_op"] == "SHAPE_HELPER"]
        assert helper_compute_blocks
        assert all(block["tiling_candidate_id"] is None for block in helper_compute_blocks)
    else:
        decode_blocks = [
            block
            for block in blocks
            if block["macro_op"] == "SDPA_DECODE" and block["stage"] == "compute"
        ]
        assert decode_blocks
        assert all(".m1." in block["tiling_candidate_id"] for block in decode_blocks)
