"""Frozen schema registry for diagnosis dataset CSV artifacts."""

from __future__ import annotations

from enum import StrEnum
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, create_model

ScalarValue = str | int | float
FieldTypeName = Literal["str", "int", "float", "bool", "scalar"]


class SourceLayer(StrEnum):
    STATIC_MODEL = "static_model"
    SCENARIO_INSTANTIATED = "scenario_instantiated"
    PLANNING_DERIVED = "planning_derived"
    EXECUTION_DERIVED = "execution_derived"
    CROSS_STAGE_SUMMARY = "cross_stage_summary"


class DiagnosisDatasetTableCategory(StrEnum):
    CORE = "core"
    VIEW = "view"
    RELATION = "relation"


class DiagnosisFieldSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type_name: FieldTypeName
    source_layer: SourceLayer
    nullable: bool = False
    unit: str
    description: str
    heuristic_note: str = "direct export"
    allowed_values: tuple[str, ...] = ()


class DiagnosisTableSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    table_name: str
    stage: str
    category: DiagnosisDatasetTableCategory
    description: str
    primary_key: tuple[str, ...]
    fields: tuple[DiagnosisFieldSchema, ...]
    notes: tuple[str, ...] = ()
    row_model: type[BaseModel]

    @property
    def csv_columns(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)


