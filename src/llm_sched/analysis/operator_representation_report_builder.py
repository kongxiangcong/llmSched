"""Builder for the DIAG-02 operator representation report."""

from __future__ import annotations

from collections import defaultdict

from llm_sched.analysis.diagnosis_context import DiagnosisContext
from llm_sched.contracts.operator_representation_report import (
    OperatorFallbackEntry,
    OperatorMacroGroup,
    OperatorNodeMapping,
    OperatorPhaseGroup,
    OperatorRepresentationReport,
    OperatorTraceabilityEntry,
)
from llm_sched.contracts.workload_decomposition_report import WorkloadDecompositionReport
from llm_sched.ir.graph_ir import GraphIR
from llm_sched.ir.nig import NIGIR


def build_operator_representation_report(
    *,
    run_id: str | None = None,
    scenario_name: str | None = None,
    canonical_graph_ir: GraphIR | None = None,
    bound_nig_ir: NIGIR | None = None,
    workload_decomposition_report: WorkloadDecompositionReport | None = None,
    ctx: DiagnosisContext | None = None,
) -> OperatorRepresentationReport:
    if ctx is not None:
        run_id = ctx.manifest.run_id
        scenario_name = ctx.scenario_name
        canonical_graph_ir = ctx.canonical_graph_ir
        bound_nig_ir = ctx.bound_nig_ir
        workload_decomposition_report = ctx.workload_decomposition_report
    if any(value is None for value in (run_id, scenario_name, canonical_graph_ir, bound_nig_ir, workload_decomposition_report)):
        raise ValueError("build_operator_representation_report requires either ctx or explicit inputs")
    assert canonical_graph_ir is not None
    assert bound_nig_ir is not None
    assert workload_decomposition_report is not None
    assert run_id is not None
    assert scenario_name is not None
    if canonical_graph_ir.graph_id != bound_nig_ir.graph_id:
        raise ValueError("graph_id mismatch between canonical graph IR and bound NIG IR")
    if canonical_graph_ir.graph_id != workload_decomposition_report.graph_id:
        raise ValueError("graph_id mismatch between canonical graph IR and workload decomposition report")

    graph_nodes = ctx.graph_node_by_id if ctx is not None else {node.node_id: node for node in canonical_graph_ir.nodes}
    graph_node_to_mapping: dict[str, OperatorNodeMapping] = {}
    fallback_entries: list[OperatorFallbackEntry] = []
    traceability_index: list[OperatorTraceabilityEntry] = []

    for record in workload_decomposition_report.traceability_records:
        nig_node = next(node for node in bound_nig_ir.nodes if node.node_id == record.lowered_node_id)
        phase = _phase_for_macro(nig_node.macro_op)
        fallback_kind = _fallback_kind_for_macro(nig_node.macro_op)
        helper_surface = fallback_kind == "helper"
        schedule_block_ids = [f"sched.block.{nig_node.node_id}"]
        descriptor_ids = [] if helper_surface else [f"desc.{nig_node.node_id}"]

        for graph_node_id in record.graph_node_ids:
            if graph_node_id not in graph_nodes:
                continue
            mapping = OperatorNodeMapping(
                graph_node_id=graph_node_id,
                canonical_op=graph_nodes[graph_node_id].op_kind,
                macro_op=_canonical_macro_name(nig_node.macro_op),
                phase=phase,
                normalized_node_id=nig_node.node_id,
                schedule_block_ids=schedule_block_ids,
                descriptor_ids=descriptor_ids,
                fallback_kind=fallback_kind,
                helper_surface=helper_surface,
            )
            graph_node_to_mapping[graph_node_id] = mapping
            traceability_index.append(
                OperatorTraceabilityEntry(
                    graph_node_id=graph_node_id,
                    normalized_node_id=nig_node.node_id,
                    macro_op=mapping.macro_op,
                    phase=phase,
                    schedule_block_ids=schedule_block_ids,
                    descriptor_ids=descriptor_ids,
                )
            )
            if fallback_kind is not None:
                fallback_entries.append(
                    OperatorFallbackEntry(
                        graph_node_id=graph_node_id,
                        normalized_node_id=nig_node.node_id,
                        macro_op=mapping.macro_op,
                        phase=phase,
                        fallback_kind=fallback_kind,
                        reason="helper-only lowering" if helper_surface else "fallback lowering",
                    )
                )

    node_mappings = [graph_node_to_mapping[node.node_id] for node in canonical_graph_ir.nodes if node.node_id in graph_node_to_mapping]
    macro_groups = _build_macro_groups(node_mappings)
    phase_groups = _build_phase_groups(node_mappings)

    return OperatorRepresentationReport(
        run_id=run_id,
        graph_id=canonical_graph_ir.graph_id,
        scenario_name=scenario_name,
        node_mappings=node_mappings,
        macro_groups=macro_groups,
        phase_groups=phase_groups,
        fallback_entries=fallback_entries,
        traceability_index=traceability_index,
    )


