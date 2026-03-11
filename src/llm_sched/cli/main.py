"""CLI entrypoint for llm_sched."""

import json
from pathlib import Path

import typer

from llm_sched.config.loader import (
    MalformedProfileError,
    ProfileValidationFailure,
    load_scenario_profile,
    load_target_profile,
)
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.pipeline import run_descriptor_generation as execute_descriptor_generation
from llm_sched.pipeline import run_decode_evaluation as execute_decode_evaluation
from llm_sched.pipeline import run_frontend_analysis as execute_frontend_analysis
from llm_sched.pipeline import run_dual_core_scheduling as execute_dual_core_scheduling
from llm_sched.pipeline import run_memory_planning as execute_memory_planning
from llm_sched.pipeline import run_performance_estimation as execute_performance_estimation
from llm_sched.pipeline import run_prefill_evaluation as execute_prefill_evaluation
from llm_sched.pipeline import run_single_core_scheduling as execute_single_core_scheduling
from llm_sched.pipeline import run_sweep_analysis as execute_sweep_analysis
from llm_sched.pipeline import run_tile_planning as execute_tile_planning
from llm_sched.pipeline import run_visualization_catalog as execute_visualization_catalog
from llm_sched.pipeline import run_visualization_packaging as execute_visualization_packaging
from llm_sched.pipeline import run_visualization_workbench as execute_visualization_workbench

app = typer.Typer(
    add_completion=False,
    help="CLI for the RISC-V + NPU evaluation compiler foundation.",
)

EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1


@app.command("validate-profile")
def validate_profile(
    target_profile: Path | None = typer.Option(
        default=None, exists=False, dir_okay=False, readable=True
    ),
    scenario_profile: Path | None = typer.Option(
        default=None, exists=False, dir_okay=False, readable=True
    ),
) -> None:
    """Validate target and/or scenario profiles."""
    if target_profile is None and scenario_profile is None:
        typer.echo("At least one of --target-profile or --scenario-profile is required.")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    failed = False
    if target_profile is not None:
        failed |= not _validate_target_profile(target_profile)
    if scenario_profile is not None:
        failed |= not _validate_scenario_profile(scenario_profile)

    raise typer.Exit(code=EXIT_VALIDATION_ERROR if failed else EXIT_OK)


