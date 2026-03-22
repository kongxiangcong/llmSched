"""Repo-local end-to-end runner that orchestrates the full CLI pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib.util import find_spec
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


CoreMode = Literal["single-core", "dual-core"]
EvalMode = Literal["prefill", "decode"]

_TARGET_PROFILE_BY_CORE_MODE: dict[CoreMode, str] = {
    "single-core": "profiles/targets/riscv_npu_single_core_v1.json",
    "dual-core": "profiles/targets/riscv_npu_dual_core_v1.json",
}

_SCENARIO_PROFILE_BY_EVAL_MODE: dict[EvalMode, str] = {
    "prefill": "profiles/scenarios/prefill_seq128.json",
    "decode": "profiles/scenarios/decode_token1_kv2048.json",
}


@dataclass(frozen=True)
class RunCase:
    run_id: str
    run_root: Path
    eval_mode: EvalMode
    schedule_kind: CoreMode
    target_profile_path: Path
    scenario_profile_path: Path


@dataclass(frozen=True)
class SweepSpecConfig:
    sweep_name: str
    sweep_root: Path
    baseline_target_profile_path: Path
    target_profile_paths: tuple[Path, ...]
    scenario_profile_paths: tuple[Path, ...]


@dataclass(frozen=True)
class EndToEndPlan:
    repo_root: Path
    session_root: Path
    model_path: Path
    run_cases: list[RunCase]
    sweep_specs: list[SweepSpecConfig]
    catalog_root: Path


@dataclass(frozen=True)
class CommandResult:
    label: str
    command: tuple[str, ...]
    returncode: int
    stdout_log_path: Path
    stderr_log_path: Path


@dataclass(frozen=True)
class RunExecutionResult:
    run_case: RunCase
    status: Literal["completed", "failed"]
    command_results: list[CommandResult]
    failed_command_label: str | None = None


@dataclass(frozen=True)
class SweepExecutionResult:
    sweep_spec: SweepSpecConfig
    status: Literal["completed", "failed", "skipped"]
    command_results: list[CommandResult]
    reason: str | None = None


@dataclass(frozen=True)
class CatalogExecutionResult:
    status: Literal["completed", "failed", "skipped"]
    command_results: list[CommandResult]
    reason: str | None = None


@dataclass(frozen=True)
class EndToEndSessionResult:
    plan: EndToEndPlan
    run_results: list[RunExecutionResult]
    sweep_results: list[SweepExecutionResult]
    catalog_result: CatalogExecutionResult
    summary_path: Path


def resolve_selected_core_modes(selection: str) -> tuple[CoreMode, ...]:
    normalized = selection.strip().lower()
    if normalized in {"single", "single-core"}:
        return ("single-core",)
    if normalized in {"dual", "dual-core"}:
        return ("dual-core",)
    if normalized in {"both", "all"}:
        return ("single-core", "dual-core")
    raise ValueError(f"unsupported core mode: {selection}")


def resolve_selected_eval_modes(selection: str) -> tuple[EvalMode, ...]:
    normalized = selection.strip().lower()
    if normalized == "prefill":
        return ("prefill",)
    if normalized == "decode":
        return ("decode",)
    if normalized in {"both", "all", "prefill+decode", "decode+prefill"}:
        return ("prefill", "decode")
    raise ValueError(f"unsupported eval mode: {selection}")


def build_session_root(repo_root: Path, output_root: Path, run_name: str | None = None) -> Path:
    root = output_root if output_root.is_absolute() else repo_root / output_root
    if run_name:
        return root / run_name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return root / f"e2e-{timestamp}"


def build_end_to_end_plan(
    *,
    repo_root: Path,
    session_root: Path,
    model_path: Path,
    core_mode: str,
    eval_mode: str,
) -> EndToEndPlan:
    selected_core_modes = resolve_selected_core_modes(core_mode)
    selected_eval_modes = resolve_selected_eval_modes(eval_mode)

    run_cases: list[RunCase] = []
    for selected_eval_mode in selected_eval_modes:
        for selected_core_mode in selected_core_modes:
            run_id = f"{selected_eval_mode}-{selected_core_mode}"
            run_cases.append(
                RunCase(
                    run_id=run_id,
                    run_root=session_root / "runs" / run_id,
                    eval_mode=selected_eval_mode,
                    schedule_kind=selected_core_mode,
                    target_profile_path=repo_root / _TARGET_PROFILE_BY_CORE_MODE[selected_core_mode],
                    scenario_profile_path=repo_root / _SCENARIO_PROFILE_BY_EVAL_MODE[selected_eval_mode],
                )
            )

    sweep_specs: list[SweepSpecConfig] = []
    if len(selected_core_modes) == 2:
        for selected_eval_mode in selected_eval_modes:
            sweep_specs.append(
                SweepSpecConfig(
                    sweep_name=f"{selected_eval_mode}-single-vs-dual",
                    sweep_root=session_root / "sweeps" / f"{selected_eval_mode}-single-vs-dual",
                    baseline_target_profile_path=repo_root / _TARGET_PROFILE_BY_CORE_MODE["single-core"],
                    target_profile_paths=(
                        repo_root / _TARGET_PROFILE_BY_CORE_MODE["single-core"],
                        repo_root / _TARGET_PROFILE_BY_CORE_MODE["dual-core"],
                    ),
                    scenario_profile_paths=(
                        repo_root / _SCENARIO_PROFILE_BY_EVAL_MODE[selected_eval_mode],
                    ),
                )
            )

    return EndToEndPlan(
        repo_root=repo_root,
        session_root=session_root,
        model_path=model_path,
        run_cases=run_cases,
        sweep_specs=sweep_specs,
        catalog_root=session_root / "catalog-root",
    )


def find_missing_python_modules(*, required_modules: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(module_name for module_name in required_modules if find_spec(module_name) is None)


def run_end_to_end_session(plan: EndToEndPlan) -> EndToEndSessionResult:
    plan.session_root.mkdir(parents=True, exist_ok=True)

    run_results = [_execute_run_case(plan.repo_root, plan.model_path, run_case) for run_case in plan.run_cases]
    successful_eval_modes = {
        result.run_case.eval_mode
        for result in run_results
        if result.status == "completed"
    }

    sweep_results: list[SweepExecutionResult] = []
    for sweep_spec in plan.sweep_specs:
        if _eval_mode_for_sweep(sweep_spec) not in successful_eval_modes:
            sweep_results.append(
                SweepExecutionResult(
                    sweep_spec=sweep_spec,
                    status="skipped",
                    command_results=[],
                    reason="matching run cases did not complete successfully",
                )
            )
            continue
        sweep_results.append(_execute_sweep(plan.repo_root, plan.model_path, sweep_spec))

    sweep_root_by_eval_mode = {
        _eval_mode_for_sweep(result.sweep_spec): result.sweep_spec.sweep_root
        for result in sweep_results
        if result.status == "completed"
    }

    successful_run_roots: list[Path] = []
    updated_run_results: list[RunExecutionResult] = []
    for result in run_results:
        if result.status != "completed":
            updated_run_results.append(result)
            continue
        sweep_root = sweep_root_by_eval_mode.get(result.run_case.eval_mode)
        packaging_result = _execute_visualization(plan.repo_root, result.run_case.run_root, sweep_root=sweep_root)
        merged_results = [*result.command_results, *packaging_result.command_results]
        updated_run_results.append(
            RunExecutionResult(
                run_case=result.run_case,
                status=packaging_result.status,
                command_results=merged_results,
                failed_command_label=packaging_result.failed_command_label,
            )
        )
        if packaging_result.status == "completed":
            successful_run_roots.append(result.run_case.run_root)

    catalog_result = _execute_catalog(plan.repo_root, plan.catalog_root, successful_run_roots)
    summary_path = _write_session_summary(
        plan,
        updated_run_results,
        sweep_results,
        catalog_result,
    )
    return EndToEndSessionResult(
        plan=plan,
        run_results=updated_run_results,
        sweep_results=sweep_results,
        catalog_result=catalog_result,
        summary_path=summary_path,
    )


def _execute_run_case(repo_root: Path, model_path: Path, run_case: RunCase) -> RunExecutionResult:
    commands = [
        (
            "init-run",
            (
                "init-run",
                "--run-root",
                str(run_case.run_root),
                "--model-path",
                str(model_path),
                "--target-profile",
                str(run_case.target_profile_path),
                "--scenario-profile",
                str(run_case.scenario_profile_path),
            ),
        ),
        ("frontend-analysis", ("run-frontend-analysis", "--run-root", str(run_case.run_root))),
        ("memory-planning", ("run-memory-planning", "--run-root", str(run_case.run_root))),
        ("tile-planning", ("run-tile-planning", "--run-root", str(run_case.run_root))),
        (
            "scheduling",
            (
                "run-single-core-scheduling"
                if run_case.schedule_kind == "single-core"
                else "run-dual-core-scheduling",
                "--run-root",
                str(run_case.run_root),
            ),
        ),
        ("descriptor-generation", ("run-descriptor-generation", "--run-root", str(run_case.run_root))),
        ("performance-estimation", ("run-performance-estimation", "--run-root", str(run_case.run_root))),
        (
            "evaluation",
            (
                "run-prefill-evaluation" if run_case.eval_mode == "prefill" else "run-decode-evaluation",
                "--run-root",
                str(run_case.run_root),
            ),
        ),
    ]

    command_results: list[CommandResult] = []
    for label, command in commands:
        result = _run_cli(repo_root, command, log_root=run_case.run_root / "logs", label=label)
        command_results.append(result)
        if result.returncode != 0:
            return RunExecutionResult(
                run_case=run_case,
                status="failed",
                command_results=command_results,
                failed_command_label=label,
            )

    return RunExecutionResult(
        run_case=run_case,
        status="completed",
        command_results=command_results,
    )


@dataclass(frozen=True)
class _VisualizationResult:
    status: Literal["completed", "failed"]
    command_results: list[CommandResult]
    failed_command_label: str | None = None


def _execute_visualization(
    repo_root: Path,
    run_root: Path,
    *,
    sweep_root: Path | None,
) -> _VisualizationResult:
    packaging_command: tuple[str, ...]
    if sweep_root is None:
        packaging_command = ("run-visualization-packaging", "--run-root", str(run_root))
    else:
        packaging_command = (
            "run-visualization-packaging",
            "--run-root",
            str(run_root),
            "--sweep-root",
            str(sweep_root),
        )
    commands = [
        ("visualization-packaging", packaging_command),
        ("visualization-workbench", ("run-visualization-workbench", "--run-root", str(run_root))),
    ]
    command_results: list[CommandResult] = []
    for label, command in commands:
        result = _run_cli(repo_root, command, log_root=run_root / "logs", label=label)
        command_results.append(result)
        if result.returncode != 0:
            return _VisualizationResult(
                status="failed",
                command_results=command_results,
                failed_command_label=label,
            )
    return _VisualizationResult(status="completed", command_results=command_results)


def _execute_sweep(repo_root: Path, model_path: Path, sweep_spec: SweepSpecConfig) -> SweepExecutionResult:
    sweep_spec.sweep_root.mkdir(parents=True, exist_ok=True)
    spec_path = sweep_spec.sweep_root / "sweep-spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "sweep_name": sweep_spec.sweep_name,
                "model_path": str(model_path.resolve()),
                "baseline_target_profile": str(sweep_spec.baseline_target_profile_path.resolve()),
                "target_profiles": [str(path.resolve()) for path in sweep_spec.target_profile_paths],
                "scenario_profiles": [str(path.resolve()) for path in sweep_spec.scenario_profile_paths],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    commands = [
        (
            "sweep-analysis",
            (
                "run-sweep-analysis",
                "--sweep-spec",
                str(spec_path),
                "--sweep-root",
                str(sweep_spec.sweep_root),
            ),
        ),
        (
            "phase-d-compare",
            ("run-phase-d-compare", "--sweep-root", str(sweep_spec.sweep_root)),
        ),
    ]
    command_results: list[CommandResult] = []
    for label, command in commands:
        result = _run_cli(repo_root, command, log_root=sweep_spec.sweep_root / "logs", label=label)
        command_results.append(result)
        if result.returncode != 0:
            return SweepExecutionResult(
                sweep_spec=sweep_spec,
                status="failed",
                command_results=command_results,
                reason=f"{label} failed",
            )
    return SweepExecutionResult(
        sweep_spec=sweep_spec,
        status="completed",
        command_results=command_results,
    )


def _execute_catalog(repo_root: Path, catalog_root: Path, run_roots: list[Path]) -> CatalogExecutionResult:
    if not run_roots:
        return CatalogExecutionResult(
            status="skipped",
            command_results=[],
            reason="no successful runs available for catalog packaging",
        )
    command: list[str] = ["run-visualization-catalog", "--catalog-root", str(catalog_root)]
    for run_root in run_roots:
        command.extend(["--run-root", str(run_root)])
    result = _run_cli(repo_root, tuple(command), log_root=catalog_root / "logs", label="visualization-catalog")
    status: Literal["completed", "failed"] = "completed" if result.returncode == 0 else "failed"
    return CatalogExecutionResult(status=status, command_results=[result], reason=None if status == "completed" else "visualization catalog failed")


def _run_cli(repo_root: Path, command: tuple[str, ...], *, log_root: Path, label: str) -> CommandResult:
    log_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    src_path = str((repo_root / "src").resolve())
    env["PYTHONPATH"] = src_path if not existing_pythonpath else os.pathsep.join([src_path, existing_pythonpath])
    completed = subprocess.run(
        [sys.executable, "-m", "llm_sched.cli.main", *command],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout_log_path = log_root / f"{label}.stdout.log"
    stderr_log_path = log_root / f"{label}.stderr.log"
    stdout_log_path.write_text(completed.stdout, encoding="utf-8")
    stderr_log_path.write_text(completed.stderr, encoding="utf-8")
    return CommandResult(
        label=label,
        command=command,
        returncode=completed.returncode,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
    )


def _eval_mode_for_sweep(sweep_spec: SweepSpecConfig) -> EvalMode:
    return "prefill" if sweep_spec.sweep_name.startswith("prefill-") else "decode"


def _write_session_summary(
    plan: EndToEndPlan,
    run_results: list[RunExecutionResult],
    sweep_results: list[SweepExecutionResult],
    catalog_result: CatalogExecutionResult,
) -> Path:
    summary_path = plan.session_root / "session-summary.json"
    payload = {
        "session_root": str(plan.session_root),
        "model_path": str(plan.model_path),
        "catalog_root": str(plan.catalog_root),
        "run_cases": [
            {
                **asdict(result.run_case),
                "run_root": str(result.run_case.run_root),
                "target_profile_path": str(result.run_case.target_profile_path),
                "scenario_profile_path": str(result.run_case.scenario_profile_path),
                "status": result.status,
                "failed_command_label": result.failed_command_label,
                "commands": [
                    {
                        "label": command_result.label,
                        "command": list(command_result.command),
                        "returncode": command_result.returncode,
                        "stdout_log_path": str(command_result.stdout_log_path),
                        "stderr_log_path": str(command_result.stderr_log_path),
                    }
                    for command_result in result.command_results
                ],
            }
            for result in run_results
        ],
        "sweeps": [
            {
                "sweep_name": result.sweep_spec.sweep_name,
                "sweep_root": str(result.sweep_spec.sweep_root),
                "baseline_target_profile_path": str(result.sweep_spec.baseline_target_profile_path),
                "target_profile_paths": [str(path) for path in result.sweep_spec.target_profile_paths],
                "scenario_profile_paths": [str(path) for path in result.sweep_spec.scenario_profile_paths],
                "status": result.status,
                "reason": result.reason,
                "commands": [
                    {
                        "label": command_result.label,
                        "command": list(command_result.command),
                        "returncode": command_result.returncode,
                        "stdout_log_path": str(command_result.stdout_log_path),
                        "stderr_log_path": str(command_result.stderr_log_path),
                    }
                    for command_result in result.command_results
                ],
            }
            for result in sweep_results
        ],
        "catalog": {
            "status": catalog_result.status,
            "reason": catalog_result.reason,
            "commands": [
                {
                    "label": command_result.label,
                    "command": list(command_result.command),
                    "returncode": command_result.returncode,
                    "stdout_log_path": str(command_result.stdout_log_path),
                    "stderr_log_path": str(command_result.stderr_log_path),
                }
                for command_result in catalog_result.command_results
            ],
        },
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary_path
