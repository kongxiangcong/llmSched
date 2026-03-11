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
    ("target_profile", "scenario_profile", "expected_overflow_regions"),
    [
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            set(),
            id="single-core-prefill",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            set(),
            id="single-core-decode",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            set(),
            id="dual-core-prefill",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            set(),
            id="dual-core-decode",
        ),
    ],
)
def test_phase_c_memory_planner_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    expected_overflow_regions: set[str],
) -> None:
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
        final_stage="memory",
    )

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    memory_plan = json.loads((run_root / "artifacts" / "memory_plan.json").read_text(encoding="utf-8"))

    overflow_regions = {
        diagnostic["region_name"]
        for diagnostic in memory_plan["diagnostics"]
        if diagnostic["status"] == "overflow"
    }
    unresolved_addresses = [
        diagnostic
        for diagnostic in memory_plan["address_diagnostics"]
        if diagnostic["status"] == "unresolved"
    ]

    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["memory_plan"] == "artifacts/memory_plan.json"
    assert memory_plan["kv_formulas"]
    assert memory_plan["storage_bindings"]
    assert memory_plan["allocations"][0]["lifetime_bucket"] in {"preload", "compute", "store", "persist"}
    assert memory_plan["allocations"][0]["backing_store"] in {"vmem-local", "ddr-backed-staged", "ddr-persistent"}
    assert all(
        allocation["storage_binding_id"] is not None
        for allocation in memory_plan["allocations"]
        if allocation["backing_store"] != "vmem-local"
    )
    assert len(memory_plan["address_diagnostics"]) >= len(memory_plan["kv_formulas"])
    assert overflow_regions == expected_overflow_regions
    assert not unresolved_addresses
    assert "peak_lifetime_bucket" in memory_plan["region_summaries"]["ping"]
    assert "peak_bytes_by_memory_class" in memory_plan["region_summaries"]["ping"]
    assert "peak_bytes_by_backing_store" in memory_plan["region_summaries"]["ping"]
    assert "required_bytes_by_memory_class" in memory_plan["diagnostics"][0]
    assert "required_bytes_by_backing_store" in memory_plan["diagnostics"][0]
    assert "weight" in {diagnostic["address_kind"] for diagnostic in memory_plan["address_diagnostics"]}
    assert "quant" in {diagnostic["address_kind"] for diagnostic in memory_plan["address_diagnostics"]}
    assert memory_plan["region_summaries"]["quant"]["fits"] is True
    assert memory_plan["region_summaries"]["wdq_reserved"]["fits"] is True
