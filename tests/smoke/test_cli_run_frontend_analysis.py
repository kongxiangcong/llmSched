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


def test_run_frontend_analysis_writes_ir_dumps_and_reports(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-frontend-001"

    init_result = run_cli(
        "init-run",
        "--run-root",
        str(run_root),
        "--model-path",
        "models/gemma3_1b/model_q4f16.onnx",
        "--target-profile",
        "profiles/targets/riscv_npu_single_core_v1.json",
        "--scenario-profile",
        "profiles/scenarios/prefill_seq128.json",
        cwd=repo_root,
    )

    assert init_result.returncode == 0

    run_result = run_cli(
        "run-frontend-analysis",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert run_result.returncode == 0
    assert (run_root / "dumps" / "graph_ir.json").is_file()
    assert (run_root / "dumps" / "canonical_graph_ir.json").is_file()
    assert (run_root / "dumps" / "nig_ir.json").is_file()
    assert (run_root / "dumps" / "bound_nig_ir.json").is_file()
    assert (run_root / "dumps" / "analysis_ir.json").is_file()
    assert (run_root / "reports" / "frontend_import_report.json").is_file()
    assert (run_root / "reports" / "workload_decomposition_report.json").is_file()
    assert (run_root / "reports" / "frontend_binding_report.json").is_file()
    assert (run_root / "reports" / "frontend_legality.json").is_file()
    assert (run_root / "reports" / "pseudo_fallback_summary.json").is_file()

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "completed"
    assert manifest["artifact_index"]["graph_ir"] == "dumps/graph_ir.json"
    assert manifest["artifact_index"]["bound_nig_ir"] == "dumps/bound_nig_ir.json"
    assert manifest["artifact_index"]["analysis_ir"] == "dumps/analysis_ir.json"
    assert (
        manifest["artifact_index"]["frontend_import_report"]
        == "reports/frontend_import_report.json"
    )
    assert (
        manifest["artifact_index"]["workload_decomposition_report"]
        == "reports/workload_decomposition_report.json"
    )
    assert (
        manifest["artifact_index"]["frontend_binding_report"]
        == "reports/frontend_binding_report.json"
    )
    assert manifest["artifact_index"]["frontend_legality_report"] == "reports/frontend_legality.json"
    assert manifest["artifact_index"]["pseudo_fallback_summary_report"] == "reports/pseudo_fallback_summary.json"

    summary = json.loads((run_root / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "completed"
    assert summary["exit_code"] == 0
    assert summary["manifest_path"] == "manifest.json"


def test_run_frontend_analysis_reports_missing_manifest_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "missing-manifest-run"
    run_root.mkdir()

    result = run_cli(
        "run-frontend-analysis",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Frontend analysis: ERROR" in result.stdout
    assert "manifest.json not found" in result.stdout
    assert "Traceback" not in result.stderr
