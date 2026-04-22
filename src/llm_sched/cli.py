"""CLI entrypoint for llm_sched."""

from pathlib import Path

import typer

app = typer.Typer(
    add_completion=False,
    help="llmSched v2 — v0.10 descriptor compiler.",
)

EXIT_OK = 0
EXIT_VALIDATION_ERROR = 1


@app.command("compile")
def compile_command(
    model: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to ONNX model file."),
    config: Path = typer.Option(..., exists=True, dir_okay=False, readable=True, help="Path to config YAML file."),
    output: Path = typer.Option(..., dir_okay=True, file_okay=False, help="Output directory for descriptors and metrics."),
) -> None:
    """Compile an ONNX model into a v0.10 descriptor set."""
    if not model.suffix.lower() == ".onnx":
        typer.echo(f"ERROR: model must be an .onnx file, got {model}")
        raise typer.Exit(code=EXIT_VALIDATION_ERROR)

    output.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Compile stub: model={model}, config={config}, output={output}")
    typer.echo("Full compilation pipeline will be wired in Phase 2.")


def run() -> None:
    """Run the CLI application."""
    app()
