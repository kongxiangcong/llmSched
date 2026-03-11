import json
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from llm_sched.config.loader import load_scenario_profile, load_target_profile
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.sweep_report import SweepDeltaReport


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
    cache_root = tmp_path_factory.mktemp("psr", numbered=False)

    def prepare_cached_root(
        *,
        target_relative_path: str,
        scenario_relative_path: str,
        final_stage: str,
    ) -> Path:
        target_profile = load_target_profile(smoke_repo_root / target_relative_path)
        scenario_profile = load_scenario_profile(smoke_repo_root / scenario_relative_path)
        stage_sequence = _smoke_stage_sequence(target_profile, scenario_profile)
        if final_stage not in stage_sequence:
            raise ValueError(f"unsupported final_stage: {final_stage}")

        cache_key = _smoke_cache_key(
            Path(target_relative_path).stem,
            Path(scenario_relative_path).stem,
            final_stage,
        )
        prepared_root = cache_root / cache_key
        ready_flag = prepared_root / ".prepared"
        if not ready_flag.is_file():
            if prepared_root.exists():
                shutil.rmtree(prepared_root)
            final_stage_index = stage_sequence.index(final_stage)
            previous_stage = stage_sequence[final_stage_index - 1] if final_stage_index > 0 else None
            if previous_stage is None:
                _initialize_cli_run_root(
                    prepared_root,
                    smoke_repo_root,
                    target_relative_path=target_relative_path,
                    scenario_relative_path=scenario_relative_path,
                )
            else:
                previous_root = prepare_cached_root(
                    target_relative_path=target_relative_path,
                    scenario_relative_path=scenario_relative_path,
                    final_stage=previous_stage,
                )
                _clone_prepared_run_root(previous_root, prepared_root)
                _rewrite_run_identity(prepared_root, prepared_root.name)
            _prepare_cli_run_root_to_stage(
                prepared_root,
                smoke_repo_root,
                target_relative_path=target_relative_path,
                scenario_relative_path=scenario_relative_path,
                final_stage=final_stage,
                start_after_stage=previous_stage,
            )
            ready_flag.write_text("prepared", encoding="utf-8")

        return prepared_root

    def factory(
        *,
        target_run_root: Path,
        target_relative_path: str,
        scenario_relative_path: str,
        final_stage: str,
    ) -> Path:
        prepared_root = prepare_cached_root(
            target_relative_path=target_relative_path,
            scenario_relative_path=scenario_relative_path,
            final_stage=final_stage,
        )

        _clone_prepared_run_root(prepared_root, target_run_root)
        _rewrite_run_identity(target_run_root, target_run_root.name)
        return target_run_root

    return factory


@pytest.fixture(scope="session")
def prepared_smoke_sweep_root_factory(
    tmp_path_factory: pytest.TempPathFactory,
    smoke_repo_root: Path,
):
    cache_root = tmp_path_factory.mktemp("pss", numbered=False)

    def factory(
        *,
        target_sweep_root: Path,
        baseline_target_relative_path: str,
        target_relative_paths: list[str],
        scenario_relative_paths: list[str],
        sweep_name: str = "smoke-cli-sweep",
    ) -> Path:
        cache_key = _smoke_cache_key(
            sweep_name,
            Path(baseline_target_relative_path).stem,
            sorted(Path(path).stem for path in target_relative_paths),
            sorted(Path(path).stem for path in scenario_relative_paths),
        )
        prepared_root = cache_root / cache_key
        ready_flag = prepared_root / ".prepared"
        if not ready_flag.is_file():
            if prepared_root.exists():
                shutil.rmtree(prepared_root)
            prepared_root.mkdir(parents=True, exist_ok=True)
            spec_path = prepared_root / "sweep-spec.json"
            _write_smoke_sweep_spec(
                spec_path,
                smoke_repo_root,
                sweep_name=sweep_name,
                baseline_target_relative_path=baseline_target_relative_path,
                target_relative_paths=target_relative_paths,
                scenario_relative_paths=scenario_relative_paths,
            )
            result = run_cli(
                "run-sweep-analysis",
                "--sweep-spec",
                str(spec_path),
                "--sweep-root",
                str(prepared_root),
                cwd=smoke_repo_root,
            )
            assert result.returncode == 0, result.stderr
            ready_flag.write_text("prepared", encoding="utf-8")

        _clone_prepared_sweep_root(prepared_root, target_sweep_root)
        _rewrite_sweep_report_paths(target_sweep_root)
        return target_sweep_root

    return factory


