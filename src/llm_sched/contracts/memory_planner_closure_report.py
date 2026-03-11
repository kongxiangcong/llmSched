"""Contracts for SPEC-08 memory-planner closure evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MemoryPlannerConsumerId = Literal[
    "tile_planning",
    "descriptor_generation",
    "performance_estimation",
    "prefill_evaluation",
    "decode_evaluation",
    "visualization_packaging",
    "visualization_workbench",
]
MemoryPlannerConsumerStatus = Literal[
    "verified",
    "missing_artifact",
    "missing_evidence",
    "not_applicable",
]
MemoryPlannerAcceptanceStatus = Literal["in_progress", "ready_for_acceptance"]


class MemoryPlannerSurfaceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_binding_count: int = Field(ge=0)
    region_count: int = Field(ge=0)
    regions_with_memory_class_attribution: int = Field(ge=0)
    regions_with_backing_store_attribution: int = Field(ge=0)
    bound_address_diagnostic_count: int = Field(ge=0)
    unresolved_address_diagnostic_count: int = Field(ge=0)


class MemoryPlannerClosureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MemoryPlannerAcceptanceStatus
    active_region_count: int = Field(ge=0)
    attributed_memory_class_region_count: int = Field(ge=0)
    attributed_backing_store_region_count: int = Field(ge=0)
    overflow_region_count: int = Field(ge=0)
    unresolved_address_diagnostic_count: int = Field(ge=0)
    remaining_gaps: list[str] = Field(default_factory=list)


class MemoryPlannerConsumerEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consumer_id: MemoryPlannerConsumerId
    required_for_acceptance: bool
    status: MemoryPlannerConsumerStatus
    artifact_key: str | None = None
    artifact_path: str | None = None
    consumed_fields: list[str] = Field(default_factory=list)
    message: str


class MemoryPlannerAcceptanceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MemoryPlannerAcceptanceStatus
    verified_required_consumer_count: int = Field(ge=0)
    required_consumer_count: int = Field(ge=0)
    verified_optional_consumer_count: int = Field(ge=0)
    optional_consumer_count: int = Field(ge=0)
    remaining_gaps: list[str] = Field(default_factory=list)


class MemoryPlannerClosureReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    schedule_kind: Literal["single-core", "dual-core"]
    memory_plan_path: str
    planner_surface: MemoryPlannerSurfaceSummary
    planner_closure: MemoryPlannerClosureSummary
    downstream_consumers: list[MemoryPlannerConsumerEvidence] = Field(default_factory=list)
    acceptance: MemoryPlannerAcceptanceSummary
