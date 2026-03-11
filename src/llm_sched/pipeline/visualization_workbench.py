"""Run-root workflow for SPEC-19 static visualization workbench packaging."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.config.loader import Diagnostic
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.visualization import build_visualization_workbench


class VisualizationWorkbenchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    entry_html_path: Path | None = None
    workbench_manifest_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_visualization_workbench(run_root: str | Path) -> VisualizationWorkbenchResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)
        bundle_path = layout.run_root / Path(
            artifact_index.get("visualization_bundle", "reports/visualization_bundle.json")
        )
        if not bundle_path.is_file():
            raise FileNotFoundError(f"visualization_bundle not found at {bundle_path}")

        bundle = VisualizationBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
        workbench_root = Path("workbench")
        bundle_relative_path = _relative_path(layout.run_root / workbench_root, bundle_path)
        artifact, files = build_visualization_workbench(
            bundle,
            bundle_relative_path=bundle_relative_path,
            workbench_root=workbench_root,
        )

        for relative_path, content in files.items():
            output_path = layout.run_root / Path(relative_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

        entry_html_path = layout.run_root / Path(artifact.entry_html_path)
        workbench_manifest_path = layout.run_root / "workbench" / "workbench_manifest.json"
        artifact_index.update(
            {
                "visualization_workbench_entry": _relative_to_run(layout.run_root, entry_html_path),
                "visualization_workbench_manifest": _relative_to_run(
                    layout.run_root, workbench_manifest_path
                ),
            }
        )

        _write_manifest(manifest, manifest_path, status="completed", artifact_index=artifact_index)
        _write_run_summary(
            layout.run_root / "run-summary.json",
            RunSummary(
                run_id=manifest.run_id,
                status="completed",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ),
        )
        return VisualizationWorkbenchResult(
            status="completed",
            entry_html_path=entry_html_path,
            workbench_manifest_path=workbench_manifest_path,
            diagnostics=[],
        )
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, FileNotFoundError) and exc.filename == str(manifest_path):
            message = f"manifest.json not found at {manifest_path}"
        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="visualization_workbench",
                severity="error",
                message=message,
            )
        ]
        if manifest is not None:
            _write_manifest(manifest, manifest_path, status="failed", artifact_index=artifact_index)
        _write_run_summary(
            layout.run_root / "run-summary.json",
            RunSummary(
                run_id=manifest.run_id if manifest is not None else layout.run_root.name,
                status="failed",
                exit_code=1,
                manifest_path="manifest.json",
                diagnostics=diagnostics,
            ),
        )
        return VisualizationWorkbenchResult(status="failed", diagnostics=diagnostics)


def _write_manifest(
    manifest: RunManifest,
    manifest_path: Path,
    *,
    status: str,
    artifact_index: dict[str, str],
) -> None:
    manifest_path.write_text(
        json.dumps(
            manifest.model_copy(
                update={
                    "status": status,
                    "artifact_index": artifact_index,
                },
                deep=True,
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_run_summary(path: Path, summary: RunSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary.model_dump(mode="json"), indent=2), encoding="utf-8")


def _relative_path(from_dir: Path, to_path: Path) -> str:
    return str(Path(os.path.relpath(to_path, start=from_dir))).replace("\\", "/")


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
