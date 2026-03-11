"""Run-root workflow for SPEC-12 descriptor generation and ISA coverage mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.config.loader import Diagnostic, load_scenario_profile, load_target_profile
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.packed_descriptor_bundle import PackedDescriptorBundle
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.ir.descriptor_ir import DescriptorIR
from llm_sched.ir.io import dump_ir_document, load_ir_document
from llm_sched.ir.nig import NIGIR
from llm_sched.ir.schedule_ir import ScheduleIR
from llm_sched.planning import build_descriptor_artifacts, pack_descriptor_bundle


class DescriptorGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    descriptor_ir_path: Path | None = None
    packed_descriptor_bundle_path: Path | None = None
    coverage_report_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_descriptor_generation(run_root: str | Path) -> DescriptorGenerationResult:
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

        bound_nig_path = layout.run_root / Path(artifact_index.get("bound_nig_ir", "dumps/bound_nig_ir.json"))
        memory_plan_path = layout.run_root / Path(artifact_index.get("memory_plan", "artifacts/memory_plan.json"))
        schedule_path = _resolve_schedule_path(layout.run_root, artifact_index)
        if not bound_nig_path.is_file():
            raise FileNotFoundError(f"bound_nig_ir not found at {bound_nig_path}")
        if not memory_plan_path.is_file():
            raise FileNotFoundError(f"memory_plan not found at {memory_plan_path}")
        if not schedule_path.is_file():
            raise FileNotFoundError(f"schedule artifact not found at {schedule_path}")

        bound_nig_ir = load_ir_document(bound_nig_path, NIGIR)
        memory_plan = load_ir_document(memory_plan_path, MemoryPlanArtifact)
        schedule_ir = load_ir_document(schedule_path, ScheduleIR)
        descriptor_ir, coverage_report = build_descriptor_artifacts(
            schedule_ir,
            bound_nig_ir,
            memory_plan,
            target_profile,
            scenario_profile,
        )
        packed_descriptor_bundle = pack_descriptor_bundle(descriptor_ir, target_profile)

        descriptor_ir_output_path = layout.artifacts_dir / "descriptor_ir.json"
        packed_descriptor_bundle_output_path = layout.artifacts_dir / "packed_descriptor_bundle.json"
        coverage_report_output_path = layout.reports_dir / "isa_coverage_report.json"
        dump_ir_document(descriptor_ir, descriptor_ir_output_path)
        _write_json_report(packed_descriptor_bundle_output_path, packed_descriptor_bundle)
        _write_json_report(coverage_report_output_path, coverage_report)

        artifact_index["descriptor_ir"] = _relative_to_run(layout.run_root, descriptor_ir_output_path)
        artifact_index["packed_descriptor_bundle"] = _relative_to_run(
            layout.run_root,
            packed_descriptor_bundle_output_path,
        )
        artifact_index["isa_coverage_report"] = _relative_to_run(layout.run_root, coverage_report_output_path)
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
        return DescriptorGenerationResult(
            status="completed",
            descriptor_ir_path=descriptor_ir_output_path,
            packed_descriptor_bundle_path=packed_descriptor_bundle_output_path,
            coverage_report_path=coverage_report_output_path,
            diagnostics=[],
        )
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="descriptor_generation",
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
        return DescriptorGenerationResult(status="failed", diagnostics=diagnostics)


def _resolve_schedule_path(run_root: Path, artifact_index: dict[str, str]) -> Path:
    for key, fallback in (
        ("dual_core_schedule_ir", "artifacts/dual_core_schedule_ir.json"),
        ("schedule_ir", "artifacts/schedule_ir.json"),
    ):
        path = run_root / Path(artifact_index.get(key, fallback))
        if path.is_file():
            return path
    return run_root / Path(artifact_index.get("schedule_ir", "artifacts/schedule_ir.json"))


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


def _write_json_report(path: Path, report: ISACoverageReport | PackedDescriptorBundle) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
