import json
import os
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(cwd / "src")
        if not existing_pythonpath
        else os.pathsep.join([str(cwd / "src"), existing_pythonpath])
    )
    return subprocess.run(
        [sys.executable, "-m", "llm_sched.cli.main", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_validate_profile_accepts_checked_in_profiles() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    result = run_cli(
        "validate-profile",
        "--target-profile",
        "profiles/targets/riscv_npu_single_core_v1.json",
        "--scenario-profile",
        "profiles/scenarios/prefill_seq128.json",
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Target profile: OK" in result.stdout
    assert "Scenario profile: OK" in result.stdout


def test_validate_profile_returns_non_zero_for_invalid_profile(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    broken_profile = tmp_path / "broken_target.json"
    broken_profile.write_text(json.dumps({"profile_name": "broken"}), encoding="utf-8")

    result = run_cli(
        "validate-profile",
        "--target-profile",
        str(broken_profile),
        cwd=repo_root,
    )

    assert result.returncode != 0
    assert "Target profile: ERROR" in result.stdout
