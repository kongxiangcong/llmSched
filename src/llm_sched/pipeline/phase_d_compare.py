"""Sweep-root workflow for standalone Phase D compare reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import build_phase_d_compare_report
from llm_sched.config.loader import Diagnostic
from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport
from llm_sched.contracts.sweep_report import SweepDeltaReport


class PhaseDCompareResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    report_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_phase_d_compare(sweep_root: str | Path) -> PhaseDCompareResult:
    sweep_root_path = Path(sweep_root)
    sweep_report_path = sweep_root_path / "reports" / "sweep_delta_report.json"
    try:
        if not sweep_report_path.is_file():
            raise FileNotFoundError(f"sweep_delta_report not found at {sweep_report_path}")

        sweep_report = SweepDeltaReport.model_validate_json(
            sweep_report_path.read_text(encoding="utf-8")
        )
        report = build_phase_d_compare_report(
            report_name=f"phase-d-compare.{sweep_root_path.name}",
            sweep_report=sweep_report,
        )
        report_path = sweep_root_path / "reports" / "phase_d_compare_report.json"
        _write_json_report(report_path, report)
        return PhaseDCompareResult(status="completed", report_path=report_path, diagnostics=[])
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(sweep_root_path),
                field="phase_d_compare",
                severity="error",
                message=str(exc),
            )
        ]
        return PhaseDCompareResult(status="failed", diagnostics=diagnostics)


def _write_json_report(path: Path, report: PhaseDCompareReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
