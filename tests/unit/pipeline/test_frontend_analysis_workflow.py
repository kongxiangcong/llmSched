import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.ir.analysis_ir import AnalysisIR
from llm_sched.ir.graph_ir import GraphIR
from llm_sched.ir.io import load_ir_document
from llm_sched.ir.nig import NIGIR


def test_run_frontend_analysis_writes_expected_artifacts(tmp_path: Path) -> None:
    from llm_sched.contracts.frontend_analysis_report import (
        FrontendLegalityReport,
        PseudoFallbackSummaryReport,
    )
    from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
    from llm_sched.contracts.frontend_import_report import FrontendImportReport
    from llm_sched.contracts.workload_decomposition_report import WorkloadDecompositionReport
    from llm_sched.pipeline.frontend_analysis import run_frontend_analysis

    repo_root = Path(__file__).resolve().parents[3]
    run_root = tmp_path / "run-frontend-unit-001"
    _write_initialized_run(run_root, repo_root)

    result = run_frontend_analysis(run_root)

    assert result.status == "completed"
    assert result.graph_ir_path == run_root / "dumps" / "graph_ir.json"
    assert result.bound_nig_ir_path == run_root / "dumps" / "bound_nig_ir.json"
    assert result.analysis_ir_path == run_root / "dumps" / "analysis_ir.json"
    assert result.import_report_path == run_root / "reports" / "frontend_import_report.json"
    assert result.decomposition_report_path == run_root / "reports" / "workload_decomposition_report.json"
    assert result.binding_report_path == run_root / "reports" / "frontend_binding_report.json"
    assert result.legality_report_path == run_root / "reports" / "frontend_legality.json"
    assert result.pseudo_fallback_summary_path == run_root / "reports" / "pseudo_fallback_summary.json"

    graph_ir = load_ir_document(result.graph_ir_path, GraphIR)
    nig_ir = load_ir_document(result.nig_ir_path, NIGIR)
    bound_nig_ir = load_ir_document(result.bound_nig_ir_path, NIGIR)
    analysis_ir = load_ir_document(result.analysis_ir_path, AnalysisIR)
    import_report = FrontendImportReport.model_validate(
        json.loads(result.import_report_path.read_text(encoding="utf-8"))
    )
    decomposition_report = WorkloadDecompositionReport.model_validate(
        json.loads(result.decomposition_report_path.read_text(encoding="utf-8"))
    )
    legality_report = FrontendLegalityReport.model_validate(
        json.loads(result.legality_report_path.read_text(encoding="utf-8"))
    )
    binding_report = FrontendBindingReport.model_validate(
        json.loads(result.binding_report_path.read_text(encoding="utf-8"))
    )
    summary_report = PseudoFallbackSummaryReport.model_validate(
        json.loads(result.pseudo_fallback_summary_path.read_text(encoding="utf-8"))
    )

    assert graph_ir.nodes
    assert nig_ir.nodes
    assert bound_nig_ir.binding_state == "bound"
    assert analysis_ir.records
    assert import_report.raw_node_total >= import_report.canonical_node_total
    assert decomposition_report.macro_op_counts["WDQ_GEMM"] > 0
    assert binding_report.node_count == len(nig_ir.nodes)
    assert binding_report.binding_coverage_ratio > 0.0
    assert binding_report.macro_summaries["WDQ_GEMM"].node_count > 0
    assert legality_report.issue_counts["no_hardware_mapping"] > 0
    assert summary_report.record_counts["SHAPE_HELPER"] > 0
    assert summary_report.totals["estimated_cycles"] > 0

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))
    assert manifest.status == "completed"
    assert "bound_nig_ir" in manifest.artifact_index
    assert "frontend_import_report" in manifest.artifact_index
    assert "workload_decomposition_report" in manifest.artifact_index
    assert "frontend_binding_report" in manifest.artifact_index
    assert summary.status == "completed"
    assert summary.exit_code == 0


def _write_initialized_run(run_root: Path, repo_root: Path) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    for relative in ("artifacts", "reports", "logs", "dumps"):
        (run_root / relative).mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_root.name,
        contract_version="phase-a.v1",
        status="initialized",
        model_path=str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
        target_profile_path=str((repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()),
        scenario_profile_path=str((repo_root / "profiles" / "scenarios" / "prefill_seq128.json").resolve()),
        artifact_index={
            "manifest": "manifest.json",
            "artifacts_dir": "artifacts",
            "reports_dir": "reports",
            "logs_dir": "logs",
            "dumps_dir": "dumps",
        },
    )
    (run_root / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(
            RunSummary(
                run_id=run_root.name,
                status="initialized",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )
