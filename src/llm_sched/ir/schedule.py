"""Schedule IR schema."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.ir.common import AuditRef


class ScheduleBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    core_id: int | Literal["both"]
    peer_core_id: int | None = None
    node_id: str | None = None
    macro_op: str | None = None
    stage: Literal["dma_in", "prepare", "compute", "store", "transfer"] | None = None
    tiling_candidate_id: str | None = None
    resource_set: list[str]
    buffer_binding: dict[str, str]
    barrier_in: list[str]
    barrier_out: list[str]
    depends_on: list[str] = Field(default_factory=list)
    issue_slot: int = Field(default=0, ge=0)
    duration_slots: int = Field(default=1, ge=1)
    transfer_kind: Literal["dma", "core_link"] | None = None
    transfer_bytes: int = Field(default=0, ge=0)
    sync_cost_cycles: int = Field(default=0, ge=0)
    order_key: int
    audit_ref: AuditRef = Field(default_factory=AuditRef)


class ScheduleIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ir_version: str
    graph_id: str
    core_mode: Literal["single-core", "dual-core"]
    blocks: list[ScheduleBlock]

    @model_validator(mode="after")
    def validate_core_mode_constraints(self) -> "ScheduleIR":
        block_ids = [block.block_id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("schedule block ids must be unique")
        block_by_id = {block.block_id: block for block in self.blocks}
        for block in self.blocks:
            for dependency_id in block.depends_on:
                if dependency_id not in block_by_id:
                    raise ValueError("schedule depends_on entries must reference existing block ids")
                if dependency_id == block.block_id:
                    raise ValueError("schedule blocks must not depend on themselves")
                if block_by_id[dependency_id].order_key >= block.order_key:
                    raise ValueError("schedule depends_on entries must point to earlier order_key blocks")
            if block.peer_core_id is not None and block.core_id != "both" and block.peer_core_id == block.core_id:
                raise ValueError("schedule peer_core_id must differ from core_id")
            if block.stage == "transfer":
                if not block.barrier_in or not block.barrier_out:
                    raise ValueError("transfer blocks must declare barrier_in and barrier_out")
                if block.peer_core_id is None:
                    raise ValueError("transfer blocks must declare peer_core_id")
                if block.transfer_kind is None:
                    raise ValueError("transfer blocks must declare transfer_kind")
                if block.transfer_bytes <= 0:
                    raise ValueError("transfer blocks must declare positive transfer_bytes")
        if self.core_mode == "single-core":
            core_ids = {block.core_id for block in self.blocks}
            if len(core_ids) > 1:
                raise ValueError("single-core schedule blocks must all target the same core")
            if any(block.core_id == "both" for block in self.blocks):
                raise ValueError("single-core schedule blocks must bind to exactly one core")
            if any("Core Link" in block.resource_set for block in self.blocks):
                raise ValueError("single-core schedules must not use Core Link")
            if any(block.barrier_in or block.barrier_out for block in self.blocks):
                raise ValueError("single-core schedules must not declare cross-core barriers")
        return self
