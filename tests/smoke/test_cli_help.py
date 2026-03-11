import os
import subprocess
import sys
from pathlib import Path


def test_cli_help_lists_phase_a_commands() -> None:
    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[2]
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(repo_root / "src")
        if not existing_pythonpath
        else os.pathsep.join([str(repo_root / "src"), existing_pythonpath])
    )

    result = subprocess.run(
        [sys.executable, "-m", "llm_sched.cli.main", "--help"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "validate-profile" in result.stdout
    assert "init-run" in result.stdout
    assert "run-frontend-analysis" in result.stdout
    assert "run-phase-c-gate" in result.stdout
