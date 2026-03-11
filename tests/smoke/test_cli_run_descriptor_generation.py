import json
import os
import subprocess
import sys
from pathlib import Path


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


def test_run_descriptor_generation_writes_artifacts_for_single_core(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-descriptor-cli-single",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="schedule",
    )

    result = run_cli("run-descriptor-generation", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    descriptor_ir = json.loads((run_root / "artifacts" / "descriptor_ir.json").read_text(encoding="utf-8"))
    packed_bundle = json.loads((run_root / "artifacts" / "packed_descriptor_bundle.json").read_text(encoding="utf-8"))
    coverage_report = json.loads((run_root / "reports" / "isa_coverage_report.json").read_text(encoding="utf-8"))

    assert manifest["artifact_index"]["descriptor_ir"] == "artifacts/descriptor_ir.json"
    assert manifest["artifact_index"]["packed_descriptor_bundle"] == "artifacts/packed_descriptor_bundle.json"
    assert manifest["artifact_index"]["isa_coverage_report"] == "reports/isa_coverage_report.json"
    assert descriptor_ir["descriptors"]
    assert packed_bundle["container_format"] == "aligned-flat-v1"
    assert packed_bundle["record_alignment_bytes"] == 64
    assert packed_bundle["stream_total_bytes"] >= len(packed_bundle["descriptors"]) * 64
    assert len(packed_bundle["descriptors"]) == len(descriptor_ir["descriptors"])
    assert len(packed_bundle["descriptors"][0]["word_hex"]) == 8
    assert packed_bundle["descriptors"][0]["stream_offset_bytes"] == 0
    assert packed_bundle["descriptors"][0]["stream_hex"].startswith("0x")
    assert coverage_report["mapped_descriptor_count"] > 0


def test_run_descriptor_generation_rejects_missing_schedule_without_traceback(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-descriptor-missing-schedule",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="tile",
    )

    result = run_cli(
        "run-descriptor-generation",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Descriptor generation: ERROR" in result.stdout
    assert "schedule" in result.stdout.lower()
    assert "Traceback" not in result.stderr