def _prepare_cli_run_root_to_stage(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    scenario_relative_path: str,
    final_stage: str,
    start_after_stage: str | None = None,
) -> None:
    target_profile = load_target_profile(repo_root / target_relative_path)
    scenario_profile = load_scenario_profile(repo_root / scenario_relative_path)
    stage_sequence = _smoke_stage_sequence(target_profile, scenario_profile)
    if final_stage not in stage_sequence:
        raise ValueError(f"unsupported final_stage: {final_stage}")
    start_index = 0 if start_after_stage is None else stage_sequence.index(start_after_stage) + 1
    final_index = stage_sequence.index(final_stage)

    for stage in stage_sequence[start_index : final_index + 1]:
        result = _run_smoke_cli_stage(run_root, repo_root, stage, target_profile=target_profile, scenario_profile=scenario_profile)
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


def _clone_prepared_sweep_root(prepared_root: Path, target_sweep_root: Path) -> None:
    if target_sweep_root.exists():
        shutil.rmtree(target_sweep_root)
    shutil.copytree(prepared_root, target_sweep_root)


def _smoke_stage_sequence(target_profile, scenario_profile) -> tuple[str, ...]:
    eval_stage = "prefill_eval" if scenario_profile.mode == "prefill" else "decode_eval"
    return ("frontend", "memory", "tile", "schedule", "descriptor", "performance", eval_stage, "visualization_bundle")


def _run_smoke_cli_stage(
    run_root: Path,
    repo_root: Path,
    stage: str,
    *,
    target_profile,
    scenario_profile,
) -> subprocess.CompletedProcess[str]:
    if stage == "frontend":
        return run_cli("run-frontend-analysis", "--run-root", str(run_root), cwd=repo_root)
    if stage == "memory":
        return run_cli("run-memory-planning", "--run-root", str(run_root), cwd=repo_root)
    if stage == "tile":
        return run_cli("run-tile-planning", "--run-root", str(run_root), cwd=repo_root)
    if stage == "schedule":
        scheduling_command = (
            "run-single-core-scheduling"
            if target_profile.core_mode == "single-core"
            else "run-dual-core-scheduling"
        )
        return run_cli(scheduling_command, "--run-root", str(run_root), cwd=repo_root)
    if stage == "descriptor":
        return run_cli("run-descriptor-generation", "--run-root", str(run_root), cwd=repo_root)
    if stage == "performance":
        return run_cli("run-performance-estimation", "--run-root", str(run_root), cwd=repo_root)
    if stage == "prefill_eval":
        if scenario_profile.mode != "prefill":
            raise ValueError("prefill_eval requires a prefill scenario")
        return run_cli("run-prefill-evaluation", "--run-root", str(run_root), cwd=repo_root)
    if stage == "decode_eval":
        if scenario_profile.mode != "decode":
            raise ValueError("decode_eval requires a decode scenario")
        return run_cli("run-decode-evaluation", "--run-root", str(run_root), cwd=repo_root)
    if stage == "visualization_bundle":
        return run_cli("run-visualization-packaging", "--run-root", str(run_root), cwd=repo_root)
    raise ValueError(f"unsupported stage: {stage}")


def _smoke_cache_key(*parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, ensure_ascii=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _write_smoke_sweep_spec(
    spec_path: Path,
    repo_root: Path,
    *,
    sweep_name: str,
    baseline_target_relative_path: str,
    target_relative_paths: list[str],
    scenario_relative_paths: list[str],
) -> None:
    spec_path.write_text(
        json.dumps(
            {
                "sweep_name": sweep_name,
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str((repo_root / baseline_target_relative_path).resolve()),
                "target_profiles": [str((repo_root / path).resolve()) for path in target_relative_paths],
                "scenario_profiles": [str((repo_root / path).resolve()) for path in scenario_relative_paths],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _rewrite_sweep_report_paths(sweep_root: Path) -> None:
    report_path = sweep_root / "reports" / "sweep_delta_report.json"
    report = SweepDeltaReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    run_records = []
    for record in report.run_records:
        cloned_run_root = sweep_root / "runs" / Path(record.run_root).name
        cloned_report_path = None
        if record.report_path is not None:
            cloned_report_path = str(cloned_run_root / "reports" / Path(record.report_path).name)
        run_records.append(
            record.model_copy(
                update={
                    "run_root": str(cloned_run_root),
                    "report_path": cloned_report_path,
                }
            )
        )
    report_path.write_text(
        json.dumps(report.model_copy(update={"run_records": run_records}, deep=True).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


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
