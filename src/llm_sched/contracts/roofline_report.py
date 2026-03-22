"""DIAG-07 roofline report contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DiagnosisReportKind = Literal["prefill", "decode"]
RooflineBoundKind = Literal["compute", "bandwidth"]


class ComputeCeiling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ceiling_id: str
    label: str
    peak_ops_per_cycle: float = Field(ge=0.0)


class BandwidthCeiling(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ceiling_id: str
    label: str
    bandwidth_bytes_per_cycle: float = Field(ge=0.0)


class NodeRooflinePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    layer_id: int | None = Field(default=None, ge=0)
    macro_op: str | None = None
    phase: str | None = None
    arithmetic_intensity: float = Field(ge=0.0)
    achieved_ops_per_cycle: float = Field(ge=0.0)
    compute_ops: float = Field(ge=0.0)
    total_bytes: float = Field(ge=0.0)
    dominant_bound: RooflineBoundKind
    active_bandwidth_ceiling_id: str | None = None
    headroom_ratio: float = Field(ge=0.0)


class LayerRooflinePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    structure_ids: list[str] = Field(default_factory=list)
    node_count: int = Field(ge=0)
    arithmetic_intensity: float = Field(ge=0.0)
    achieved_ops_per_cycle: float = Field(ge=0.0)
    compute_ops: float = Field(ge=0.0)
    total_bytes: float = Field(ge=0.0)
    dominant_bound: RooflineBoundKind
    active_bandwidth_ceiling_id: str | None = None
    headroom_ratio: float = Field(ge=0.0)


class DominantBoundSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominant_bound: RooflineBoundKind
    node_counts: dict[RooflineBoundKind, int] = Field(default_factory=dict)
    layer_counts: dict[RooflineBoundKind, int] = Field(default_factory=dict)
    top_node_ids: list[str] = Field(default_factory=list)
    top_layer_ids: list[int] = Field(default_factory=list)


class HeadroomSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_headroom_ratio: float = Field(ge=0.0)
    mean_headroom_ratio: float = Field(ge=0.0)
    most_limited_node_id: str | None = None
    most_limited_layer_id: int | None = Field(default=None, ge=0)
    top_headroom_node_ids: list[str] = Field(default_factory=list)
    top_headroom_layer_ids: list[int] = Field(default_factory=list)


class RooflineReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    schedule_kind: str
    report_kind: DiagnosisReportKind
    compute_ceiling: ComputeCeiling
    bandwidth_ceilings: list[BandwidthCeiling] = Field(default_factory=list)
    node_points: list[NodeRooflinePoint] = Field(default_factory=list)
    layer_points: list[LayerRooflinePoint] = Field(default_factory=list)
    dominant_bound_summary: DominantBoundSummary
    headroom_summary: HeadroomSummary
