import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from llm_sched.config.loader import load_scenario_profile, load_target_profile
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


SMOKE_STAGES = (
    "frontend",
    "memory",
    "tile",
    "schedule",
    "descriptor",
    "performance",
    "prefill_eval",
    "decode_eval",
    "visualization_bundle",
)


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


@pytest.fixture(scope="session")
def smoke_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def prepared_smoke_run_root_factory(
    tmp_path_factory: pytest.TempPathFactory,
    smoke_repo_root: Path,
):
    cache_root = tmp_path_factory.mktemp("prepared-smoke-run-roots", numbered=False)

    def factory(
        *,
        target_run_root: Path,
        target_relative_path: str,
        scenario_relative_path: str,
        final_stage: str,
    ) -> Path:
        cache_key = (
            Path(target_relative_path).stem,
            Path(scenario_relative_path).stem,
            final_stage,
        )
        prepared_root = cache_root / "__".join(cache_key)
        ready_flag = prepared_root / ".prepared"
        if not ready_flag.is_file():
            if prepared_root.exists():
                shutil.rmtree(prepared_root)
            _initialize_cli_run_root(
                prepared_root,
                smoke_repo_root,
                target_relative_path=target_relative_path,
                scenario_relative_path=scenario_relative_path,
            )
            _prepare_cli_run_root_to_stage(
                prepared_root,
                smoke_repo_root,
                target_relative_path=target_relative_path,
                scenario_relative_path=scenario_relative_path,
                final_stage=final_stage,
            )
            ready_flag.write_text("prepared", encoding="utf-8")

        _clone_prepared_run_root(prepared_root, target_run_root)
        _rewrite_run_identity(target_run_root, target_run_root.name)
        return target_run_root

    return factory


def _prepare_cli_run_root_to_stage(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    scenario_relative_path: str,
    final_stage: str,
) -> None:
    if final_stage not in SMOKE_STAGES:
        raise ValueError(f"unsupported final_stage: {final_stage}")

    target_profile = load_target_profile(repo_root / target_relative_path)
    scenario_profile = load_scenario_profile(repo_root / scenario_relative_path)

    for stage in SMOKE_STAGES:
        if stage == "frontend":
            result = run_cli("run-frontend-analysis", "--run-root", str(run_root), cwd=repo_root)
        elif stage == "memory":
            result = run_cli("run-memory-planning", "--run-root", str(run_root), cwd=repo_root)
        elif stage == "tile":
            result = run_cli("run-tile-planning", "--run-root", str(run_root), cwd=repo_root)
        elif stage == "schedule":
            scheduling_command = (
                "run-single-core-scheduling"
                if target_profile.core_mode == "single-core"
                else "run-dual-core-scheduling"
            )
            result = run_cli(scheduling_command, "--run-root", str(run_root), cwd=repo_root)
        elif stage == "descriptor":
            result = run_cli("run-descriptor-generation", "--run-root", str(run_root), cwd=repo_root)
        elif stage == "performance":
            result = run_cli("run-performance-estimation", "--run-root", str(run_root), cwd=repo_root)
        elif stage == "prefill_eval":
            if scenario_profile.mode != "prefill":
                if final_stage == "prefill_eval":
                    raise ValueError("prefill_eval requires a prefill scenario")
                continue
            result = run_cli("run-prefill-evaluation", "--run-root", str(run_root), cwd=repo_root)
        elif stage == "decode_eval":
            if scenario_profile.mode != "decode":
                if final_stage == "decode_eval":
                    raise ValueError("decode_eval requires a decode scenario")
                continue
            result = run_cli("run-decode-evaluation", "--run-root", str(run_root), cwd=repo_root)
        else:
            if scenario_profile.mode == "prefill":
                eval_command = "run-prefill-evaluation"
            else:
                eval_command = "run-decode-evaluation"
            result = run_cli(eval_command, "--run-root", str(run_root), cwd=repo_root)
            assert result.returncode == 0, result.stderr
            result = run_cli("run-visualization-packaging", "--run-root", str(run_root), cwd=repo_root)

        assert result.returncode == 0, result.stderr
        if stage == final_stage:
            return


def _initialize_cli_run_root(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    scenario_relative_path: str,
) -> None:
    result = run_cli(
        "init-run",
        "--run-root",
        str(run_root),
        "--model-path",
        "models/gemma3_1b/model_q4f16.onnx",
        "--target-profile",
        target_relative_path,
        "--scenario-profile",
        scenario_relative_path,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr


def _clone_prepared_run_root(prepared_root: Path, target_run_root: Path) -> None:
    if target_run_root.exists():
        shutil.rmtree(target_run_root)
    shutil.copytree(prepared_root, target_run_root)
    prepared_flag = target_run_root / ".prepared"
    if prepared_flag.exists():
        prepared_flag.unlink()


def _rewrite_run_identity(run_root: Path, run_id: str) -> None:
    manifest_path = run_root / "manifest.json"
    run_summary_path = run_root / "run-summary.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    run_summary = RunSummary.model_validate_json(run_summary_path.read_text(encoding="utf-8"))
    manifest_path.write_text(
        json.dumps(manifest.model_copy(update={"run_id": run_id}).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    run_summary_path.write_text(
        json.dumps(run_summary.model_copy(update={"run_id": run_id}).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
