"""CLI entrypoint for llm_sched."""

import typer

app = typer.Typer(add_completion=False, help="llmSched v2 — v0.10 descriptor compiler.")


def run() -> None:
    """Run the CLI application."""
    app()
