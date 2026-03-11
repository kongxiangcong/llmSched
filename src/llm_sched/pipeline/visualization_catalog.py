"""Static cross-run catalog packaging for SPEC-19."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.config.loader import Diagnostic
from llm_sched.contracts.sweep_report import SweepDeltaReport
from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.contracts.visualization_catalog import VisualizationCatalogEntry
from llm_sched.contracts.visualization_workbench import VisualizationWorkbenchArtifact
from llm_sched.visualization import build_visualization_catalog


class VisualizationCatalogResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    entry_html_path: Path | None = None
    catalog_manifest_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_visualization_catalog(
    catalog_root: str | Path,
    run_roots: list[str | Path] | None = None,
    *,
    sweep_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> VisualizationCatalogResult:
    catalog_root_path = Path(catalog_root)
    try:
        resolved_run_roots = _resolve_run_roots(
            [Path(run_root) for run_root in (run_roots or [])],
            sweep_root=Path(sweep_root) if sweep_root is not None else None,
            workspace_root=Path(workspace_root) if workspace_root is not None else None,
        )
        if not resolved_run_roots:
            raise ValueError("no run roots resolved for visualization catalog")

        entries = [_build_catalog_entry(catalog_root_path, run_root) for run_root in resolved_run_roots]
        artifact, files = build_visualization_catalog(
            catalog_id=f"catalog.{catalog_root_path.name}",
            title="Visualization Catalog",
            entries=entries,
            catalog_root=Path("catalog"),
        )
        for relative_path, content in files.items():
            output_path = catalog_root_path / Path(relative_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

        return VisualizationCatalogResult(
            status="completed",
            entry_html_path=catalog_root_path / "catalog" / "index.html",
            catalog_manifest_path=catalog_root_path / "catalog" / "catalog_manifest.json",
            diagnostics=[],
        )
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(catalog_root_path),
                field="visualization_catalog",
                severity="error",
                message=str(exc),
            )
        ]
        return VisualizationCatalogResult(status="failed", diagnostics=diagnostics)


def _build_catalog_entry(catalog_root: Path, run_root: Path) -> VisualizationCatalogEntry:
    workbench_manifest_path = run_root / "workbench" / "workbench_manifest.json"
    bundle_path = run_root / "reports" / "visualization_bundle.json"
    if not workbench_manifest_path.is_file():
        raise FileNotFoundError(f"workbench_manifest not found at {workbench_manifest_path}")
    if not bundle_path.is_file():
        raise FileNotFoundError(f"visualization_bundle not found at {bundle_path}")

    workbench = VisualizationWorkbenchArtifact.model_validate_json(
        workbench_manifest_path.read_text(encoding="utf-8")
    )
    bundle = VisualizationBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
    primary_metric_name, primary_metric_value = _select_primary_metric(bundle)
    entry_html_path = run_root / Path(workbench.entry_html_path)
    relative_entry_path = str(
        Path(os.path.relpath(entry_html_path, start=catalog_root / "catalog"))
    ).replace("\\", "/")

    return VisualizationCatalogEntry(
        entry_id=f"{bundle.metadata.run_id}.{bundle.metadata.mode}.{bundle.metadata.schedule_kind}",
        run_id=bundle.metadata.run_id,
        scenario_name=bundle.metadata.scenario_name,
        mode=bundle.metadata.mode,
        schedule_kind=bundle.metadata.schedule_kind,
        target_profile_name=bundle.metadata.target_profile_name,
        primary_metric_name=primary_metric_name,
        primary_metric_value=primary_metric_value,
        metric_values=_collect_metric_values(bundle),
        workbench_entry_path=relative_entry_path,
    )


def _select_primary_metric(bundle: VisualizationBundle) -> tuple[str, float]:
    metrics = bundle.report_summary.primary_metrics
    if "estimated_cycles" in metrics:
        return ("estimated_cycles", float(metrics["estimated_cycles"]))
    if "token_latency_cycles" in metrics:
        return ("token_latency_cycles", float(metrics["token_latency_cycles"]))
    if not metrics:
        return ("unknown", 0.0)
    first_key = next(iter(metrics))
    return (first_key, float(metrics[first_key]))


def _collect_metric_values(bundle: VisualizationBundle) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in bundle.report_summary.primary_metrics.items()
    }


def _resolve_run_roots(
    explicit_run_roots: list[Path],
    *,
    sweep_root: Path | None,
    workspace_root: Path | None,
) -> list[Path]:
    discovered: list[Path] = []
    discovered.extend(explicit_run_roots)

    if sweep_root is not None:
        discovered.extend(_discover_run_roots_from_sweep_root(sweep_root))
    if workspace_root is not None:
        discovered.extend(_discover_run_roots_from_workspace_root(workspace_root))

    deduplicated: list[Path] = []
    seen: set[str] = set()
    for path in discovered:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        deduplicated.append(path)
    return deduplicated


def _discover_run_roots_from_sweep_root(sweep_root: Path) -> list[Path]:
    report_path = sweep_root / "reports" / "sweep_delta_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"sweep_delta_report not found at {report_path}")
    report = SweepDeltaReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    return [Path(record.run_root) for record in report.run_records if record.status == "completed"]


def _discover_run_roots_from_workspace_root(workspace_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for child in workspace_root.iterdir():
        if not child.is_dir():
            continue
        if (child / "workbench" / "workbench_manifest.json").is_file():
            candidates.append(child)
    runs_dir = workspace_root / "runs"
    if runs_dir.is_dir():
        for child in runs_dir.iterdir():
            if child.is_dir() and (child / "workbench" / "workbench_manifest.json").is_file():
                candidates.append(child)
    return candidates
