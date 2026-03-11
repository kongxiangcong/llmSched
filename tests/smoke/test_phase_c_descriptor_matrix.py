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
        (
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "single-core",
        ),
        (
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "single-core",
        ),
        (
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "dual-core",
        ),
        (
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "dual-core",
        ),
    ],
)
def test_phase_c_descriptor_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    schedule_kind: str,
) -> None:
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}-descriptor",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
        final_stage="descriptor",
    )

    descriptor_ir = json.loads((run_root / "artifacts" / "descriptor_ir.json").read_text(encoding="utf-8"))
    packed_bundle = json.loads((run_root / "artifacts" / "packed_descriptor_bundle.json").read_text(encoding="utf-8"))
    coverage_report = json.loads((run_root / "reports" / "isa_coverage_report.json").read_text(encoding="utf-8"))

    assert descriptor_ir["descriptors"]
    assert packed_bundle["container_format"] == "aligned-flat-v1"
    assert packed_bundle["record_alignment_bytes"] == 64
    assert packed_bundle["stream_total_bytes"] >= len(packed_bundle["descriptors"]) * 64
    assert len(packed_bundle["descriptors"]) == len(descriptor_ir["descriptors"])
    assert packed_bundle["descriptors"][0]["stream_offset_bytes"] == 0
    assert packed_bundle["descriptors"][0]["stream_hex"].startswith("0x")
    assert coverage_report["schedule_kind"] == schedule_kind
    assert coverage_report["mapped_descriptor_count"] == len(descriptor_ir["descriptors"])
    assert coverage_report["unmapped_block_count"] >= 0

    transfer_descriptors = [
        descriptor
        for descriptor in descriptor_ir["descriptors"]
        if descriptor["transfer_fields"] is not None
    ]
    if schedule_kind == "dual-core":
        assert transfer_descriptors
    else:
        assert transfer_descriptors == []
