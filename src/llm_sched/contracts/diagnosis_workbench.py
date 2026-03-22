"""Contracts for diagnosis workbench artifacts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DiagnosisWorkbenchPanelId = Literal[
    "summary",
    "model-structure",
    "operator-representation",
    "support-matrix",
    "resource-demand",
    "schedule",
    "timeline",
    "performance",
    "roofline",
    "assessment",
    "compare",
]
DiagnosisWorkbenchAssetRole = Literal["entry_html", "script", "style", "manifest"]


class DiagnosisWorkbenchMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    report_kind: Literal["prefill", "decode"]
    schedule_kind: str
    title: str


class DiagnosisWorkbenchAssetFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    media_type: str
    role: DiagnosisWorkbenchAssetRole


class DiagnosisWorkbenchPanelExportFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    media_type: str


class DiagnosisWorkbenchArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workbench_id: str
    metadata: DiagnosisWorkbenchMetadata
    entry_html_path: str
    bundle_path: str
    default_panel: DiagnosisWorkbenchPanelId
    available_panels: list[DiagnosisWorkbenchPanelId] = Field(default_factory=list)
    deep_links: dict[DiagnosisWorkbenchPanelId, str] = Field(default_factory=dict)
    panel_exports: dict[DiagnosisWorkbenchPanelId, list[DiagnosisWorkbenchPanelExportFile]] = (
        Field(default_factory=dict)
    )
    asset_files: list[DiagnosisWorkbenchAssetFile] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_contract(self) -> "DiagnosisWorkbenchArtifact":
        if self.default_panel not in self.available_panels:
            raise ValueError("default_panel must be included in available_panels")
        if set(self.deep_links) != set(self.available_panels):
            raise ValueError("deep_links keys must exactly match available_panels")
        asset_paths = [asset.path for asset in self.asset_files]
        if len(asset_paths) != len(set(asset_paths)):
            raise ValueError("asset file paths must be unique")
        return self
