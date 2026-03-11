"""Contracts for ISA coverage reporting derived from schedule-to-descriptor mapping."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ISACoverageIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    schedule_block_id: str
    core_id: int | Literal["both"]
    stage: str
    macro_op: str | None = None
    requested_opcode: str
    code: str
    message: str


class ISACoverageReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    schedule_kind: Literal["single-core", "dual-core"]
    mapped_descriptor_count: int = Field(ge=0)
    unmapped_block_count: int = Field(ge=0)
    opcode_counts: dict[str, int] = Field(default_factory=dict)
    gap_counts: dict[str, int] = Field(default_factory=dict)
    issues: list[ISACoverageIssue] = Field(default_factory=list)
