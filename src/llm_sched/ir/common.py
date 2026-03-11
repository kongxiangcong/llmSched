"""Shared IR helper models."""

from pydantic import BaseModel, ConfigDict, Field


class AuditRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_node_ids: list[str] = Field(default_factory=list)
    nig_node_ids: list[str] = Field(default_factory=list)
    schedule_block_ids: list[str] = Field(default_factory=list)
    descriptor_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
