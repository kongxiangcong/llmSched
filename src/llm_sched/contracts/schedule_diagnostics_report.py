"""DIAG-05 schedule diagnostics report contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ScheduleStage = Literal["dma_in", "prepare", "compute", "store", "transfer"]


class ScheduleDiagnosticBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    node_id: str | None = None
    macro_op: str | None = None
    stage: ScheduleStage | None = None
    core_ids: list[int] = Field(default_factory=list)
    issue_slot: int = Field(ge=0)
    duration_slots: int = Field(ge=1)
    start_slot: int = Field(ge=0)
    end_slot: int = Field(ge=0)
    span_slots: int = Field(ge=0)
    depends_on: list[str] = Field(default_factory=list)
    stall_reason: str | None = None
    wait_for_block_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_schedule_span(self) -> "ScheduleDiagnosticBlock":
        expected_start = self.issue_slot
        expected_end = self.issue_slot + self.duration_slots
        expected_span = self.duration_slots
        if self.start_slot != expected_start:
            raise ValueError("schedule diagnostic block start_slot must match issue_slot")
        if self.end_slot != expected_end:
            raise ValueError("schedule diagnostic block end_slot must match issue_slot + duration_slots")
        if self.span_slots != expected_span:
            raise ValueError("schedule diagnostic block span_slots must match duration_slots")
        return self


class CoreLaneOccupancy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core_id: int = Field(ge=0)
    occupied_slots: int = Field(ge=0)
    makespan_slots: int = Field(ge=0)
    utilization_ratio: float = Field(ge=0.0, le=1.0)
    block_ids: list[str] = Field(default_factory=list)


class IdleSpanEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core_id: int = Field(ge=0)
    start_slot: int = Field(ge=0)
    end_slot: int = Field(ge=0)
    span_slots: int = Field(ge=0)
    reason: str
    preceding_block_id: str | None = None
    following_block_id: str | None = None

    @model_validator(mode="after")
    def validate_span(self) -> "IdleSpanEntry":
        if self.end_slot - self.start_slot != self.span_slots:
            raise ValueError("idle span span_slots must match end_slot - start_slot")
        return self


class StallEventEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    core_id: int = Field(ge=0)
    start_slot: int = Field(ge=0)
    end_slot: int = Field(ge=0)
    span_slots: int = Field(ge=0)
    reason: str
    wait_for_block_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_span(self) -> "StallEventEntry":
        if self.end_slot - self.start_slot != self.span_slots:
            raise ValueError("stall event span_slots must match end_slot - start_slot")
        return self


class ResourceContentionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    makespan_slots: int = Field(ge=0)
    contention_slots: int = Field(ge=0)
    contention_ratio: float = Field(ge=0.0, le=1.0)
    contended_resources: dict[str, int] = Field(default_factory=dict)
    top_contention_block_ids: list[str] = Field(default_factory=list)


class ScheduleDiagnosticsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    blocks: list[ScheduleDiagnosticBlock] = Field(default_factory=list)
    core_lanes: list[CoreLaneOccupancy] = Field(default_factory=list)
    idle_spans: list[IdleSpanEntry] = Field(default_factory=list)
    stall_events: list[StallEventEntry] = Field(default_factory=list)
    critical_path_blocks: list[str] = Field(default_factory=list)
    resource_contention_summary: ResourceContentionSummary
