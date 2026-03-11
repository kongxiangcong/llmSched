"""Contracts for SPEC-19 cross-run visualization catalogs."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CatalogSortKey = Literal["primary_metric", "run_id", "scenario_name"]


class VisualizationCatalogMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_by: str
    entry_count: int = Field(ge=0)
    default_sort_key: CatalogSortKey = "primary_metric"


class VisualizationCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str
    run_id: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    schedule_kind: Literal["single-core", "dual-core"]
    target_profile_name: str
    primary_metric_name: str
    primary_metric_value: float
    workbench_entry_path: str


class VisualizationCatalogArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    title: str
    metadata: VisualizationCatalogMetadata
    entries: list[VisualizationCatalogEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entries(self) -> "VisualizationCatalogArtifact":
        entry_ids = [entry.entry_id for entry in self.entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("duplicate catalog entry ids are not allowed")
        if self.metadata.entry_count != len(self.entries):
            raise ValueError("metadata.entry_count must match entries length")
        return self
