"""Run manifest schema."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    contract_version: str
    status: Literal["initialized", "failed", "completed"] = "initialized"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_path: str
    target_profile_path: str
    scenario_profile_path: str
    artifact_index: dict[str, str]
