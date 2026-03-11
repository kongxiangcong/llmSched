from pathlib import Path

from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.manifest import RunManifest


def test_build_run_layout_returns_canonical_directories(tmp_path: Path) -> None:
    run_root = tmp_path / "run-001"

    layout = build_run_layout(run_root)

    assert layout.run_root == run_root
    assert layout.artifacts_dir == run_root / "artifacts"
    assert layout.reports_dir == run_root / "reports"
    assert layout.logs_dir == run_root / "logs"
    assert layout.dumps_dir == run_root / "dumps"


def test_run_manifest_serializes_and_round_trips() -> None:
    manifest = RunManifest(
        run_id="run-001",
        contract_version="phase-a.v1",
        status="initialized",
        model_path="models/gemma3_1b/model_q4f16.onnx",
        target_profile_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_profile_path="profiles/scenarios/prefill_seq128.json",
        artifact_index={
            "manifest": "manifest.json",
            "log": "logs/run.log",
        },
    )

    payload = manifest.model_dump(mode="json")
    restored = RunManifest.model_validate(payload)

    assert restored == manifest
    assert restored.artifact_index["manifest"] == "manifest.json"