def _build_macro_groups(node_mappings: list[OperatorNodeMapping]) -> list[OperatorMacroGroup]:
    grouped: dict[tuple[str, str], dict[str, list[str]]] = defaultdict(
        lambda: {
            "normalized_node_ids": [],
            "graph_node_ids": [],
            "schedule_block_ids": [],
        }
    )
    for mapping in node_mappings:
        bucket = grouped[(mapping.macro_op, mapping.phase)]
        bucket["normalized_node_ids"].append(mapping.normalized_node_id)
        bucket["graph_node_ids"].append(mapping.graph_node_id)
        bucket["schedule_block_ids"].extend(mapping.schedule_block_ids)

    return [
        OperatorMacroGroup(
            macro_op=macro_op,
            phase=phase,
            normalized_node_ids=sorted(set(values["normalized_node_ids"])),
            graph_node_ids=values["graph_node_ids"],
            schedule_block_ids=sorted(set(values["schedule_block_ids"])),
        )
        for (macro_op, phase), values in sorted(grouped.items())
    ]


def _build_phase_groups(node_mappings: list[OperatorNodeMapping]) -> list[OperatorPhaseGroup]:
    grouped: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"macro_ops": [], "normalized_node_ids": [], "graph_node_ids": []}
    )
    for mapping in node_mappings:
        bucket = grouped[mapping.phase]
        bucket["macro_ops"].append(mapping.macro_op)
        bucket["normalized_node_ids"].append(mapping.normalized_node_id)
        bucket["graph_node_ids"].append(mapping.graph_node_id)

    return [
        OperatorPhaseGroup(
            phase=phase,
            macro_ops=sorted(set(values["macro_ops"])),
            normalized_node_ids=sorted(set(values["normalized_node_ids"])),
            graph_node_ids=values["graph_node_ids"],
        )
        for phase, values in sorted(grouped.items())
    ]


def _phase_for_macro(macro_op: str) -> str:
    if macro_op in {"WDQ_GEMM", "GEMM", "GEGLU"}:
        return "projection"
    if "ROPE" in macro_op or "SDPA" in macro_op or "ATTENTION" in macro_op:
        return "attention"
    if "KV" in macro_op:
        return "kv_io"
    return "other"


def _fallback_kind_for_macro(macro_op: str) -> str | None:
    if macro_op in {"ROPE_TABLE", "SHAPE_HELPER", "LAYOUT_FALLBACK"}:
        return "helper"
    return None


def _canonical_macro_name(macro_op: str) -> str:
    if macro_op == "ROPE_TABLE":
        return "ROPE"
    return macro_op


def _extract_operator_mapping_rows(
    report: OperatorRepresentationReport,
    *,
    ctx: DiagnosisContext,
) -> list[dict[str, object]]:
    return [
        {
            "normalized_node_id": mapping.normalized_node_id,
            "graph_node_id": mapping.graph_node_id,
            "canonical_op": mapping.canonical_op,
            "macro_op": mapping.macro_op,
            "phase": mapping.phase,
            "fallback_kind": mapping.fallback_kind,
            "structure_id": ctx.resolve_normalized_node_provenance(mapping.normalized_node_id).structure_id,
            "layer_id": ctx.resolve_normalized_node_provenance(mapping.normalized_node_id).layer_id,
        }
        for mapping in report.node_mappings
    ]


def _extract_macro_op_summary_rows(report: OperatorRepresentationReport) -> list[dict[str, object]]:
    fallback_ids = {entry.normalized_node_id for entry in report.fallback_entries}
    return [
        {
            "macro_op": group.macro_op,
            "phase": group.phase,
            "node_count": len(group.normalized_node_ids),
            "fallback_count": sum(1 for node_id in group.normalized_node_ids if node_id in fallback_ids),
            "helper_count": sum(1 for entry in report.fallback_entries if entry.phase == group.phase and entry.macro_op == group.macro_op and entry.fallback_kind == "helper"),
            "native_count": sum(1 for node_id in group.normalized_node_ids if node_id not in fallback_ids),
        }
        for group in report.macro_groups
    ]
