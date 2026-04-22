"""Verify that Phase 1 cleanup removed all v0.9-era modules and commands."""

from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "llm_sched"


def test_old_directories_removed() -> None:
    old_dirs = [
        "analysis",
        "visualization",
        "tools",
        "cli",
        "config",
        "arch",
        "contracts",
        "pipeline",
        "planning",
    ]
    for name in old_dirs:
        assert not (SRC / name).exists(), f"Old directory should be removed: {name}"


def test_new_flat_files_exist() -> None:
    new_files = ["cli.py", "config.py", "arch.py", "models.py"]
    for name in new_files:
        assert (SRC / name).exists(), f"New flat file should exist: {name}"


def test_new_packages_exist() -> None:
    new_packages = ["scheduler", "descriptor", "ir", "frontend"]
    for name in new_packages:
        assert (SRC / name).is_dir(), f"New package should exist: {name}"


def test_old_cli_commands_absent() -> None:
    from llm_sched.cli import app

    old_commands = {
        "validate-profile",
        "init-run",
        "run-frontend-analysis",
        "run-memory-planning",
        "run-memory-planner-closure",
        "run-tile-planning",
        "run-single-core-scheduling",
        "run-dual-core-scheduling",
        "run-descriptor-generation",
        "run-performance-estimation",
        "run-prefill-evaluation",
        "run-decode-evaluation",
        "run-diagnosis-analysis",
        "run-diagnosis-packaging",
        "run-diagnosis-workbench",
        "run-sweep-analysis",
        "run-phase-d-compare",
        "run-visualization-packaging",
        "run-visualization-workbench",
        "run-visualization-catalog",
        "run-phase-c-acceptance",
        "run-phase-c-gate",
    }
    registered = {cmd.name for cmd in app.registered_commands}
    assert old_commands.isdisjoint(registered), (
        f"Old CLI commands still registered: {old_commands & registered}"
    )


def test_compile_command_present() -> None:
    from llm_sched.cli import app

    registered = {cmd.name for cmd in app.registered_commands}
    assert "compile" in registered, "compile command should be present"
