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
        pytest.param("profiles/scenarios/prefill_seq128.json", "prefill", id="dual-core-prefill"),
        pytest.param("profiles/scenarios/decode_token1_kv2048.json", "decode", id="dual-core-decode"),
    ],
)
def test_phase_c_dual_core_schedule_matrix(
    tmp_path: Path,
    scenario_profile: str,
    expected_mode: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / f"dual-core-{Path(scenario_profile).stem}"

    for args in [
        (
            "init-run",
            "--run-root",
            str(run_root),
            "--model-path",
            "models/gemma3_1b/model_q4f16.onnx",
            "--target-profile",
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "--scenario-profile",
            scenario_profile,
        ),
        ("run-frontend-analysis", "--run-root", str(run_root)),
        ("run-memory-planning", "--run-root", str(run_root)),
        ("run-tile-planning", "--run-root", str(run_root)),
        ("run-dual-core-scheduling", "--run-root", str(run_root)),
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    schedule_ir = json.loads((run_root / "artifacts" / "dual_core_schedule_ir.json").read_text(encoding="utf-8"))
    blocks = schedule_ir["blocks"]

    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["dual_core_schedule_ir"] == "artifacts/dual_core_schedule_ir.json"
    assert schedule_ir["core_mode"] == "dual-core"
    assert blocks
    assert {block["core_id"] for block in blocks if block["stage"] != "transfer"} == {0, 1}

    transfer_blocks = [block for block in blocks if block["stage"] == "transfer"]
    assert transfer_blocks
    assert all(block["peer_core_id"] in {0, 1} for block in transfer_blocks)
    assert all(block["peer_core_id"] != block["core_id"] for block in transfer_blocks)
    assert all(block["barrier_in"] and block["barrier_out"] for block in transfer_blocks)
    assert all(block["resource_set"] in (["Core Link"], ["DMA"]) for block in transfer_blocks)
    assert all(block["depends_on"] for block in transfer_blocks)
    assert all(block["duration_slots"] > 0 for block in transfer_blocks)
    assert all(block["sync_cost_cycles"] > 0 for block in transfer_blocks)
    assert any(block["issue_slot"] > 0 for block in blocks)

    if expected_mode == "prefill":
        compute_blocks = [block for block in blocks if block["stage"] == "compute"]
        assert compute_blocks
        assert any(block["macro_op"] in {"WDQ_GEMM", "RMSNORM_GEMM"} for block in compute_blocks)
        untiled_compute_blocks = [
            block for block in compute_blocks if block["macro_op"] in {"RMSNORM", "ELEM_ADD"}
        ]
        assert untiled_compute_blocks
        assert all(block["tiling_candidate_id"] is None for block in untiled_compute_blocks)
    else:
        decode_blocks = [
            block
            for block in blocks
            if block["macro_op"] == "SDPA_DECODE" and block["stage"] == "compute"
        ]
        assert decode_blocks
        assert all(".m1." in block["tiling_candidate_id"] for block in decode_blocks)
