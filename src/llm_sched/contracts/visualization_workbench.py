"""Contracts for SPEC-19 visualization workbench artifacts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


WorkbenchPanelId = Literal[
    "summary",
    "graph",
    "timeline",
    "core-occupancy",
    "memory",
    "coverage",
    "sweep",
]
WorkbenchAssetRole = Literal["entry_html", "script", "style", "manifest"]


class VisualizationWorkbenchMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    schedule_kind: Literal["single-core", "dual-core"]
    title: str


class VisualizationWorkbenchAssetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    media_type: str
    role: WorkbenchAssetRole


class VisualizationWorkbenchArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workbench_id: str
    metadata: VisualizationWorkbenchMetadata
    entry_html_path: str
    bundle_path: str
    default_panel: WorkbenchPanelId
    available_panels: list[WorkbenchPanelId] = Field(default_factory=list)
    asset_files: list[VisualizationWorkbenchAssetFile] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_contract(self) -> "VisualizationWorkbenchArtifact":
        if self.default_panel not in self.available_panels:
            raise ValueError("default_panel must be included in available_panels")
        asset_paths = [asset.path for asset in self.asset_files]
        if len(asset_paths) != len(set(asset_paths)):
            raise ValueError("asset file paths must be unique")
        return self
