"""Machine-readable summary for a CLI run."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.config.loader import Diagnostic


class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: Literal["initialized", "failed", "completed"]
    exit_code: int
    manifest_path: str | None = None
    diagnostics: list[Diagnostic] = []
