"""End-to-end frontend analysis workflow for one initialized run."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import estimate_nig_analysis
from llm_sched.config.loader import Diagnostic, load_scenario_profile, load_target_profile
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.frontend_analysis_report import (
    FrontendLegalityReport,
    PseudoFallbackSummaryReport,
)
from llm_sched.contracts.frontend_binding_report import (
    FrontendBindingIssue,
    FrontendBindingReport,
    MacroBindingSummary,
)
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.frontend import (
    bind_nig_ir,
    build_frontend_import_report,
    build_gemma3_shape_bindings,
    build_workload_decomposition_report,
    canonicalize_graph_ir,
    collect_frontend_legality_issues,
    import_onnx_to_graph_ir,
    load_gemma_model_metadata,
    lower_graph_ir_to_nig,
)
from llm_sched.ir.io import dump_ir_document


class FrontendAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    graph_ir_path: Path | None = None
    canonical_graph_ir_path: Path | None = None
    nig_ir_path: Path | None = None
    bound_nig_ir_path: Path | None = None
    analysis_ir_path: Path | None = None
    import_report_path: Path | None = None
    decomposition_report_path: Path | None = None
    binding_report_path: Path | None = None
    legality_report_path: Path | None = None
    pseudo_fallback_summary_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_frontend_analysis(run_root: str | Path) -> FrontendAnalysisResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)
        model_path = Path(manifest.model_path)
        target_profile = load_target_profile(manifest.target_profile_path)
        scenario_profile = load_scenario_profile(manifest.scenario_profile_path)
        metadata = load_gemma_model_metadata(model_path.with_name("config.json"))
        shape_bindings = build_gemma3_shape_bindings(metadata, scenario_profile)

        graph_ir = import_onnx_to_graph_ir(model_path, shape_bindings=shape_bindings)
        canonical_graph_ir = canonicalize_graph_ir(graph_ir)
        import_report = build_frontend_import_report(graph_ir, canonical_graph_ir)
        legality_issues = collect_frontend_legality_issues(
            canonical_graph_ir,
            hardware=target_profile,
            shape_bindings=shape_bindings,
        )
        nig_ir = lower_graph_ir_to_nig(canonical_graph_ir, scenario=scenario_profile)
        decomposition_report = build_workload_decomposition_report(canonical_graph_ir, nig_ir=nig_ir)
        bound_nig_ir = bind_nig_ir(nig_ir, shape_bindings=shape_bindings)
        analysis_ir = estimate_nig_analysis(nig_ir, target_profile)

        graph_ir_path = layout.dumps_dir / "graph_ir.json"
        canonical_graph_ir_path = layout.dumps_dir / "canonical_graph_ir.json"
        nig_ir_path = layout.dumps_dir / "nig_ir.json"
        bound_nig_ir_path = layout.dumps_dir / "bound_nig_ir.json"
        analysis_ir_path = layout.dumps_dir / "analysis_ir.json"
        import_report_path = layout.reports_dir / "frontend_import_report.json"
        decomposition_report_path = layout.reports_dir / "workload_decomposition_report.json"
        binding_report_path = layout.reports_dir / "frontend_binding_report.json"
        legality_report_path = layout.reports_dir / "frontend_legality.json"
        pseudo_fallback_summary_path = layout.reports_dir / "pseudo_fallback_summary.json"

        dump_ir_document(graph_ir, graph_ir_path)
        dump_ir_document(canonical_graph_ir, canonical_graph_ir_path)
        dump_ir_document(nig_ir, nig_ir_path)
        dump_ir_document(bound_nig_ir, bound_nig_ir_path)
        dump_ir_document(analysis_ir, analysis_ir_path)
        _write_json_report(import_report, import_report_path)
        _write_json_report(decomposition_report, decomposition_report_path)
        _write_json_report(_build_binding_report(manifest.run_id, bound_nig_ir), binding_report_path)
        _write_json_report(_build_legality_report(manifest.run_id, legality_issues), legality_report_path)
        _write_json_report(
            _build_pseudo_fallback_summary_report(manifest.run_id, nig_ir, analysis_ir),
            pseudo_fallback_summary_path,
        )

        artifact_index.update(
            {
                "graph_ir": _relative_to_run(layout.run_root, graph_ir_path),
                "canonical_graph_ir": _relative_to_run(layout.run_root, canonical_graph_ir_path),
                "nig_ir": _relative_to_run(layout.run_root, nig_ir_path),
                "bound_nig_ir": _relative_to_run(layout.run_root, bound_nig_ir_path),
                "analysis_ir": _relative_to_run(layout.run_root, analysis_ir_path),
                "frontend_import_report": _relative_to_run(layout.run_root, import_report_path),
                "workload_decomposition_report": _relative_to_run(
                    layout.run_root, decomposition_report_path
                ),
                "frontend_binding_report": _relative_to_run(layout.run_root, binding_report_path),
                "frontend_legality_report": _relative_to_run(layout.run_root, legality_report_path),
                "pseudo_fallback_summary_report": _relative_to_run(
                    layout.run_root, pseudo_fallback_summary_path
                ),
            }
        )
        _write_manifest(manifest, manifest_path, status="completed", artifact_index=artifact_index)
        _write_run_summary(
            layout.run_root / "run-summary.json",
            RunSummary(
                run_id=manifest.run_id,
                status="completed",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ),
        )
        return FrontendAnalysisResult(
            status="completed",
            graph_ir_path=graph_ir_path,
            canonical_graph_ir_path=canonical_graph_ir_path,
            nig_ir_path=nig_ir_path,
            bound_nig_ir_path=bound_nig_ir_path,
            analysis_ir_path=analysis_ir_path,
            import_report_path=import_report_path,
            decomposition_report_path=decomposition_report_path,
            binding_report_path=binding_report_path,
            legality_report_path=legality_report_path,
            pseudo_fallback_summary_path=pseudo_fallback_summary_path,
            diagnostics=[],
        )
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, FileNotFoundError) and exc.filename == str(manifest_path):
            message = f"manifest.json not found at {manifest_path}"

        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="manifest.json" if manifest is None else "frontend_analysis",
                severity="error",
                message=message,
            )
        ]
        if manifest is not None:
            _write_manifest(manifest, manifest_path, status="failed", artifact_index=artifact_index)
        _write_run_summary(
            layout.run_root / "run-summary.json",
            RunSummary(
                run_id=manifest.run_id if manifest is not None else layout.run_root.name,
                status="failed",
                exit_code=1,
                manifest_path="manifest.json",
                diagnostics=diagnostics,
            ),
        )
        return FrontendAnalysisResult(status="failed", diagnostics=diagnostics)


def _build_legality_report(
    run_id: str,
    legality_issues: list[object],
) -> FrontendLegalityReport:
    from llm_sched.frontend.legality import FrontendLegalityIssue

    issues = [issue for issue in legality_issues if isinstance(issue, FrontendLegalityIssue)]
    counts = Counter(issue.rule_id for issue in issues)
    return FrontendLegalityReport(
        run_id=run_id,
        issue_counts=dict(sorted(counts.items())),
        issues=issues,
    )


def _build_binding_report(
    run_id: str,
    bound_nig_ir: object,
) -> FrontendBindingReport:
    from llm_sched.ir.nig import NIGIR, NIGNode

    if not isinstance(bound_nig_ir, NIGIR):
        raise TypeError("binding report requires a bound NIGIR input")
    if bound_nig_ir.binding_state != "bound":
        raise ValueError("binding report requires bound NIGIR input")

    issue_counts: Counter[str] = Counter()
    missing_field_counts: Counter[str] = Counter()
    macro_node_counts: Counter[str] = Counter()
    macro_fully_bound_counts: Counter[str] = Counter()
    issues: list[FrontendBindingIssue] = []

    for node in bound_nig_ir.nodes:
        if not isinstance(node, NIGNode):
            continue
        macro_node_counts[node.macro_op] += 1
        node_issues, node_missing_field_counts = _collect_binding_issues(node)
        issues.extend(node_issues)
        issue_counts.update(issue.issue_id for issue in node_issues)
        missing_field_counts.update(node_missing_field_counts)
        if not node_issues:
            macro_fully_bound_counts[node.macro_op] += 1

    fully_bound_node_count = sum(macro_fully_bound_counts.values())
    node_count = len(bound_nig_ir.nodes)
    macro_summaries = {
        macro_op: MacroBindingSummary(
            node_count=count,
            fully_bound_node_count=macro_fully_bound_counts.get(macro_op, 0),
            completeness_ratio=_safe_ratio(macro_fully_bound_counts.get(macro_op, 0), count),
        )
        for macro_op, count in sorted(macro_node_counts.items())
    }

    return FrontendBindingReport(
        run_id=run_id,
        node_count=node_count,
        fully_bound_node_count=fully_bound_node_count,
        binding_coverage_ratio=_safe_ratio(fully_bound_node_count, node_count),
        issue_counts=dict(sorted(issue_counts.items())),
        missing_field_counts=dict(sorted(missing_field_counts.items())),
        macro_summaries=macro_summaries,
        issues=issues,
    )


def _build_pseudo_fallback_summary_report(
    run_id: str,
    nig_ir: object,
    analysis_ir: object,
) -> PseudoFallbackSummaryReport:
    from llm_sched.ir.analysis_ir import AnalysisIR
    from llm_sched.ir.nig import NIGIR

    if not isinstance(nig_ir, NIGIR) or not isinstance(analysis_ir, AnalysisIR):
        raise TypeError("summary report requires NIGIR and AnalysisIR inputs")

    macro_by_subject = {node.node_id: node.macro_op for node in nig_ir.nodes}
    record_counts = Counter(macro_by_subject.get(record.subject_id, "UNKNOWN") for record in analysis_ir.records)
    tag_counts = Counter(tag for record in analysis_ir.records for tag in record.tags)
    totals = defaultdict(float)
    total_bytes_by_macro = defaultdict(float)
    estimated_cycles_by_macro = defaultdict(float)

    for record in analysis_ir.records:
        macro_op = macro_by_subject.get(record.subject_id, "UNKNOWN")
        totals["records"] += 1.0
        totals["read_bytes"] += record.metrics.get("read_bytes", 0.0)
        totals["write_bytes"] += record.metrics.get("write_bytes", 0.0)
        totals["estimated_cycles"] += record.metrics.get("estimated_cycles", 0.0)
        total_bytes_by_macro[macro_op] += record.metrics.get("total_bytes", 0.0)
        estimated_cycles_by_macro[macro_op] += record.metrics.get("estimated_cycles", 0.0)

    return PseudoFallbackSummaryReport(
        run_id=run_id,
        record_counts=dict(sorted(record_counts.items())),
        tag_counts=dict(sorted(tag_counts.items())),
        totals=dict(sorted(totals.items())),
        total_bytes_by_macro=dict(sorted(total_bytes_by_macro.items())),
        estimated_cycles_by_macro=dict(sorted(estimated_cycles_by_macro.items())),
    )


def _collect_binding_issues(
    node: object,
) -> tuple[list[FrontendBindingIssue], Counter[str]]:
    from llm_sched.ir.nig import NIGNode

    if not isinstance(node, NIGNode):
        return ([], Counter())

    issues: list[FrontendBindingIssue] = []
    missing_field_counts: Counter[str] = Counter()

    if node.binding is None:
        missing_field_counts["binding"] += 1
        issues.append(
            FrontendBindingIssue(
                issue_id="binding_missing",
                message="node is missing bound-NIG payload",
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )
        return (issues, missing_field_counts)

    if any(dim < 0 for dim in node.binding.resolved_shape):
        missing_field_counts["resolved_shape"] += 1
        issues.append(
            FrontendBindingIssue(
                issue_id="resolved_shape_unbound",
                message="resolved shape still contains dynamic dimensions",
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    if not node.binding.canonical_layout:
        missing_field_counts["canonical_layout"] += 1
        issues.append(
            FrontendBindingIssue(
                issue_id="canonical_layout_missing",
                message="bound node is missing canonical layout",
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    if not node.binding.memory_class:
        missing_field_counts["memory_class"] += 1
        issues.append(
            FrontendBindingIssue(
                issue_id="memory_class_missing",
                message="bound node is missing primary memory class",
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    missing_inputs = [tensor_name for tensor_name in node.inputs if tensor_name not in node.binding.input_memory_classes]
    if missing_inputs:
        missing_field_counts["input_memory_class"] += len(missing_inputs)
        issues.append(
            FrontendBindingIssue(
                issue_id="input_memory_class_missing",
                message="bound node is missing input memory classes for: " + ", ".join(missing_inputs),
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    missing_outputs = [
        tensor_name for tensor_name in node.outputs if tensor_name not in node.binding.output_memory_classes
    ]
    if missing_outputs:
        missing_field_counts["output_memory_class"] += len(missing_outputs)
        issues.append(
            FrontendBindingIssue(
                issue_id="output_memory_class_missing",
                message="bound node is missing output memory classes for: " + ", ".join(missing_outputs),
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    if node.binding.quant.quant_mode != "none" and not node.binding.quant.scale_present:
        missing_field_counts["scale_present"] += 1
        issues.append(
            FrontendBindingIssue(
                issue_id="quant_scale_missing",
                message="quantized node is missing scale binding metadata",
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    if node.binding.quant.quant_mode != "none" and not node.binding.quant.k_tile_aligned:
        issues.append(
            FrontendBindingIssue(
                issue_id="quant_k_tile_misaligned",
                message="quantized node group_size does not align with K_tile",
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    if node.macro_op in {"ROPE", "KVSTORE", "KVLOAD", "SDPA", "SDPA_DECODE"} and node.binding.attention is None:
        missing_field_counts["attention"] += 1
        issues.append(
            FrontendBindingIssue(
                issue_id="attention_binding_missing",
                message="attention-path node is missing bound attention payload",
                node_id=node.node_id,
                macro_op=node.macro_op,
            )
        )

    return (issues, missing_field_counts)


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return numerator / denominator


def _write_json_report(report: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")


def _write_manifest(
    manifest: RunManifest,
    manifest_path: Path,
    status: str,
    artifact_index: dict[str, str],
) -> None:
    manifest_path.write_text(
        json.dumps(
            manifest.model_copy(
                update={
                    "status": status,
                    "artifact_index": artifact_index,
                },
                deep=True,
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_run_summary(path: Path, summary: RunSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary.model_dump(mode="json"), indent=2), encoding="utf-8")


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
