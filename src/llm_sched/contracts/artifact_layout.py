"""Canonical artifact layout for a run."""

from pathlib import Path

from pydantic import BaseModel


class ArtifactLayout(BaseModel):
    run_root: Path
    artifacts_dir: Path
    reports_dir: Path
    logs_dir: Path
    dumps_dir: Path


def build_run_layout(run_root: Path) -> ArtifactLayout:
    return ArtifactLayout(
        run_root=run_root,
        artifacts_dir=run_root / "artifacts",
        reports_dir=run_root / "reports",
        logs_dir=run_root / "logs",
        dumps_dir=run_root / "dumps",
    )
