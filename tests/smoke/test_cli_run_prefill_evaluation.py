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


def test_run_prefill_evaluation_writes_report_for_single_core(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-prefill-cli-single",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )

    result = run_cli("run-prefill-evaluation", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0

    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((run_root / "reports" / "prefill_evaluation_report.json").read_text(encoding="utf-8"))

    assert manifest["artifact_index"]["prefill_evaluation_report"] == "reports/prefill_evaluation_report.json"
    assert report["scenario_name"] == "prefill_seq128"
    assert report["throughput"]["estimated_cycles"] > 0.0
    assert report["throughput"]["fitted_work_cycles"] >= report["throughput"]["estimated_cycles"]
    assert report["throughput"]["tokens_per_fitted_work_cycle"] > 0.0
    assert report["throughput"]["projection_fitted_work_cycles"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["cycles_per_token"] > 0.0
    assert report["throughput"]["phase_attribution"]["attention"]["bytes_per_token"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["compute_cycles"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["memory_cycles"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["sync_cycles"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["schedule_compression_cycles"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["schedule_compression_ratio"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["schedule_overhang_cycles"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["occupied_slots"] > 0.0
    assert report["throughput"]["phase_attribution"]["other"]["occupied_slots_per_token"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["per_core_occupied_slots"] == {
        "0": report["throughput"]["phase_attribution"]["projection"]["occupied_slots"]
    }
    assert report["throughput"]["phase_attribution"]["projection"]["per_core_span_slots"]["0"] >= report["throughput"]["phase_attribution"]["projection"]["per_core_occupied_slots"]["0"]
    assert report["throughput"]["phase_attribution"]["projection"]["occupied_slot_imbalance_slots"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["occupied_slot_balance_ratio"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["span_imbalance_slots"] >= 0.0
    assert report["throughput"]["phase_attribution"]["projection"]["span_balance_ratio"] >= 0.0
    assert isinstance(report["throughput"]["phase_attribution"]["projection"]["read_bytes_by_address_space"], dict)
    assert isinstance(report["throughput"]["phase_attribution"]["projection"]["write_bytes_by_address_space"], dict)
    assert isinstance(report["throughput"]["phase_attribution"]["projection"]["read_bytes_by_backing_store"], dict)
    assert isinstance(report["throughput"]["phase_attribution"]["projection"]["write_bytes_by_backing_store"], dict)
    assert isinstance(report["throughput"]["phase_attribution"]["projection"]["read_bytes_by_memory_class"], dict)
    assert isinstance(report["throughput"]["phase_attribution"]["projection"]["write_bytes_by_memory_class"], dict)


def test_run_prefill_evaluation_rejects_decode_without_traceback(
    tmp_path: Path,
    prepared_smoke_run_root_factory,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = prepared_smoke_run_root_factory(
        target_run_root=tmp_path / "run-prefill-cli-decode",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )

    result = run_cli("run-prefill-evaluation", "--run-root", str(run_root), cwd=repo_root)

    assert result.returncode == 1
    assert "Prefill evaluation: ERROR" in result.stdout
    assert "prefill" in result.stdout.lower()
    assert "Traceback" not in result.stderr
