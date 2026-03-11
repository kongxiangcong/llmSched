"""Run-root workflow for SPEC-08 memory planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.config.loader import Diagnostic, load_scenario_profile, load_target_profile
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.ir.io import dump_ir_document, load_ir_document
from llm_sched.ir.nig import NIGIR
from llm_sched.planning import plan_memory_artifact


class MemoryPlanningResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    memory_plan_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_memory_planning(run_root: str | Path) -> MemoryPlanningResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)
        target_profile = load_target_profile(manifest.target_profile_path)
        scenario_profile = load_scenario_profile(manifest.scenario_profile_path)

        bound_nig_relative_path = artifact_index.get("bound_nig_ir", "dumps/bound_nig_ir.json")
        bound_nig_path = layout.run_root / Path(bound_nig_relative_path)
        if not bound_nig_path.is_file():
            raise FileNotFoundError(f"bound_nig_ir not found at {bound_nig_path}")

        bound_nig_ir = load_ir_document(bound_nig_path, NIGIR)
        memory_plan = plan_memory_artifact(bound_nig_ir, target_profile, scenario_profile)

        memory_plan_path = layout.artifacts_dir / "memory_plan.json"
        dump_ir_document(memory_plan, memory_plan_path)

        artifact_index["memory_plan"] = _relative_to_run(layout.run_root, memory_plan_path)
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
        return MemoryPlanningResult(
            status="completed",
            memory_plan_path=memory_plan_path,
            diagnostics=[],
        )
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="memory_planning",
                severity="error",
                message=str(exc),
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
        return MemoryPlanningResult(status="failed", diagnostics=diagnostics)


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


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
