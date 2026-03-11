from pathlib import Path

import pytest

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


@pytest.mark.parametrize(
    ("target_profile", "scenario_profile", "schedule_kind", "artifact_name"),
    [
        (
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "single-core",
            "schedule_ir",
        ),
        (
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            "dual-core",
            "dual_core_schedule_ir",
        ),
    ],
)
def test_run_descriptor_generation_writes_descriptor_and_coverage_artifacts(
    tmp_path: Path,
    prepared_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    schedule_kind: str,
    artifact_name: str,
) -> None:
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport
    from llm_sched.contracts.packed_descriptor_bundle import PackedDescriptorBundle
    from llm_sched.ir.descriptor_ir import DescriptorIR
    from llm_sched.pipeline import run_descriptor_generation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / f"run-descriptor-{schedule_kind}",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
        final_stage="schedule",
    )

    result = run_descriptor_generation(run_root)

    assert result.status == "completed"
    assert result.descriptor_ir_path == run_root / "artifacts" / "descriptor_ir.json"
    assert result.packed_descriptor_bundle_path == run_root / "artifacts" / "packed_descriptor_bundle.json"
    assert result.coverage_report_path == run_root / "reports" / "isa_coverage_report.json"

    descriptor_ir = DescriptorIR.model_validate_json(result.descriptor_ir_path.read_text(encoding="utf-8"))
    packed_bundle = PackedDescriptorBundle.model_validate_json(
        result.packed_descriptor_bundle_path.read_text(encoding="utf-8")
    )
    coverage = ISACoverageReport.model_validate_json(result.coverage_report_path.read_text(encoding="utf-8"))
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))

    assert descriptor_ir.descriptors
    assert len(packed_bundle.descriptors) == len(descriptor_ir.descriptors)
    assert packed_bundle.container_format == "aligned-flat-v1"
    assert packed_bundle.record_alignment_bytes == 64
    assert packed_bundle.stream_total_bytes >= len(packed_bundle.descriptors) * 64
    assert packed_bundle.stream_hex.startswith("0x")
    assert packed_bundle.descriptors[0].stream_hex.startswith("0x")
    assert packed_bundle.descriptors[0].record_index == 0
    assert packed_bundle.descriptors[0].stream_offset_bytes == 0
    assert packed_bundle.descriptors[0].stream_size_bytes == 64
    assert packed_bundle.descriptors[0].word_order == "lsw-first"
    assert packed_bundle.descriptors[0].byte_order == "little-endian"
    assert coverage.schedule_kind == schedule_kind
    assert coverage.mapped_descriptor_count == len(descriptor_ir.descriptors)
    assert artifact_name in manifest.artifact_index
    assert manifest.artifact_index["descriptor_ir"] == "artifacts/descriptor_ir.json"
    assert manifest.artifact_index["packed_descriptor_bundle"] == "artifacts/packed_descriptor_bundle.json"
    assert manifest.artifact_index["isa_coverage_report"] == "reports/isa_coverage_report.json"
    assert summary.status == "completed"
    assert summary.exit_code == 0
