"""DIAG-09 diagnosis bundle builder."""

from __future__ import annotations

from pathlib import Path

from llm_sched.contracts.diagnosis_bundle import (
    DiagnosisBundle,
    DiagnosisBundleMetadata,
    DiagnosisComparePayload,
)

_BASE_PANELS = [
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
]


def build_diagnosis_bundle(
    *,
    run_id: str,
    graph_id: str,
    scenario_name: str,
    report_kind: str,
    schedule_kind: str,
    run_root: Path,
    diagnosis_reports_dir: Path,
    report_references: dict[str, str],
    compare_payloads: list[dict[str, str]],
) -> DiagnosisBundle:
    compare_entries = [
        payload
        if isinstance(payload, DiagnosisComparePayload)
        else DiagnosisComparePayload.model_validate(payload)
        for payload in compare_payloads
    ]
    available_panels = list(_BASE_PANELS)
    if compare_entries:
        available_panels.append("compare")
    return DiagnosisBundle(
        bundle_id=f"diag-bundle-{run_id}",
        metadata=DiagnosisBundleMetadata(
            run_id=run_id,
            graph_id=graph_id,
            scenario_name=scenario_name,
            report_kind=report_kind,
            schedule_kind=schedule_kind,
            run_root=str(run_root).replace("\\", "/"),
            diagnosis_reports_dir=str(diagnosis_reports_dir).replace("\\", "/"),
        ),
        report_references=report_references,
        available_panels=available_panels,
        compare_payloads=compare_entries,
    )
