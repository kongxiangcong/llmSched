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
    ("target_profile", "scenario_profile", "expected_mode"),
    [
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "prefill",
            id="single-core-prefill",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "decode",
            id="single-core-decode",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "prefill",
            id="dual-core-prefill",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "decode",
            id="dual-core-decode",
        ),
    ],
)
def test_phase_c_tile_planner_matrix(
    tmp_path: Path,
    target_profile: str,
    scenario_profile: str,
    expected_mode: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}"

    for args in [
        (
            "init-run",
            "--run-root",
            str(run_root),
            "--model-path",
            "models/gemma3_1b/model_q4f16.onnx",
            "--target-profile",
            target_profile,
            "--scenario-profile",
            scenario_profile,
        ),
        ("run-frontend-analysis", "--run-root", str(run_root)),
        ("run-memory-planning", "--run-root", str(run_root)),
        ("run-tile-planning", "--run-root", str(run_root)),
    ]:
        result = run_cli(*args, cwd=repo_root)
        assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    tiling_plan = json.loads((run_root / "artifacts" / "tiling_plan.json").read_text(encoding="utf-8"))
    candidates = tiling_plan["candidates"]

    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["tiling_plan"] == "artifacts/tiling_plan.json"
    assert candidates
    assert "rank" in candidates[0]
    assert "ranking_reason" in candidates[0]
    assert "storage_binding_ids" in candidates[0]["resource_summary"]
    assert any(candidate["resource_summary"]["storage_binding_ids"] for candidate in candidates)

    if expected_mode == "prefill":
        gemm_candidates = [candidate for candidate in candidates if candidate["macro_op"] in {"GEMM", "WDQ_GEMM", "RMSNORM_GEMM"}]
        assert gemm_candidates
        assert max(candidate["m_tile"] for candidate in gemm_candidates) > 1
    else:
        decode_candidates = [candidate for candidate in candidates if candidate["macro_op"] == "SDPA_DECODE"]
        assert decode_candidates
        assert all(candidate["m_tile"] == 1 for candidate in decode_candidates)
