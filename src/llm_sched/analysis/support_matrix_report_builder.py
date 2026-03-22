"""Builder for the DIAG-04 support matrix report."""

from __future__ import annotations

from collections import Counter, defaultdict

from llm_sched.contracts.frontend_analysis_report import FrontendLegalityReport
from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport
from llm_sched.contracts.support_matrix_report import (
    CriticalSupportGap,
    LayerSupportSummary,
    NodeSupportEntry,
    StructureSupportSummary,
    SupportMatrixReport,
)


def build_support_matrix_report(
    *,
    run_id: str,
    scenario_name: str,
    legality_report: FrontendLegalityReport,
    binding_report: FrontendBindingReport,
    model_structure_report: ModelStructureReport,
    operator_representation_report: OperatorRepresentationReport,
) -> SupportMatrixReport:
    legality_by_graph_node = defaultdict(list)
    for issue in legality_report.issues:
        legality_by_graph_node[issue.node_id].append(issue)

    binding_by_subject = defaultdict(list)
    for issue in binding_report.issues:
        binding_by_subject[issue.node_id].append(issue)

    node_index_by_graph_node = {
        entry.node_id: entry for entry in model_structure_report.node_index
    }
    structure_kind_by_id = {
        entry.structure_id: entry.structure_kind for entry in model_structure_report.structures
    }

    node_entries: list[NodeSupportEntry] = []
    critical_gaps: list[CriticalSupportGap] = []
    reason_counts: Counter[str] = Counter()

    for mapping in operator_representation_report.node_mappings:
        legality_issues = legality_by_graph_node.get(mapping.graph_node_id, [])
        binding_issues = binding_by_subject.get(mapping.normalized_node_id, [])
        provenance = _lookup_node_provenance(
            mapping.graph_node_id,
            node_index_by_graph_node=node_index_by_graph_node,
            structure_kind_by_id=structure_kind_by_id,
        )
        status, reasons, details = _classify_node_support(
            mapping,
            legality_issues,
            binding_issues,
        )
        reason_counts.update(reasons)
        node_entries.append(
            NodeSupportEntry(
                subject_id=mapping.normalized_node_id,
                graph_node_id=mapping.graph_node_id,
                layer_id=provenance["layer_id"],
                structure_id=provenance["structure_id"],
                structure_kind=provenance["structure_kind"],
                phase=mapping.phase,
                macro_op=mapping.macro_op,
                canonical_op=mapping.canonical_op,
                support_status=status,
                fallback_kind=mapping.fallback_kind or "none",
                binding_issue_ids=[issue.issue_id for issue in binding_issues],
                legality_rule_ids=[issue.rule_id for issue in legality_issues],
                reason_codes=reasons,
                detail_messages=details,
            )
        )
        if status in {"fallback", "unsupported", "constrained"}:
            for reason, detail in zip(reasons, details):
                critical_gaps.append(
                    CriticalSupportGap(
                        subject_id=mapping.normalized_node_id,
                        subject_kind="node",
                        support_status=status,
                        reason_code=reason,
                        message=detail,
                    )
                )

    layer_summaries = _aggregate_layer_summaries(node_entries)
    structure_summaries = _aggregate_structure_summaries(node_entries)
    critical_gaps.extend(_aggregate_structure_gaps(structure_summaries))

    return SupportMatrixReport(
        run_id=run_id,
        graph_id=operator_representation_report.graph_id,
        scenario_name=scenario_name,
        node_support_entries=node_entries,
        layer_support_summary=layer_summaries,
        structure_support_summary=structure_summaries,
        reason_counts=dict(sorted(reason_counts.items())),
        critical_gaps=critical_gaps,
    )


def _classify_node_support(mapping, legality_issues, binding_issues) -> tuple[str, list[str], list[str]]:
    reasons: list[str] = []
    details: list[str] = []

    if mapping.helper_surface or mapping.fallback_kind in {"helper", "fallback"}:
        reasons.append("helper_only_lowering")
        details.append("helper-only lowering path required")
    for issue in legality_issues:
        reasons.append(issue.rule_id)
        details.append(issue.message)
    if legality_issues:
        if mapping.helper_surface or mapping.fallback_kind in {"helper", "fallback"}:
            return ("fallback", reasons, details)
        return ("unsupported", reasons, details)
    if binding_issues:
        first = binding_issues[0]
        reasons.append(f"binding_issue:{first.issue_id}")
        details.append(first.message)
        return (
            "constrained",
            reasons,
            details,
        )
    if reasons:
        return ("fallback", reasons, details)
    return ("native", [], [])


