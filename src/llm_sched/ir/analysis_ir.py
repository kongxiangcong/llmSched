"""Analysis IR schema."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.ir.common import AuditRef


class AnalysisRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    subject_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    audit_ref: AuditRef = Field(default_factory=AuditRef)


class AnalysisIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ir_version: str
    graph_id: str
    records: list[AnalysisRecord]

    @model_validator(mode="after")
    def validate_unique_record_ids(self) -> "AnalysisIR":
        record_ids = [record.record_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("analysis record ids must be unique")
        return self
