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
    ("target_profile", "scenario_profile", "schedule_kind", "report_kind"),
    [
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            "single-core",
            "prefill",
            marks=pytest.mark.local_smoke,
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
def test_phase_f_architecture_diagnosis_matrix(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    target_profile: str,
    scenario_profile: str,
    schedule_kind: str,
    report_kind: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    final_stage = "prefill_eval" if report_kind == "prefill" else "decode_eval"
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}-diag",
        target_relative_path=target_profile,
        scenario_relative_path=scenario_profile,
        final_stage=final_stage,
    )

    for command in ("run-diagnosis-analysis", "run-diagnosis-packaging", "run-diagnosis-workbench"):
        result = run_cli(command, "--run-root", str(run_root), cwd=repo_root)
        assert result.returncode == 0, result.stderr

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    support_matrix_report = json.loads(
        (run_root / "reports" / "diagnosis" / "support_matrix_report.json").read_text(encoding="utf-8")
    )
    performance_diagnostics_report = json.loads(
        (run_root / "reports" / "diagnosis" / "performance_diagnostics_report.json").read_text(encoding="utf-8")
    )
    architecture_assessment_report = json.loads(
        (run_root / "reports" / "diagnosis" / "architecture_assessment_report.json").read_text(encoding="utf-8")
    )
    chain_summary = json.loads(
        (run_root / "reports" / "diagnosis" / "diagnosis_chain_summary.json").read_text(encoding="utf-8")
    )
    diagnosis_bundle = json.loads((run_root / "reports" / "diagnosis_bundle.json").read_text(encoding="utf-8"))
    diagnosis_workbench = json.loads(
        (run_root / "diagnosis_workbench" / "workbench_manifest.json").read_text(encoding="utf-8")
    )

    required_artifacts = [
        run_root / "reports" / "diagnosis" / "model_structure_report.json",
        run_root / "reports" / "diagnosis" / "operator_representation_report.json",
        run_root / "reports" / "diagnosis" / "resource_demand_report.json",
        run_root / "reports" / "diagnosis" / "support_matrix_report.json",
        run_root / "reports" / "diagnosis" / "schedule_diagnostics_report.json",
        run_root / "reports" / "diagnosis" / "performance_diagnostics_report.json",
        run_root / "reports" / "diagnosis" / "roofline_report.json",
        run_root / "reports" / "diagnosis" / "architecture_assessment_report.json",
        run_root / "reports" / "diagnosis" / "diagnosis_chain_summary.json",
        run_root / "reports" / "diagnosis" / "trace" / "model_structure_report.json",
        run_root / "reports" / "diagnosis" / "dataset" / "realization_gap.csv",
        run_root / "reports" / "diagnosis" / "dataset" / "timeline_loss_summary.csv",
        run_root / "reports" / "diagnosis_bundle.json",
        run_root / "diagnosis_workbench" / "index.html",
        run_root / "diagnosis_workbench" / "workbench_manifest.json",
    ]
    for artifact_path in required_artifacts:
        assert artifact_path.is_file(), f"missing artifact: {artifact_path}"

    assert diagnosis_bundle["metadata"]["report_kind"] == report_kind
    assert diagnosis_bundle["metadata"]["schedule_kind"] == schedule_kind
    assert diagnosis_bundle["report_references"]["roofline_report"] == "reports/diagnosis/roofline_report.json"
    assert "assessment" in diagnosis_bundle["available_panels"]
    assert len(support_matrix_report["layer_support_summary"]) > 1
    assert len(support_matrix_report["structure_support_summary"]) > 2
    assert any(
        row.get("layer_id") is not None and row.get("structure_id")
        for row in performance_diagnostics_report["node_hotspots"]
    )
    assert architecture_assessment_report["key_metrics"]
    assert architecture_assessment_report["top_realization_gaps"]
    if architecture_assessment_report["overall_assessment"]["verdict"] == "unsupported":
        summary_lower = architecture_assessment_report["overall_assessment"]["summary"].lower()
        assert "viable" not in summary_lower
        assert "runnable" not in summary_lower
    assert chain_summary["stage_chain"]
    assert any(stage["stage"] == "realization_gap" for stage in chain_summary["stage_chain"])
    assert any(stage["stage"] == "timeline" for stage in chain_summary["stage_chain"])
    assert diagnosis_workbench["default_panel"] == "summary"
    assert "roofline" in diagnosis_workbench["available_panels"]
    assert diagnosis_workbench["deep_links"]["performance"] == "#/performance"
    assert (
        manifest["artifact_index"]["diagnosis_workbench_manifest"]
        == "diagnosis_workbench/workbench_manifest.json"
    )
    assert manifest["artifact_index"]["diagnosis_bundle"] == "reports/diagnosis_bundle.json"
