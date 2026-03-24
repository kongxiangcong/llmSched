"""CSV writer for diagnosis dataset artifacts."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from llm_sched.analysis.architecture_assessment_report_builder import (
    _extract_assessment_summary_rows,
    _extract_recommendation_rows,
)
from llm_sched.analysis.model_structure_report_builder import (
    _extract_model_summary_rows,
    _extract_structure_inventory_rows,
)
from llm_sched.analysis.operator_representation_report_builder import (
    _extract_macro_op_summary_rows,
    _extract_operator_mapping_rows,
)
from llm_sched.analysis.realization_gap_builder import build_realization_gap_rows
from llm_sched.analysis.timeline_loss_builder import (
    build_timeline_loss_detail_rows,
    build_timeline_loss_summary_rows,
)
from llm_sched.analysis.performance_diagnostics_report_builder import (
    _extract_bottleneck_summary_rows,
    _extract_node_hotspot_rows,
    _extract_perf_by_structure_rows,
    _extract_phase_breakdown_rows,
    _extract_pressure_summary_rows,
    _extract_structure_bottleneck_rows,
)
from llm_sched.analysis.resource_demand_report_builder import (
    _extract_demand_hotspot_top20_rows,
    _extract_layer_demand_rows,
    _extract_phase_demand_summary_rows,
    _extract_structure_demand_rows,
    _extract_subject_demand_rows,
)
from llm_sched.analysis.roofline_report_builder import _extract_roofline_points_by_layer_rows
from llm_sched.analysis.schedule_diagnostics_report_builder import (
    _extract_core_utilization_rows,
    _extract_schedule_block_rows,
)
from llm_sched.analysis.support_matrix_report_builder import (
    _extract_critical_gaps_rows,
    _extract_structure_support_rows,
)
from llm_sched.contracts.diagnosis_dataset_schema import (
    get_diagnosis_table_schema,
    validate_diagnosis_dataset_rows,
)


def write_diagnosis_dataset(
    dataset_dir: Path,
    *,
    ctx,
    model_structure_report,
    operator_representation_report,
    resource_demand_report,
    support_matrix_report,
    schedule_diagnostics_report,
    performance_diagnostics_report,
    roofline_report,
    architecture_assessment_report,
) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    structure_inventory_rows = _extract_structure_inventory_rows(model_structure_report)
    operator_mapping_rows = _extract_operator_mapping_rows(operator_representation_report, ctx=ctx)
    structure_demand_rows = _extract_structure_demand_rows(resource_demand_report)
    layer_demand_rows = _extract_layer_demand_rows(resource_demand_report)
    subject_demand_rows = _extract_subject_demand_rows(resource_demand_report)
    phase_demand_summary_rows = _extract_phase_demand_summary_rows(resource_demand_report)
    demand_hotspot_rows = _extract_demand_hotspot_top20_rows(resource_demand_report)
    structure_support_rows = _extract_structure_support_rows(support_matrix_report)
    critical_gap_rows = _extract_critical_gaps_rows(support_matrix_report)
    schedule_block_rows = _extract_schedule_block_rows(schedule_diagnostics_report)
    core_utilization_rows = _extract_core_utilization_rows(schedule_diagnostics_report)
    perf_by_structure_rows = _extract_perf_by_structure_rows(performance_diagnostics_report)
    node_hotspot_rows = _extract_node_hotspot_rows(performance_diagnostics_report)
    phase_breakdown_rows = _extract_phase_breakdown_rows(performance_diagnostics_report)
    bottleneck_summary_rows = _extract_bottleneck_summary_rows(performance_diagnostics_report)
    structure_bottleneck_rows = _extract_structure_bottleneck_rows(performance_diagnostics_report)
    pressure_summary_rows = _extract_pressure_summary_rows(performance_diagnostics_report)
    roofline_rows = _extract_roofline_points_by_layer_rows(roofline_report)
    assessment_summary_rows = _extract_assessment_summary_rows(architecture_assessment_report)
    recommendation_rows = _extract_recommendation_rows(architecture_assessment_report)
    subject_structure_map_rows = _extract_subject_structure_map_rows(ctx)
    subject_block_map_rows = _extract_subject_block_map_rows(ctx)
    block_descriptor_map_rows = _extract_block_descriptor_map_rows(ctx)
    realization_gap_rows = build_realization_gap_rows(
        structure_demand_rows=structure_demand_rows,
        structure_support_rows=structure_support_rows,
        schedule_block_rows=schedule_block_rows,
        perf_by_structure_rows=perf_by_structure_rows,
        subject_block_rows=subject_block_map_rows,
    )
    timeline_loss_detail_rows = build_timeline_loss_detail_rows(schedule_diagnostics_report)
    timeline_loss_summary_rows = build_timeline_loss_summary_rows(
        timeline_loss_detail_rows,
        makespan_slots=schedule_diagnostics_report.resource_contention_summary.makespan_slots,
    )
    tables: dict[str, list[dict[str, Any]]] = {
        "structure_inventory.csv": structure_inventory_rows,
        "model_summary.csv": _extract_model_summary_rows(model_structure_report),
        "operator_mapping.csv": operator_mapping_rows,
        "macro_op_summary.csv": _extract_macro_op_summary_rows(operator_representation_report),
        "structure_demand.csv": structure_demand_rows,
        "layer_demand.csv": layer_demand_rows,
        "subject_demand.csv": subject_demand_rows,
        "phase_demand_summary.csv": phase_demand_summary_rows,
        "demand_hotspot_top20.csv": demand_hotspot_rows,
        "structure_support_matrix.csv": structure_support_rows,
        "critical_gaps.csv": critical_gap_rows,
        "schedule_blocks.csv": schedule_block_rows,
        "core_utilization.csv": core_utilization_rows,
        "perf_by_structure.csv": perf_by_structure_rows,
        "node_hotspot_top30.csv": node_hotspot_rows,
        "phase_breakdown.csv": phase_breakdown_rows,
        "bottleneck_summary.csv": bottleneck_summary_rows,
        "structure_bottleneck.csv": structure_bottleneck_rows,
        "pressure_summary.csv": pressure_summary_rows,
        "roofline_points_by_layer.csv": roofline_rows,
        "assessment_summary.csv": assessment_summary_rows,
        "recommendations.csv": recommendation_rows,
        "subject_structure_map.csv": subject_structure_map_rows,
        "subject_block_map.csv": subject_block_map_rows,
        "block_descriptor_map.csv": block_descriptor_map_rows,
        "realization_gap.csv": realization_gap_rows,
        "timeline_loss_detail.csv": timeline_loss_detail_rows,
        "timeline_loss_summary.csv": timeline_loss_summary_rows,
    }
    for table_name, rows in tables.items():
        write_table(dataset_dir, table_name, rows)


def write_table(dataset_dir: Path, table_name: str, rows: list[dict[str, Any]]) -> None:
    schema = get_diagnosis_table_schema(table_name)
    normalized_rows = _normalize_rows_for_schema(table_name, rows)
    validate_diagnosis_dataset_rows(table_name, normalized_rows)
    path = dataset_dir / table_name
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(schema.csv_columns), extrasaction="ignore")
        writer.writeheader()
        for row in normalized_rows:
            writer.writerow({column: _csv_value(row.get(column)) for column in schema.csv_columns})


def _normalize_rows_for_schema(table_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schema = get_diagnosis_table_schema(table_name)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        output = dict(row)
        for field in schema.fields:
            value = output.get(field.name)
            if value is None and not field.nullable:
                if field.type_name == "str":
                    output[field.name] = ""
                elif field.type_name == "int":
                    output[field.name] = 0
                elif field.type_name == "float":
                    output[field.name] = 0.0
                elif field.type_name == "bool":
                    output[field.name] = False
                else:
                    output[field.name] = ""
        normalized.append(output)
    return normalized


def _csv_value(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


__all__ = [
    "write_diagnosis_dataset",
    "write_table",
]



def _extract_subject_structure_map_rows(ctx) -> list[dict[str, object]]:
    return [
        {
            "normalized_node_id": normalized_node_id,
            "structure_id": provenance.structure_id,
            "layer_id": provenance.layer_id,
        }
        for normalized_node_id, provenance in sorted(ctx.normalized_node_provenance_by_id.items())
    ]


def _extract_subject_block_map_rows(ctx) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for normalized_node_id, block_ids in sorted(ctx.block_ids_by_normalized_node_id.items()):
        for block_id in block_ids:
            rows.append({"normalized_node_id": normalized_node_id, "block_id": block_id})
    return rows


def _extract_block_descriptor_map_rows(ctx) -> list[dict[str, object]]:
    return [
        {"block_id": block_id, "descriptor_id": descriptor.descriptor_id}
        for block_id, descriptor in sorted(ctx.descriptor_by_block_id.items())
    ]