def _aggregate_layer_summaries(node_entries: list[NodeSupportEntry]) -> list[LayerSupportSummary]:
    grouped = defaultdict(list)
    for entry in node_entries:
        if entry.layer_id is not None:
            grouped[entry.layer_id].append(entry)

    return [
        LayerSupportSummary(
            layer_id=layer_id,
            support_status=_aggregate_status(entries),
            node_count=len(entries),
            native_count=sum(1 for entry in entries if entry.support_status == "native"),
            constrained_count=sum(1 for entry in entries if entry.support_status == "constrained"),
            fallback_count=sum(1 for entry in entries if entry.support_status == "fallback"),
            unsupported_count=sum(1 for entry in entries if entry.support_status == "unsupported"),
            reason_codes=sorted({reason for entry in entries for reason in entry.reason_codes}),
        )
        for layer_id, entries in sorted(grouped.items())
    ]


def _aggregate_structure_summaries(node_entries: list[NodeSupportEntry]) -> list[StructureSupportSummary]:
    grouped = defaultdict(list)
    for entry in node_entries:
        if entry.structure_id is not None:
            grouped[entry.structure_id].append(entry)

    return [
        StructureSupportSummary(
            structure_id=structure_id,
            layer_id=entries[0].layer_id,
            structure_kind=entries[0].structure_kind,
            support_status=_aggregate_status(entries),
            node_count=len(entries),
            native_count=sum(1 for entry in entries if entry.support_status == "native"),
            constrained_count=sum(1 for entry in entries if entry.support_status == "constrained"),
            fallback_count=sum(1 for entry in entries if entry.support_status == "fallback"),
            unsupported_count=sum(1 for entry in entries if entry.support_status == "unsupported"),
            reason_codes=sorted({reason for entry in entries for reason in entry.reason_codes}),
        )
        for structure_id, entries in sorted(grouped.items())
    ]


def _aggregate_structure_gaps(
    structure_summaries: list[StructureSupportSummary],
) -> list[CriticalSupportGap]:
    gaps: list[CriticalSupportGap] = []
    for summary in structure_summaries:
        if summary.support_status == "native":
            continue
        for reason in summary.reason_codes:
            gaps.append(
                CriticalSupportGap(
                    subject_id=summary.structure_id,
                    subject_kind="structure",
                    support_status=summary.support_status,
                    reason_code=reason,
                    message=f"{summary.structure_kind} is classified as {summary.support_status} due to {reason}",
                )
            )
    return gaps


def _aggregate_status(entries: list[NodeSupportEntry]) -> str:
    statuses = {entry.support_status for entry in entries}
    if "unsupported" in statuses:
        return "unsupported"
    if "fallback" in statuses:
        return "fallback"
    if "constrained" in statuses:
        return "constrained"
    return "native"


def _lookup_node_provenance(
    graph_node_id: str,
    *,
    node_index_by_graph_node: dict[str, object],
    structure_kind_by_id: dict[str, str],
) -> dict[str, int | str | None]:
    node_index_entry = node_index_by_graph_node.get(graph_node_id)
    if node_index_entry is None:
        return {
            "layer_id": None,
            "structure_id": f"structure.unmapped.{graph_node_id}",
            "structure_kind": "unmapped_structure",
        }

    structure_id = node_index_entry.structure_ids[0] if node_index_entry.structure_ids else None
    if structure_id is None:
        return {
            "layer_id": node_index_entry.layer_id,
            "structure_id": f"structure.unmapped.{graph_node_id}",
            "structure_kind": "unmapped_structure",
        }
    return {
        "layer_id": node_index_entry.layer_id,
        "structure_id": structure_id,
        "structure_kind": structure_kind_by_id.get(structure_id, "unmapped_structure"),
    }
