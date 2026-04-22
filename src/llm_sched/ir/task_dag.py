"""TaskDAG IR schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.ir.common import AuditRef


class TaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_task_id: str
    tensor_name: str


class TaskOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tensor_name: str
    shape: list[int] = Field(default_factory=list)


class TaskNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    macro_op: str
    inputs: list[TaskInput] = Field(default_factory=list)
    outputs: list[TaskOutput] = Field(default_factory=list)
    attrs: dict[str, Any] = Field(default_factory=dict)
    audit_ref: AuditRef = Field(default_factory=AuditRef)


class TaskDAG(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ir_version: str
    graph_id: str
    nodes: list[TaskNode]
    output_tasks: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_task_ids(self) -> "TaskDAG":
        task_ids = [node.task_id for node in self.nodes]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("task ids must be unique")
        return self

    @property
    def edges(self) -> dict[str, list[str]]:
        return {
            node.task_id: sorted(
                {inp.source_task_id for inp in node.inputs}
            )
            for node in self.nodes
        }
