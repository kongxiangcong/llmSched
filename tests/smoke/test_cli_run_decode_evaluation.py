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


def test_run_decode_evaluation_writes_report_for_single_core(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-decode-cli-single",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )

    result = run_cli("run-decode-evaluation", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((run_root / "reports" / "decode_evaluation_report.json").read_text(encoding="utf-8"))

    assert manifest["artifact_index"]["decode_evaluation_report"] == "reports/decode_evaluation_report.json"
    assert report["scenario_name"] == "decode_token1_kv2048"
    assert report["token_latency"]["estimated_cycles"] > 0.0
    assert report["token_latency"]["phase_attribution"]["projection"]["cycles_per_token"] >= 0.0
    assert report["token_latency"]["phase_attribution"]["kv_io"]["bytes_per_token"] >= 0.0
    assert report["token_latency"]["phase_attribution"]["projection"]["occupied_slots"] >= 0.0
    assert report["token_latency"]["phase_attribution"]["other"]["occupied_slots_per_token"] >= 0.0
    assert isinstance(report["token_latency"]["phase_attribution"]["kv_io"]["read_bytes_by_address_space"], dict)
    assert isinstance(report["token_latency"]["phase_attribution"]["kv_io"]["write_bytes_by_address_space"], dict)


def test_run_decode_evaluation_rejects_prefill_without_traceback(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-decode-cli-prefill",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )

    result = run_cli("run-decode-evaluation", "--run-root", str(run_root), cwd=repo_root)

    assert result.returncode == 1
    assert "Decode evaluation: ERROR" in result.stdout
    assert "decode" in result.stdout.lower()
    assert "Traceback" not in result.stderr
