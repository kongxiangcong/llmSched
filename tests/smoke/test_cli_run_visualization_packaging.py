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


def test_run_visualization_packaging_writes_bundle_with_optional_sweep(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
    prepared_smoke_sweep_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-viz-cli-decode",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="decode_eval",
    )
    sweep_root = prepared_smoke_sweep_root_factory(
        target_sweep_root=tmp_path / "sweep-viz-cli",
        baseline_target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        target_relative_paths=[
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/targets/riscv_npu_dual_core_v1.json",
        ],
        scenario_relative_paths=["profiles/scenarios/decode_token1_kv2048.json"],
        sweep_name="viz-cli-sweep",
    )

    result = run_cli(
        "run-visualization-packaging",
        "--run-root",
        str(run_root),
        "--sweep-root",
        str(sweep_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Visualization packaging completed" in result.stdout

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    bundle = json.loads((run_root / "reports" / "visualization_bundle.json").read_text(encoding="utf-8"))

    assert manifest["artifact_index"]["visualization_bundle"] == "reports/visualization_bundle.json"
    assert bundle["metadata"]["mode"] == "decode"
    assert bundle["sweep_view"] is not None


def test_run_visualization_packaging_rejects_missing_top_level_report_without_traceback(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-viz-cli-missing-report",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )

    result = run_cli(
        "run-visualization-packaging",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Visualization packaging: ERROR" in result.stdout
    assert "prefill" in result.stdout.lower()
    assert "Traceback" not in result.stderr