class DiagnosisDatasetRow(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _desc(name: str) -> str:
    return name.replace("_", " ")


def _field(
    name: str,
    type_name: FieldTypeName,
    source_layer: SourceLayer,
    unit: str,
    *,
    nullable: bool = False,
    heuristic_note: str = "direct export",
    allowed_values: tuple[str, ...] = (),
) -> DiagnosisFieldSchema:
    return DiagnosisFieldSchema(
        name=name,
        type_name=type_name,
        source_layer=source_layer,
        nullable=nullable,
        unit=unit,
        description=_desc(name),
        heuristic_note=heuristic_note,
        allowed_values=allowed_values,
    )


def _annotation_for(type_name: FieldTypeName) -> Any:
    if type_name == "str":
        return str
    if type_name == "int":
        return int
    if type_name == "float":
        return float
    if type_name == "bool":
        return bool
    if type_name == "scalar":
        return ScalarValue
    raise ValueError(f"unsupported type_name: {type_name}")


def _row_model_name(table_name: str) -> str:
    stem = table_name.removesuffix(".csv")
    parts = re.split(r"[^a-zA-Z0-9]+", stem)
    return "".join(part.capitalize() for part in parts if part) + "Row"


def _build_row_model(table_name: str, fields: tuple[DiagnosisFieldSchema, ...]) -> type[BaseModel]:
    model_fields: dict[str, tuple[Any, Any]] = {}
    for field in fields:
        annotation = _annotation_for(field.type_name)
        if field.nullable:
            annotation = annotation | None
        model_fields[field.name] = (annotation, Field(default=None if field.nullable else ...))
    return create_model(_row_model_name(table_name), __base__=DiagnosisDatasetRow, **model_fields)


def _table(
    table_name: str,
    stage: str,
    category: DiagnosisDatasetTableCategory,
    primary_key: tuple[str, ...],
    fields: tuple[DiagnosisFieldSchema, ...],
    *,
    description: str = "",
    notes: tuple[str, ...] = (),
) -> DiagnosisTableSchema:
    return DiagnosisTableSchema(
        table_name=table_name,
        stage=stage,
        category=category,
        description=description or table_name,
        primary_key=primary_key,
        fields=fields,
        notes=notes,
        row_model=_build_row_model(table_name, fields),
    )


CORE = DiagnosisDatasetTableCategory.CORE
VIEW = DiagnosisDatasetTableCategory.VIEW
RELATION = DiagnosisDatasetTableCategory.RELATION
STATIC = SourceLayer.STATIC_MODEL
SCENARIO = SourceLayer.SCENARIO_INSTANTIATED
PLAN = SourceLayer.PLANNING_DERIVED
EXEC = SourceLayer.EXECUTION_DERIVED
SUMMARY = SourceLayer.CROSS_STAGE_SUMMARY
SUPPORT_STATUS = ("native", "constrained", "fallback", "unsupported")
RECOVERABILITY = ("none", "low", "medium", "high")
GAP_CONFIDENCE = ("low", "medium", "high")
PRESSURE_STATUS = ("ok", "warning", "critical")


TABLE_SCHEMAS = (
    _table("structure_inventory.csv", "Stage 1", CORE, ("structure_id",), (
        _field("structure_id", "str", STATIC, "identifier"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("layer_id", "int", STATIC, "index"),
        _field("node_count", "int", STATIC, "count"),
        _field("input_shape", "str", STATIC, "shape"),
        _field("output_shape", "str", STATIC, "shape"),
        _field("dtype", "str", STATIC, "dtype"),
        _field("parameter_count", "int", STATIC, "count"),
        _field("parameter_bytes", "int", STATIC, "bytes"),
    )),
    _table("model_summary.csv", "Stage 1", VIEW, ("metric",), (
        _field("metric", "str", SUMMARY, "metric_name"),
        _field("value", "scalar", STATIC, "scalar"),
    ), notes=("flat metric/value summary view",)),
    _table("operator_mapping.csv", "Stage 2", CORE, ("normalized_node_id",), (
        _field("normalized_node_id", "str", PLAN, "identifier"),
        _field("graph_node_id", "str", STATIC, "identifier"),
        _field("canonical_op", "str", STATIC, "kind"),
        _field("macro_op", "str", PLAN, "kind"),
        _field("phase", "str", PLAN, "kind", allowed_values=("projection", "attention", "kv_io", "other")),
        _field("fallback_kind", "str", PLAN, "kind", nullable=True, heuristic_note="null means native lowering"),
        _field("structure_id", "str", STATIC, "identifier"),
        _field("layer_id", "int", STATIC, "index"),
    )),
    _table("macro_op_summary.csv", "Stage 2", VIEW, ("macro_op", "phase"), (
        _field("macro_op", "str", PLAN, "kind"),
        _field("phase", "str", PLAN, "kind"),
        _field("node_count", "int", PLAN, "count"),
        _field("fallback_count", "int", PLAN, "count"),
        _field("helper_count", "int", PLAN, "count"),
        _field("native_count", "int", PLAN, "count"),
    )),
    _table("structure_demand.csv", "Stage 3", CORE, ("structure_id",), (
        _field("structure_id", "str", STATIC, "identifier"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("layer_id", "int", STATIC, "index"),
        _field("compute_ops", "float", SCENARIO, "ops"),
        _field("read_bytes", "float", SCENARIO, "bytes"),
        _field("write_bytes", "float", SCENARIO, "bytes"),
        _field("activation_bytes_estimated", "float", SCENARIO, "bytes", heuristic_note="shape-based estimate"),
        _field("working_set_bytes", "float", PLAN, "bytes", heuristic_note="planning-derived estimate"),
        _field("arithmetic_intensity", "float", SCENARIO, "ops_per_byte"),
        _field("node_count", "int", STATIC, "count"),
    )),
    _table("layer_demand.csv", "Stage 3", CORE, ("layer_id",), (
        _field("layer_id", "int", STATIC, "index"),
        _field("compute_ops", "float", SCENARIO, "ops"),
        _field("read_bytes", "float", SCENARIO, "bytes"),
        _field("write_bytes", "float", SCENARIO, "bytes"),
        _field("activation_bytes_estimated", "float", SCENARIO, "bytes", heuristic_note="shape-based estimate"),
        _field("kv_bytes_estimated", "float", SCENARIO, "bytes", heuristic_note="scenario-dependent estimate"),
        _field("working_set_bytes", "float", PLAN, "bytes"),
        _field("arithmetic_intensity", "float", SCENARIO, "ops_per_byte"),
        _field("node_count", "int", STATIC, "count"),
        _field("dominant_macro_op", "str", PLAN, "kind", heuristic_note="largest aggregate contributor"),
    )),
    _table("subject_demand.csv", "Stage 3", VIEW, ("normalized_node_id",), (
        _field("normalized_node_id", "str", PLAN, "identifier"),
        _field("structure_id", "str", STATIC, "identifier"),
        _field("layer_id", "int", STATIC, "index"),
        _field("macro_op", "str", PLAN, "kind"),
        _field("phase", "str", PLAN, "kind"),
        _field("fallback_kind", "str", PLAN, "kind", nullable=True, heuristic_note="null means native lowering"),
        _field("compute_ops", "float", SCENARIO, "ops"),
        _field("read_bytes", "float", SCENARIO, "bytes"),
        _field("write_bytes", "float", SCENARIO, "bytes"),
        _field("working_set_bytes", "float", PLAN, "bytes"),
        _field("arithmetic_intensity", "float", SCENARIO, "ops_per_byte"),
    )),
    _table("phase_demand_summary.csv", "Stage 3", VIEW, ("phase",), (
        _field("phase", "str", PLAN, "kind"),
        _field("total_compute_ops", "float", SCENARIO, "ops"),
        _field("total_read_bytes", "float", SCENARIO, "bytes"),
        _field("total_write_bytes", "float", SCENARIO, "bytes"),
        _field("total_working_set_bytes", "float", PLAN, "bytes"),
        _field("node_count", "int", PLAN, "count"),
        _field("share_of_total_compute", "float", SUMMARY, "ratio"),
        _field("share_of_total_bytes", "float", SUMMARY, "ratio"),
    )),
    _table("demand_hotspot_top20.csv", "Stage 3", VIEW, ("rank",), (
        _field("rank", "int", SUMMARY, "rank"),
        _field("normalized_node_id", "str", PLAN, "identifier"),
        _field("layer_id", "int", STATIC, "index"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("macro_op", "str", PLAN, "kind"),
        _field("compute_ops", "float", SCENARIO, "ops"),
        _field("total_bytes", "float", SUMMARY, "bytes"),
        _field("arithmetic_intensity", "float", SCENARIO, "ops_per_byte"),
    )),
    _table("structure_support_matrix.csv", "Stage 4", CORE, ("structure_id",), (
        _field("structure_id", "str", STATIC, "identifier"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("layer_id", "int", STATIC, "index"),
        _field("worst_support_status", "str", PLAN, "status", allowed_values=SUPPORT_STATUS),
        _field("native_count", "int", PLAN, "count"),
        _field("constrained_count", "int", PLAN, "count"),
        _field("fallback_count", "int", PLAN, "count"),
        _field("unsupported_count", "int", PLAN, "count"),
        _field("blocking_gap_count", "int", PLAN, "count"),
        _field("top_reason_code", "str", PLAN, "kind", heuristic_note="dominant reason by severity+count"),
    )),
    _table("critical_gaps.csv", "Stage 4", VIEW, ("normalized_node_id", "reason_code"), (
        _field("normalized_node_id", "str", PLAN, "identifier", heuristic_note="P0-T3 confirms mixed-granularity subject key"),
        _field("subject_kind", "str", SUMMARY, "kind", heuristic_note="P0-T3 confirms node vs structure semantics"),
        _field("support_status", "str", PLAN, "status", allowed_values=SUPPORT_STATUS),
        _field("reason_code", "str", PLAN, "kind"),
        _field("message", "str", SUMMARY, "text"),
    ), notes=("primary-key semantics still need P0-T3 spike confirmation",)),
    _table("schedule_blocks.csv", "Stage 5", CORE, ("block_id",), (
        _field("block_id", "str", PLAN, "identifier"),
        _field("normalized_node_id", "str", PLAN, "identifier"),
        _field("macro_op", "str", PLAN, "kind"),
        _field("schedule_stage", "str", PLAN, "kind"),
        _field("core_id", "int", PLAN, "index", heuristic_note="P0-T3 confirms dual-core transfer encoding"),
        _field("start_slot", "int", PLAN, "slots"),
        _field("end_slot", "int", PLAN, "slots"),
        _field("duration_slots", "int", PLAN, "slots"),
        _field("stall_reason", "str", PLAN, "kind", nullable=True, heuristic_note="present only when schedule diagnostics expose one"),
    ), notes=("P0-T3 confirms whether a multi-core encoding is required",)),
    _table("core_utilization.csv", "Stage 5", VIEW, ("core_id",), (
        _field("core_id", "int", PLAN, "index"),
        _field("occupied_slots", "int", PLAN, "slots"),
        _field("makespan_slots", "int", PLAN, "slots"),
        _field("utilization_ratio", "float", SUMMARY, "ratio"),
        _field("block_count", "int", PLAN, "count"),
    )),
    _table("perf_by_structure.csv", "Stage 6", CORE, ("structure_id",), (
        _field("structure_id", "str", STATIC, "identifier"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("layer_id", "int", STATIC, "index"),
        _field("estimated_cycles", "float", EXEC, "cycles"),
        _field("fitted_work_cycles", "float", EXEC, "cycles"),
        _field("cycle_share", "float", SUMMARY, "ratio"),
        _field("total_bytes", "float", EXEC, "bytes"),
        _field("dominant_bound", "str", EXEC, "kind"),
        _field("worst_support_status", "str", PLAN, "status", allowed_values=SUPPORT_STATUS),
    )),
    _table("node_hotspot_top30.csv", "Stage 6", VIEW, ("rank",), (
        _field("rank", "int", SUMMARY, "rank"),
        _field("normalized_node_id", "str", PLAN, "identifier"),
        _field("layer_id", "int", STATIC, "index"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("phase", "str", PLAN, "kind"),
        _field("macro_op", "str", PLAN, "kind"),
        _field("support_status", "str", PLAN, "status", allowed_values=SUPPORT_STATUS),
        _field("bound_kind", "str", EXEC, "kind"),
        _field("estimated_cycles", "float", EXEC, "cycles"),
        _field("cycle_share", "float", SUMMARY, "ratio"),
        _field("total_bytes", "float", EXEC, "bytes"),
    )),
    _table("phase_breakdown.csv", "Stage 6", VIEW, ("phase",), (
        _field("phase", "str", PLAN, "kind"),
        _field("estimated_cycles", "float", EXEC, "cycles"),
        _field("fitted_work_cycles", "float", EXEC, "cycles"),
        _field("critical_path_share", "float", SUMMARY, "ratio"),
        _field("total_bytes", "float", EXEC, "bytes"),
    )),
    _table("realization_gap.csv", "Stage 6.5", CORE, ("structure_id",), (
        _field("structure_id", "str", STATIC, "identifier"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("layer_id", "int", STATIC, "index"),
        _field("theoretical_compute_ops", "float", SCENARIO, "ops"),
        _field("theoretical_bytes", "float", SCENARIO, "bytes"),
        _field("theoretical_ai", "float", SCENARIO, "ops_per_byte"),
        _field("scheduled_duration_slots", "int", PLAN, "slots"),
        _field("estimated_cycles", "float", EXEC, "cycles"),
        _field("fitted_cycles", "float", EXEC, "cycles"),
        _field("worst_support_status", "str", PLAN, "status", allowed_values=SUPPORT_STATUS),
        _field("support_penalty_score", "float", SUMMARY, "score", heuristic_note="heuristic non-physical score"),
        _field("fallback_ratio", "float", SUMMARY, "ratio"),
        _field("sync_penalty_slots", "float", SUMMARY, "slots", heuristic_note="heuristic attribution"),
        _field("overlap_loss_slots", "float", SUMMARY, "slots", heuristic_note="heuristic attribution"),
        _field("effective_ai", "float", SUMMARY, "ops_per_byte", heuristic_note="derived effective metric"),
        _field("theoretical_ai_no_penalty", "float", SUMMARY, "ops_per_byte", heuristic_note="penalty-free comparison metric"),
        _field("gap_kind", "str", SUMMARY, "kind"),
        _field("gap_score", "float", SUMMARY, "score", heuristic_note="heuristic non-physical score"),
        _field("gap_confidence", "str", SUMMARY, "confidence", heuristic_note="required qualitative confidence", allowed_values=GAP_CONFIDENCE),
    ), notes=("derived fields must be backed by explicit formulas before writer work",)),
    _table("bottleneck_summary.csv", "Stage 7", CORE, ("bottleneck_kind",), (
        _field("bottleneck_kind", "str", SUMMARY, "kind"),
        _field("node_count", "int", EXEC, "count"),
        _field("cycle_share", "float", SUMMARY, "ratio"),
        _field("share_of_total", "float", SUMMARY, "ratio"),
    )),
    _table("structure_bottleneck.csv", "Stage 7", VIEW, ("structure_id",), (
        _field("structure_id", "str", STATIC, "identifier"),
        _field("structure_kind", "str", STATIC, "kind"),
        _field("layer_id", "int", STATIC, "index"),
        _field("dominant_bound_kind", "str", EXEC, "kind"),
        _field("bound_cycle_share", "float", SUMMARY, "ratio"),
        _field("support_gap_count", "int", PLAN, "count"),
        _field("gap_score", "float", SUMMARY, "score", heuristic_note="heuristic non-physical score"),
    )),
    _table("pressure_summary.csv", "Stage 7", VIEW, ("metric",), (
        _field("metric", "str", SUMMARY, "metric_name"),
        _field("value", "scalar", EXEC, "scalar"),
        _field("threshold", "scalar", SUMMARY, "scalar", heuristic_note="policy threshold"),
        _field("status", "str", SUMMARY, "status", allowed_values=PRESSURE_STATUS),
    )),
    _table("roofline_points_by_layer.csv", "Stage 7", VIEW, ("layer_id",), (
        _field("layer_id", "int", STATIC, "index"),
        _field("arithmetic_intensity", "float", SCENARIO, "ops_per_byte"),
        _field("achieved_throughput", "float", EXEC, "throughput"),
        _field("peak_compute", "float", SUMMARY, "throughput"),
        _field("peak_bandwidth", "float", SUMMARY, "bandwidth"),
        _field("bound_kind", "str", EXEC, "kind"),
        _field("headroom_ratio", "float", SUMMARY, "ratio"),
    )),
    _table("timeline_loss_detail.csv", "Stage 8", CORE, ("core_id", "start_slot", "end_slot"), (
        _field("core_id", "int", PLAN, "index"),
        _field("start_slot", "int", PLAN, "slots"),
        _field("end_slot", "int", PLAN, "slots"),
        _field("span_slots", "int", PLAN, "slots"),
        _field("loss_kind", "str", PLAN, "kind"),
        _field("recoverability", "str", SUMMARY, "kind", heuristic_note="bucketed estimate", allowed_values=RECOVERABILITY),
        _field("recoverable_slots_estimated", "float", SUMMARY, "slots", heuristic_note="high=0.8, medium=0.4, low=0.1, none=0"),
        _field("preceding_block_id", "str", PLAN, "identifier", nullable=True),
        _field("following_block_id", "str", PLAN, "identifier", nullable=True),
    )),
    _table("timeline_loss_summary.csv", "Stage 8", CORE, ("loss_kind",), (
        _field("loss_kind", "str", SUMMARY, "kind"),
        _field("total_slots", "float", SUMMARY, "slots"),
        _field("event_count", "int", SUMMARY, "count"),
        _field("share_of_makespan", "float", SUMMARY, "ratio"),
        _field("recoverable_slots_total", "float", SUMMARY, "slots"),
        _field("recoverable_share_of_makespan", "float", SUMMARY, "ratio"),
        _field("representative_entities", "str", SUMMARY, "text", heuristic_note="P0-T3 resolves string vs relation representation"),
    ), notes=("representative_entities is provisional because CSV arrays are disallowed",)),
    _table("assessment_summary.csv", "Stage 9", CORE, ("metric",), (
        _field("metric", "str", SUMMARY, "metric_name"),
        _field("value", "scalar", SUMMARY, "scalar"),
        _field("interpretation", "str", SUMMARY, "text"),
    )),
    _table("recommendations.csv", "Stage 9", VIEW, ("priority",), (
        _field("priority", "int", SUMMARY, "rank"),
        _field("category", "str", SUMMARY, "kind"),
        _field("title", "str", SUMMARY, "text"),
        _field("action", "str", SUMMARY, "text"),
        _field("rationale", "str", SUMMARY, "text"),
    )),
    _table("subject_structure_map.csv", "Relation", RELATION, ("normalized_node_id",), (
        _field("normalized_node_id", "str", PLAN, "identifier"),
        _field("structure_id", "str", STATIC, "identifier"),
        _field("layer_id", "int", STATIC, "index"),
    )),
    _table("subject_block_map.csv", "Relation", RELATION, ("normalized_node_id", "block_id"), (
        _field("normalized_node_id", "str", PLAN, "identifier"),
        _field("block_id", "str", PLAN, "identifier"),
    )),
    _table("block_descriptor_map.csv", "Relation", RELATION, ("block_id", "descriptor_id"), (
        _field("block_id", "str", PLAN, "identifier"),
        _field("descriptor_id", "str", PLAN, "identifier"),
    ), notes=("P0-T3 confirms 1:n block-to-descriptor behavior",)),
)

DIAGNOSIS_DATASET_SCHEMA_REGISTRY: dict[str, DiagnosisTableSchema] = {schema.table_name: schema for schema in TABLE_SCHEMAS}


def list_diagnosis_table_schemas() -> tuple[DiagnosisTableSchema, ...]:
    return tuple(DIAGNOSIS_DATASET_SCHEMA_REGISTRY.values())


def get_diagnosis_table_schema(table_name: str) -> DiagnosisTableSchema:
    try:
        return DIAGNOSIS_DATASET_SCHEMA_REGISTRY[table_name]
    except KeyError as exc:
        raise KeyError(f"unknown diagnosis dataset table: {table_name}") from exc


def get_diagnosis_row_model(table_name: str) -> type[BaseModel]:
    return get_diagnosis_table_schema(table_name).row_model


def validate_diagnosis_dataset_row(table_name: str, row: dict[str, Any]) -> BaseModel:
    return get_diagnosis_row_model(table_name).model_validate(row)


def validate_diagnosis_dataset_rows(table_name: str, rows: list[dict[str, Any]]) -> list[BaseModel]:
    row_model = get_diagnosis_row_model(table_name)
    return [row_model.model_validate(row) for row in rows]


__all__ = [
    "DIAGNOSIS_DATASET_SCHEMA_REGISTRY",
    "DiagnosisDatasetRow",
    "DiagnosisDatasetTableCategory",
    "DiagnosisFieldSchema",
    "DiagnosisTableSchema",
    "SourceLayer",
    "get_diagnosis_row_model",
    "get_diagnosis_table_schema",
    "list_diagnosis_table_schemas",
    "validate_diagnosis_dataset_row",
    "validate_diagnosis_dataset_rows",
]
