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


def test_run_visualization_catalog_writes_catalog_index(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root_a = tmp_path / "run-a"
    run_root_b = tmp_path / "run-b"
    catalog_root = tmp_path / "catalog-root"
    _write_packaged_run(run_root_a, run_id="run-a", mode="prefill", schedule_kind="single-core")
    _write_packaged_run(run_root_b, run_id="run-b", mode="decode", schedule_kind="dual-core")

    result = run_cli(
        "run-visualization-catalog",
        "--catalog-root",
        str(catalog_root),
        "--run-root",
        str(run_root_a),
        "--run-root",
        str(run_root_b),
        cwd=repo_root,
    )

    assert result.returncode == 0
    assert "Visualization catalog completed" in result.stdout
    assert (catalog_root / "catalog" / "index.html").is_file()

    manifest = json.loads((catalog_root / "catalog" / "catalog_manifest.json").read_text(encoding="utf-8"))
    assert manifest["metadata"]["entry_count"] == 2


def test_run_visualization_catalog_rejects_missing_workbench_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / "run-missing"
    run_root.mkdir(parents=True, exist_ok=True)

    result = run_cli(
        "run-visualization-catalog",
        "--catalog-root",
        str(tmp_path / "catalog-root"),
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )

    assert result.returncode == 1
    assert "Visualization catalog: ERROR" in result.stdout
    assert "Traceback" not in result.stderr


def test_run_visualization_catalog_supports_sweep_root_discovery(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sweep_root = tmp_path / "sweep-root"
    run_root = sweep_root / "runs" / "run-a"
    catalog_root = tmp_path / "catalog-root"
    _write_packaged_run(run_root, run_id="run-a", mode="prefill", schedule_kind="single-core")
    (sweep_root / "reports").mkdir(parents=True, exist_ok=True)
    (sweep_root / "reports" / "sweep_delta_report.json").write_text(
        json.dumps(
            {
                "sweep_name": "phase-d",
                "baseline_target_profile_name": "riscv_npu_single_core_v1",
                "completed_run_count": 1,
                "failed_run_count": 0,
                "run_records": [
                    {
                        "run_id": "run-a",
                        "run_root": str(run_root),
                        "target_profile_name": "riscv_npu_single_core_v1",
                        "target_profile_path": "profiles/targets/riscv_npu_single_core_v1.json",
                        "scenario_name": "prefill_seq128",
                        "mode": "prefill",
                        "schedule_kind": "single-core",
                        "status": "completed",
                        "report_path": str(run_root / "reports" / "prefill_evaluation_report.json"),
                        "metrics": {"estimated_cycles": 4096.0},
                        "macro_hotspots": [],
                        "failure_message": None,
                    }
                ],
                "comparisons": [],
                "issues": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_cli(
        "run-visualization-catalog",
        "--catalog-root",
        str(catalog_root),
        "--sweep-root",
        str(sweep_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    manifest = json.loads((catalog_root / "catalog" / "catalog_manifest.json").read_text(encoding="utf-8"))
    assert manifest["metadata"]["entry_count"] == 1


def _write_packaged_run(run_root: Path, *, run_id: str, mode: str, schedule_kind: str) -> None:
    (run_root / "reports").mkdir(parents=True, exist_ok=True)
    (run_root / "workbench").mkdir(parents=True, exist_ok=True)
    (run_root / "workbench" / "index.html").write_text("<html></html>", encoding="utf-8")
    (run_root / "workbench" / "workbench_manifest.json").write_text(
        json.dumps(
            {
                "workbench_id": f"workbench.{run_id}",
                "metadata": {
                    "run_id": run_id,
                    "graph_id": "gemma3",
                    "scenario_name": "prefill_seq128" if mode == "prefill" else "decode_token1_kv2048",
                    "mode": mode,
                    "schedule_kind": schedule_kind,
                    "title": run_id,
                },
                "entry_html_path": "workbench/index.html",
                "bundle_path": "../reports/visualization_bundle.json",
                "default_panel": "summary",
                "available_panels": ["summary", "graph", "timeline", "memory", "coverage"],
                "asset_files": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_root / "reports" / "visualization_bundle.json").write_text(
        json.dumps(
            {
                "bundle_id": f"viz.{run_id}",
                "metadata": {
                    "run_id": run_id,
                    "graph_id": "gemma3",
                    "scenario_name": "prefill_seq128" if mode == "prefill" else "decode_token1_kv2048",
                    "mode": mode,
                    "schedule_kind": schedule_kind,
                    "target_profile_name": "riscv_npu_single_core_v1" if schedule_kind == "single-core" else "riscv_npu_dual_core_v1",
                    "target_profile_path": "profiles/targets/target.json",
                    "scenario_profile_path": "profiles/scenarios/scenario.json",
                    "run_root": str(run_root),
                    "sweep_root": None,
                },
                "view_index": {
                    "available_views": ["graph", "timeline", "kv", "vmem", "coverage"],
                    "section_ids": {
                        "graph": "graph_view",
                        "timeline": "timeline_view",
                        "kv": "kv_view",
                        "vmem": "vmem_view",
                        "coverage": "coverage_view",
                    },
                },
                "report_summary": {
                    "report_kind": mode,
                    "primary_metrics": (
                        {"estimated_cycles": 4096.0}
                        if mode == "prefill"
                        else {"token_latency_cycles": 512.0}
                    ),
                    "hotspot_macro_ops": ["WDQ_GEMM"],
                },
                "graph_view": {
                    "graph_id": "gemma3",
                    "node_count": 1,
                    "edge_count": 0,
                    "op_counts": {"Linear": 1},
                    "nodes": [
                        {
                            "node_id": "graph.linear.0",
                            "label": "Linear",
                            "op_kind": "Linear",
                            "dtype": "float16",
                            "shape": [1, 128, 2048],
                        }
                    ],
                    "edges": [],
                },
                "timeline_view": {
                    "core_mode": schedule_kind,
                    "total_block_count": 1,
                    "core_block_counts": {"0": 1},
                    "blocks": [
                        {
                            "block_id": "sched.0",
                            "core_id": 0,
                            "node_id": "nig.linear.0",
                            "macro_op": "WDQ_GEMM",
                            "stage": "compute",
                            "order_key": 0,
                            "transfer_bytes": 0,
                            "sync_cost_cycles": 0,
                        }
                    ],
                },
                "kv_view": {
                    "kv_len": 0,
                    "kv_formula_count": 0,
                    "unresolved_address_count": 0,
                    "formulas": [],
                },
                "vmem_view": {
                    "max_region_utilization": 0.5,
                    "overflow_region_count": 0,
                    "regions": [
                        {
                            "region_name": "ping",
                            "capacity_bytes": 65536,
                            "peak_bytes": 32768,
                            "utilization_ratio": 0.5,
                            "fits": True,
                        }
                    ],
                    "diagnostics": [],
                },
                "coverage_view": {
                    "mapped_descriptor_count": 1,
                    "unmapped_block_count": 0,
                    "opcode_counts": {"WDQ_GEMM": 1},
                    "gap_counts": {},
                    "issues": [],
                },
                "sweep_view": None,
                "issues": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