@app.command("init-run")
def init_run(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
    model_path: Path = typer.Option(..., exists=True, dir_okay=False),
    target_profile: Path = typer.Option(..., exists=True, dir_okay=False),
    scenario_profile: Path = typer.Option(..., exists=True, dir_okay=False),
) -> None:
    """Create a run directory and seed it with a manifest."""
    if not _validate_target_profile(target_profile):
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)
    if not _validate_scenario_profile(scenario_profile):
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    layout = build_run_layout(run_root)
    for directory in (
        layout.run_root,
        layout.artifacts_dir,
        layout.reports_dir,
        layout.logs_dir,
        layout.dumps_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_root.name,
        contract_version="phase-a.v1",
        status="initialized",
        model_path=str(model_path.resolve()),
        target_profile_path=str(target_profile.resolve()),
        scenario_profile_path=str(scenario_profile.resolve()),
        artifact_index={
            "manifest": "manifest.json",
            "artifacts_dir": "artifacts",
            "reports_dir": "reports",
            "logs_dir": "logs",
            "dumps_dir": "dumps",
        },
    )
    manifest_path = run_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    summary = RunSummary(
        run_id=run_root.name,
        status="initialized",
        exit_code=EXIT_OK,
        manifest_path="manifest.json",
        diagnostics=[],
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    typer.echo(f"Run initialized at {run_root}")


@app.command("run-frontend-analysis")
def run_frontend_analysis(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute the frontend import/canonicalize/lower/analyze flow and emit run artifacts."""
    result = execute_frontend_analysis(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "frontend analysis failed"
        typer.echo(f"Frontend analysis: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Frontend analysis completed at {run_root}")
    typer.echo("Artifacts updated under dumps/ and reports/, including bound-NIG and Phase B reports.")


@app.command("run-memory-planning")
def run_memory_planning(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-08 static VMEM / KV planning for a run with bound-NIG artifacts."""
    result = execute_memory_planning(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "memory planning failed"
        typer.echo(f"Memory planning: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Memory planning completed at {run_root}")
    typer.echo("Artifacts updated under artifacts/, including memory_plan.json.")


@app.command("run-tile-planning")
def run_tile_planning(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-09 tile candidate planning for a run with memory-plan artifacts."""
    result = execute_tile_planning(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "tile planning failed"
        typer.echo(f"Tile planning: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Tile planning completed at {run_root}")
    typer.echo("Artifacts updated under artifacts/, including tiling_plan.json.")


@app.command("run-single-core-scheduling")
def run_single_core_scheduling(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-10 deterministic single-core scheduling for a run with tiling artifacts."""
    result = execute_single_core_scheduling(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "single-core scheduling failed"
        typer.echo(f"Single-core scheduling: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Single-core scheduling completed at {run_root}")
    typer.echo("Artifacts updated under artifacts/, including schedule_ir.json.")


@app.command("run-dual-core-scheduling")
def run_dual_core_scheduling(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-11 deterministic dual-core scheduling for a run with tiling artifacts."""
    result = execute_dual_core_scheduling(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "dual-core scheduling failed"
        typer.echo(f"Dual-core scheduling: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Dual-core scheduling completed at {run_root}")
    typer.echo("Artifacts updated under artifacts/, including dual_core_schedule_ir.json.")


@app.command("run-descriptor-generation")
def run_descriptor_generation(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-12 descriptor generation and ISA coverage mapping for a scheduled run."""
    result = execute_descriptor_generation(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "descriptor generation failed"
        typer.echo(f"Descriptor generation: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Descriptor generation completed at {run_root}")
    typer.echo(
        "Artifacts updated under artifacts/ and reports/, including descriptor_ir.json, packed_descriptor_bundle.json, and isa_coverage_report.json."
    )


@app.command("run-performance-estimation")
def run_performance_estimation(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-13 descriptor-driven performance estimation for a scheduled run."""
    result = execute_performance_estimation(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "performance estimation failed"
        typer.echo(f"Performance estimation: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Performance estimation completed at {run_root}")
    typer.echo(
        "Artifacts updated under artifacts/ and reports/, including perf_analysis_ir.json and perf_summary_report.json."
    )


@app.command("run-prefill-evaluation")
def run_prefill_evaluation(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-14 prefill top-level evaluation for a run with performance artifacts."""
    result = execute_prefill_evaluation(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "prefill evaluation failed"
        typer.echo(f"Prefill evaluation: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Prefill evaluation completed at {run_root}")
    typer.echo("Artifacts updated under reports/, including prefill_evaluation_report.json.")


@app.command("run-decode-evaluation")
def run_decode_evaluation(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-15 decode top-level evaluation for a run with performance artifacts."""
    result = execute_decode_evaluation(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "decode evaluation failed"
        typer.echo(f"Decode evaluation: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Decode evaluation completed at {run_root}")
    typer.echo("Artifacts updated under reports/, including decode_evaluation_report.json.")


@app.command("run-sweep-analysis")
def run_sweep_analysis(
    sweep_spec: Path = typer.Option(..., exists=True, dir_okay=False, readable=True),
    sweep_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-16 sweep reruns and emit a delta report across target-profile variants."""
    result = execute_sweep_analysis(sweep_spec, sweep_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "sweep analysis failed"
        typer.echo(f"Sweep analysis: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Sweep analysis completed at {sweep_root}")
    typer.echo("Artifacts updated under runs/ and reports/, including sweep_delta_report.json.")


@app.command("run-visualization-packaging")
def run_visualization_packaging(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
    sweep_root: Path | None = typer.Option(default=None, dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-18 visualization bundle packaging for one run, with optional sweep context."""
    result = execute_visualization_packaging(run_root, sweep_root=sweep_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "visualization packaging failed"
        typer.echo(f"Visualization packaging: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Visualization packaging completed at {run_root}")
    typer.echo("Artifacts updated under reports/, including visualization_bundle.json.")


@app.command("run-visualization-workbench")
def run_visualization_workbench(
    run_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-19 static workbench packaging for one run with a visualization bundle."""
    result = execute_visualization_workbench(run_root)
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "visualization workbench failed"
        typer.echo(f"Visualization workbench: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Visualization workbench completed at {run_root}")
    typer.echo("Artifacts updated under workbench/, including index.html and workbench_manifest.json.")


@app.command("run-visualization-catalog")
def run_visualization_catalog(
    catalog_root: Path = typer.Option(..., dir_okay=True, file_okay=False),
    run_root: list[Path] = typer.Option([], dir_okay=True, file_okay=False),
    sweep_root: Path | None = typer.Option(default=None, dir_okay=True, file_okay=False),
    workspace_root: Path | None = typer.Option(default=None, dir_okay=True, file_okay=False),
) -> None:
    """Execute SPEC-19 static cross-run catalog packaging for explicit run roots."""
    result = execute_visualization_catalog(
        catalog_root,
        run_root,
        sweep_root=sweep_root,
        workspace_root=workspace_root,
    )
    if result.status != "completed":
        message = result.diagnostics[0].message if result.diagnostics else "visualization catalog failed"
        typer.echo(f"Visualization catalog: ERROR ({message})")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    typer.echo(f"Visualization catalog completed at {catalog_root}")
    typer.echo("Artifacts updated under catalog/, including index.html and catalog_manifest.json.")


def run() -> None:
    """Run the CLI application."""
    app()

def _validate_target_profile(path: Path) -> bool:
    try:
        load_target_profile(path)
    except FileNotFoundError:
        typer.echo(f"Target profile: ERROR ({path} not found)")
        return False
    except (MalformedProfileError, ProfileValidationFailure) as exc:
        typer.echo(f"Target profile: ERROR ({exc.diagnostics[0].message})")
        return False

    typer.echo("Target profile: OK")
    return True


def _validate_scenario_profile(path: Path) -> bool:
    try:
        load_scenario_profile(path)
    except FileNotFoundError:
        typer.echo(f"Scenario profile: ERROR ({path} not found)")
        return False
    except (MalformedProfileError, ProfileValidationFailure) as exc:
        typer.echo(f"Scenario profile: ERROR ({exc.diagnostics[0].message})")
        return False

    typer.echo("Scenario profile: OK")
    return True


if __name__ == "__main__":
    run()
