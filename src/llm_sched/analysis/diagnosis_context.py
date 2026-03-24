"""Shared context and accessors for diagnosis pipeline inputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from llm_sched.config.loader import load_scenario_profile, load_target_profile
from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.frontend_analysis_report import FrontendLegalityReport
from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
from llm_sched.contracts.frontend_import_report import FrontendImportReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_plan import MemoryPlanArtifact, PlannedAllocation
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.workload_decomposition_report import WorkloadDecompositionReport
from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorRecord
from llm_sched.ir.graph_ir import GraphIR, GraphNode
from llm_sched.ir.io import load_ir_document
from llm_sched.ir.nig import NIGIR, NIGNode
from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

ReportKind = Literal["prefill", "decode"]
ScheduleKind = Literal["single-core", "dual-core"]
TopLevelDiagnosisReport = PrefillEvaluationReport | DecodeEvaluationReport

_LAYER_PATTERN = re.compile(r"layers\.(\d+)")


class DiagnosisProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_node_id: str | None = None
    graph_node_id: str | None = None
    graph_node_ids: tuple[str, ...] = ()
    layer_id: int | None = Field(default=None, ge=0)
    structure_id: str
    structure_kind: str


class DiagnosisContext(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    run_root: Path
    manifest: RunManifest
    artifact_index: dict[str, str]
    target_profile: TargetProfile
    scenario_profile: ScenarioProfile
    canonical_graph_ir: GraphIR
    bound_nig_ir: NIGIR
    memory_plan: MemoryPlanArtifact | None = None
    schedule_ir: ScheduleIR | None = None
    descriptor_ir: DescriptorIR | None = None
    perf_summary_report: PerfSummaryReport | None = None
    workload_decomposition_report: WorkloadDecompositionReport | None = None
    frontend_import_report: FrontendImportReport
    frontend_binding_report: FrontendBindingReport
    frontend_legality_report: FrontendLegalityReport
    prefill_evaluation_report: PrefillEvaluationReport | None = None
    decode_evaluation_report: DecodeEvaluationReport | None = None
    top_level_report: TopLevelDiagnosisReport | None = None
    report_kind: ReportKind
    schedule_kind: ScheduleKind
    graph_id: str
    scenario_name: str
    graph_node_by_id: dict[str, GraphNode]
    normalized_node_by_id: dict[str, NIGNode]
    schedule_block_by_id: dict[str, ScheduleBlock]
    descriptor_by_block_id: dict[str, DescriptorRecord]
    allocations_by_node: dict[str, tuple[PlannedAllocation, ...]]
    graph_node_provenance_by_id: dict[str, DiagnosisProvenance]
    normalized_node_provenance_by_id: dict[str, DiagnosisProvenance]
    block_ids_by_normalized_node_id: dict[str, tuple[str, ...]]

    def resolve_graph_node_provenance(self, graph_node_id: str) -> DiagnosisProvenance:
        return self.graph_node_provenance_by_id.get(
            graph_node_id,
            DiagnosisProvenance(
                graph_node_id=graph_node_id,
                graph_node_ids=(graph_node_id,),
                structure_id=f"structure.unmapped.{graph_node_id}",
                structure_kind="unmapped_structure",
            ),
        )

    def resolve_normalized_node_provenance(self, normalized_node_id: str) -> DiagnosisProvenance:
        return self.normalized_node_provenance_by_id.get(
            normalized_node_id,
            DiagnosisProvenance(
                normalized_node_id=normalized_node_id,
                structure_id=f"structure.unmapped.{normalized_node_id}",
                structure_kind="unmapped_structure",
            ),
        )

    def resolve_graph_node_id_for_normalized_node(self, normalized_node_id: str) -> str | None:
        return self.resolve_normalized_node_provenance(normalized_node_id).graph_node_id

    def resolve_block_ids_for_normalized_node(self, normalized_node_id: str) -> tuple[str, ...]:
        return self.block_ids_by_normalized_node_id.get(normalized_node_id, ())

    def resolve_descriptor_for_block(self, block_id: str) -> DescriptorRecord | None:
        return self.descriptor_by_block_id.get(block_id)


def build_diagnosis_context(run_root: str | Path, *, require_top_level_report: bool = False) -> DiagnosisContext:
    run_root_path = Path(run_root)
    manifest_path = run_root_path / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    artifact_index = dict(manifest.artifact_index)

    target_profile = load_target_profile(manifest.target_profile_path)
    scenario_profile = load_scenario_profile(manifest.scenario_profile_path)
    canonical_graph_ir = load_ir_document(_artifact_path(run_root_path, artifact_index, "canonical_graph_ir", "dumps/canonical_graph_ir.json"), GraphIR)
    bound_nig_ir = load_ir_document(_artifact_path(run_root_path, artifact_index, "bound_nig_ir", "dumps/bound_nig_ir.json"), NIGIR)
    memory_plan = _optional_load_ir(_artifact_path(run_root_path, artifact_index, "memory_plan", "artifacts/memory_plan.json"), MemoryPlanArtifact)
    schedule_ir = _optional_load_ir(resolve_schedule_artifact_path(run_root_path, artifact_index), ScheduleIR)
    descriptor_ir = _optional_load_ir(_artifact_path(run_root_path, artifact_index, "descriptor_ir", "artifacts/descriptor_ir.json"), DescriptorIR)
    perf_summary_report = _optional_load_report(
        _artifact_path(run_root_path, artifact_index, "perf_summary_report", "reports/perf_summary_report.json"),
        PerfSummaryReport,
    )
    workload_decomposition_report = _optional_load_report(
        _artifact_path(run_root_path, artifact_index, "workload_decomposition_report", "reports/workload_decomposition_report.json"),
        WorkloadDecompositionReport,
    )
    frontend_import_report = FrontendImportReport.model_validate_json(
        _artifact_path(run_root_path, artifact_index, "frontend_import_report", "reports/frontend_import_report.json").read_text(encoding="utf-8")
    )
    frontend_binding_report = FrontendBindingReport.model_validate_json(
        _artifact_path(run_root_path, artifact_index, "frontend_binding_report", "reports/frontend_binding_report.json").read_text(encoding="utf-8")
    )
    frontend_legality_report = FrontendLegalityReport.model_validate_json(
        _artifact_path(run_root_path, artifact_index, "frontend_legality_report", "reports/frontend_legality.json").read_text(encoding="utf-8")
    )

    report_kind, prefill_report, decode_report, top_level_report = load_top_level_report(
        run_root_path,
        artifact_index,
        scenario_profile,
        require_top_level_report=require_top_level_report,
    )
    schedule_kind = target_profile.core_mode if schedule_ir is None else resolve_schedule_kind(schedule_ir, target_profile)
    _validate_graph_alignment(
        canonical_graph_ir=canonical_graph_ir,
        bound_nig_ir=bound_nig_ir,
        memory_plan=memory_plan,
        schedule_ir=schedule_ir,
        descriptor_ir=descriptor_ir,
        perf_summary_report=perf_summary_report,
        workload_decomposition_report=workload_decomposition_report,
        frontend_import_report=frontend_import_report,
    )

    graph_node_by_id = {node.node_id: node for node in canonical_graph_ir.nodes}
    normalized_node_by_id = {node.node_id: node for node in bound_nig_ir.nodes}
    schedule_block_by_id = {} if schedule_ir is None else {block.block_id: block for block in schedule_ir.blocks}
    descriptor_by_block_id = {} if descriptor_ir is None else {descriptor.schedule_block_id: descriptor for descriptor in descriptor_ir.descriptors}
    allocations_by_node = {} if memory_plan is None else _build_allocations_by_node(memory_plan)
    graph_node_provenance_by_id = _build_graph_node_provenance_index(canonical_graph_ir)
    normalized_node_provenance_by_id = _build_normalized_node_provenance_index(
        bound_nig_ir=bound_nig_ir,
        workload_decomposition_report=workload_decomposition_report,
        graph_node_by_id=graph_node_by_id,
        graph_node_provenance_by_id=graph_node_provenance_by_id,
    )
    block_ids_by_normalized_node_id = {} if schedule_ir is None else _build_block_ids_by_normalized_node(schedule_ir)

    return DiagnosisContext(
        run_root=run_root_path,
        manifest=manifest,
        artifact_index=artifact_index,
        target_profile=target_profile,
        scenario_profile=scenario_profile,
        canonical_graph_ir=canonical_graph_ir,
        bound_nig_ir=bound_nig_ir,
        memory_plan=memory_plan,
        schedule_ir=schedule_ir,
        descriptor_ir=descriptor_ir,
        perf_summary_report=perf_summary_report,
        workload_decomposition_report=workload_decomposition_report,
        frontend_import_report=frontend_import_report,
        frontend_binding_report=frontend_binding_report,
        frontend_legality_report=frontend_legality_report,
        prefill_evaluation_report=prefill_report,
        decode_evaluation_report=decode_report,
        top_level_report=top_level_report,
        report_kind=report_kind,
        schedule_kind=schedule_kind,
        graph_id=canonical_graph_ir.graph_id,
        scenario_name=scenario_profile.scenario_name,
        graph_node_by_id=graph_node_by_id,
        normalized_node_by_id=normalized_node_by_id,
        schedule_block_by_id=schedule_block_by_id,
        descriptor_by_block_id=descriptor_by_block_id,
        allocations_by_node=allocations_by_node,
        graph_node_provenance_by_id=graph_node_provenance_by_id,
        normalized_node_provenance_by_id=normalized_node_provenance_by_id,
        block_ids_by_normalized_node_id=block_ids_by_normalized_node_id,
    )


def resolve_report_kind(*, prefill_report: PrefillEvaluationReport | None, decode_report: DecodeEvaluationReport | None, scenario_profile: ScenarioProfile) -> ReportKind:
    if prefill_report is not None and decode_report is not None:
        raise ValueError("exactly one top-level evaluation report must exist for diagnosis context")
    if prefill_report is None and decode_report is None:
        raise ValueError("top-level evaluation report not found for diagnosis context")
    report_kind: ReportKind = "prefill" if prefill_report is not None else "decode"
    if report_kind != scenario_profile.mode:
        raise ValueError(f"scenario mode {scenario_profile.mode} does not match resolved report_kind {report_kind}")
    return report_kind


def resolve_schedule_kind(schedule_ir: ScheduleIR, target_profile: TargetProfile) -> ScheduleKind:
    if schedule_ir.core_mode != target_profile.core_mode:
        raise ValueError(
            f"target profile core_mode {target_profile.core_mode} does not match schedule core_mode {schedule_ir.core_mode}"
        )
    return schedule_ir.core_mode


def load_top_level_report(
    run_root: Path,
    artifact_index: dict[str, str],
    scenario_profile: ScenarioProfile,
    *,
    require_top_level_report: bool = False,
) -> tuple[ReportKind, PrefillEvaluationReport | None, DecodeEvaluationReport | None, TopLevelDiagnosisReport | None]:
    prefill_path = run_root / Path(artifact_index.get("prefill_evaluation_report", "reports/prefill_evaluation_report.json"))
    decode_path = run_root / Path(artifact_index.get("decode_evaluation_report", "reports/decode_evaluation_report.json"))
    prefill_report = PrefillEvaluationReport.model_validate_json(prefill_path.read_text(encoding="utf-8")) if prefill_path.is_file() else None
    decode_report = DecodeEvaluationReport.model_validate_json(decode_path.read_text(encoding="utf-8")) if decode_path.is_file() else None
    if prefill_report is None and decode_report is None and not require_top_level_report:
        return scenario_profile.mode, prefill_report, decode_report, None
    report_kind = resolve_report_kind(prefill_report=prefill_report, decode_report=decode_report, scenario_profile=scenario_profile)
    top_level_report = prefill_report if report_kind == "prefill" else decode_report
    return report_kind, prefill_report, decode_report, top_level_report


def resolve_schedule_artifact_path(run_root: Path, artifact_index: dict[str, str]) -> Path:
    for artifact_key in ("dual_core_schedule_ir", "schedule_ir"):
        candidate_path = run_root / Path(artifact_index.get(artifact_key, f"artifacts/{artifact_key}.json"))
        if candidate_path.is_file():
            return candidate_path
    return run_root / Path(artifact_index.get("schedule_ir", "artifacts/schedule_ir.json"))



def _optional_load_ir(path: Path, model_type):
    return load_ir_document(path, model_type) if path.is_file() else None


def _optional_load_report(path: Path, model_type):
    return model_type.model_validate_json(path.read_text(encoding="utf-8")) if path.is_file() else None

def _artifact_path(run_root: Path, artifact_index: dict[str, str], key: str, default: str) -> Path:
    return run_root / Path(artifact_index.get(key, default))


def _validate_graph_alignment(**payloads: object) -> None:
    graph_ids = {getattr(value, "graph_id", None) for value in payloads.values() if getattr(value, "graph_id", None) is not None}
    if len(graph_ids) > 1:
        raise ValueError(f"graph_id mismatch across diagnosis context artifacts: {sorted(graph_ids)}")


def _build_allocations_by_node(memory_plan: MemoryPlanArtifact) -> dict[str, tuple[PlannedAllocation, ...]]:
    grouped: dict[str, list[PlannedAllocation]] = {}
    for allocation in memory_plan.allocations:
        grouped.setdefault(allocation.node_id, []).append(allocation)
    return {node_id: tuple(entries) for node_id, entries in grouped.items()}


def _build_graph_node_provenance_index(canonical_graph_ir: GraphIR) -> dict[str, DiagnosisProvenance]:
    provenance_by_id: dict[str, DiagnosisProvenance] = {}
    for node in canonical_graph_ir.nodes:
        layer_id, structure_kind = _structure_bucket_key(node)
        provenance_by_id[node.node_id] = DiagnosisProvenance(
            graph_node_id=node.node_id,
            graph_node_ids=(node.node_id,),
            layer_id=layer_id,
            structure_id=_structure_id(layer_id, structure_kind),
            structure_kind=structure_kind,
        )
    return provenance_by_id


def _build_normalized_node_provenance_index(
    *,
    bound_nig_ir: NIGIR,
    workload_decomposition_report: WorkloadDecompositionReport,
    graph_node_by_id: dict[str, GraphNode],
    graph_node_provenance_by_id: dict[str, DiagnosisProvenance],
) -> dict[str, DiagnosisProvenance]:
    graph_nodes_by_normalized: dict[str, list[str]] = {}
    if workload_decomposition_report is None:
        workload_records = ()
    else:
        workload_records = workload_decomposition_report.traceability_records
    for record in workload_records:
        graph_nodes_by_normalized.setdefault(record.lowered_node_id, []).extend(record.graph_node_ids)

    provenance_by_id: dict[str, DiagnosisProvenance] = {}
    for node in bound_nig_ir.nodes:
        graph_node_ids = [graph_node_id for graph_node_id in graph_nodes_by_normalized.get(node.node_id, []) if graph_node_id in graph_node_by_id]
        if not graph_node_ids:
            graph_node_ids = [source for source in node.source_ref if source in graph_node_by_id]
        ordered_graph_node_ids = tuple(dict.fromkeys(graph_node_ids))
        primary_graph_node_id = ordered_graph_node_ids[0] if ordered_graph_node_ids else None
        graph_provenance = graph_node_provenance_by_id.get(primary_graph_node_id) if primary_graph_node_id is not None else None
        provenance_by_id[node.node_id] = DiagnosisProvenance(
            normalized_node_id=node.node_id,
            graph_node_id=primary_graph_node_id,
            graph_node_ids=ordered_graph_node_ids,
            layer_id=None if graph_provenance is None else graph_provenance.layer_id,
            structure_id=(f"structure.unmapped.{primary_graph_node_id or node.node_id}" if graph_provenance is None else graph_provenance.structure_id),
            structure_kind=("unmapped_structure" if graph_provenance is None else graph_provenance.structure_kind),
        )
    return provenance_by_id


def _build_block_ids_by_normalized_node(schedule_ir: ScheduleIR) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for block in schedule_ir.blocks:
        if block.node_id is not None:
            grouped.setdefault(block.node_id, []).append(block.block_id)
    return {node_id: tuple(block_ids) for node_id, block_ids in grouped.items()}


def _structure_bucket_key(node: GraphNode) -> tuple[int | None, str]:
    source_hints = " ".join([*node.source_ref, *node.audit_ref.source_ids, node.node_id]).lower()
    layer_match = _LAYER_PATTERN.search(source_hints)
    layer_id = int(layer_match.group(1)) if layer_match else None
    if "embed" in source_hints:
        return (None, "embedding")
    if "self_attn" in source_hints or "attention" in source_hints:
        return (layer_id, "attention_block")
    if "mlp" in source_hints:
        return (layer_id, "mlp_block")
    return (layer_id, "auxiliary_block")


def _structure_id(layer_id: int | None, structure_kind: str) -> str:
    if layer_id is None:
        return f"structure.{structure_kind}"
    return f"structure.layer{layer_id}.{structure_kind}"


__all__ = [
    "DiagnosisContext",
    "DiagnosisProvenance",
    "ReportKind",
    "ScheduleKind",
    "TopLevelDiagnosisReport",
    "build_diagnosis_context",
    "load_top_level_report",
    "resolve_report_kind",
    "resolve_schedule_artifact_path",
    "resolve_schedule_kind",
]
