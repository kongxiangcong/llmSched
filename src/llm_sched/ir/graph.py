"""Graph IR schema."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.ir.common import AuditRef


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    op_kind: str
    inputs: list[str]
    outputs: list[str]
    shape: list[int] = Field(default_factory=list)
    dtype: str
    attrs: dict[str, Any] = Field(default_factory=dict)
    source_ref: list[str] = Field(default_factory=list)
    audit_ref: AuditRef = Field(default_factory=AuditRef)


class GraphIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ir_version: str
    graph_id: str
    nodes: list[GraphNode]

    @model_validator(mode="after")
    def validate_unique_node_ids(self) -> "GraphIR":
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("graph node ids must be unique")
        return self
