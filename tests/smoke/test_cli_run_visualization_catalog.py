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
    index_html = (catalog_root / "catalog" / "index.html").read_text(encoding="utf-8")
    app_js = (catalog_root / "catalog" / "assets" / "app.js").read_text(encoding="utf-8")
    assert "catalog-workbench-panel-filter" in index_html
    assert "function currentWorkbenchPanel" in app_js
    assert "function serializeCatalogState" in app_js
    assert "function hydrateCatalogStateFromUrl" in app_js
    assert "catalog_return" in app_js
    assert "Open Selected Panel" in app_js

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


def test_run_visualization_catalog_surfaces_phase_c_gate_summary_from_workspace_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = tmp_path / "workspace-root"
    runs_root = workspace_root / "runs"
    run_root_a = runs_root / "run-a"
    run_root_b = runs_root / "run-b"
    catalog_root = tmp_path / "catalog-root"
    _write_packaged_run(run_root_a, run_id="run-a", mode="prefill", schedule_kind="single-core")
    _write_packaged_run(run_root_b, run_id="run-b", mode="decode", schedule_kind="dual-core")
    (workspace_root / "reports").mkdir(parents=True, exist_ok=True)
    (workspace_root / "reports" / "phase_c_acceptance_report.json").write_text(
        json.dumps(
            {
                "report_name": "phase-c-acceptance.workspace-root",
                "status": "in_progress",
                "matrix_coverage": {
                    "expected_case_ids": [
                        "single-core:prefill",
                        "single-core:decode",
                        "dual-core:prefill",
                        "dual-core:decode",
                    ],
                    "present_case_ids": [
                        "single-core:prefill",
                        "dual-core:decode",
                    ],
                    "missing_case_ids": ["single-core:decode", "dual-core:prefill"],
                    "duplicate_case_ids": [],
                    "ready_case_count": 2,
                    "blocked_case_count": 2,
                    "planner_blocked_case_count": 1,
                    "downstream_blocked_case_count": 1,
                },
                "case_records": [],
                "issues": [],
                "remaining_gaps": [
                    "missing canonical case: single-core:decode",
                    "missing canonical case: dual-core:prefill",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_cli(
        "run-visualization-catalog",
        "--catalog-root",
        str(catalog_root),
        "--workspace-root",
        str(workspace_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    index_html = (catalog_root / "catalog" / "index.html").read_text(encoding="utf-8")
    manifest = json.loads((catalog_root / "catalog" / "catalog_manifest.json").read_text(encoding="utf-8"))
    assert "Phase C Gate" in index_html
    assert "planner_blocked" in index_html
    assert "downstream_blocked" in index_html
    assert manifest["metadata"]["phase_c_gate_summary"]["status"] == "in_progress"
    assert manifest["metadata"]["phase_c_gate_summary"]["missing_case_count"] == 2


def test_run_visualization_catalog_surfaces_phase_c_blocked_cases_from_workspace_root(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = tmp_path / "workspace-root"
    runs_root = workspace_root / "runs"
    run_root_a = runs_root / "run-single-prefill"
    catalog_root = tmp_path / "catalog-root"
    _write_packaged_run(run_root_a, run_id="run-single-prefill", mode="prefill", schedule_kind="single-core")
    _write_packaged_run(
        runs_root / "run-single-decode",
        run_id="run-single-decode",
        mode="decode",
        schedule_kind="single-core",
    )
    (workspace_root / "reports").mkdir(parents=True, exist_ok=True)
    (workspace_root / "reports" / "phase_c_acceptance_report.json").write_text(
        json.dumps(
            {
                "report_name": "phase-c-acceptance.workspace-root",
                "status": "in_progress",
                "matrix_coverage": {
                    "expected_case_ids": [
                        "single-core:prefill",
                        "single-core:decode",
                        "dual-core:prefill",
                        "dual-core:decode",
                    ],
                    "present_case_ids": [
                        "single-core:prefill",
                        "single-core:decode",
                        "dual-core:decode",
                    ],
                    "missing_case_ids": ["dual-core:prefill"],
                    "duplicate_case_ids": [],
                    "ready_case_count": 1,
                    "blocked_case_count": 2,
                    "planner_blocked_case_count": 1,
                    "downstream_blocked_case_count": 1,
                },
                "case_records": [
                    {
                        "case_id": "single-core:prefill",
                        "run_id": "run-single-prefill",
                        "run_root": "workspace/runs/run-single-prefill",
                        "scenario_name": "prefill_seq128",
                        "mode": "prefill",
                        "schedule_kind": "single-core",
                        "target_profile_name": "riscv_npu_single_core_v1",
                        "closure_report_path": "reports/memory_planner_closure_report.json",
                        "closure_status": "in_progress",
                        "planner_closure_status": "in_progress",
                        "planner_remaining_gaps": ["overflow region: ping"],
                        "downstream_closure_status": "ready_for_acceptance",
                        "downstream_remaining_gaps": [],
                        "downstream_missing_consumers": [],
                        "verified_required_consumer_count": 4,
                        "required_consumer_count": 4,
                        "remaining_gaps": ["planner_closure: overflow region: ping"],
                    },
                    {
                        "case_id": "single-core:decode",
                        "run_id": "run-single-decode",
                        "run_root": "workspace/runs/run-single-decode",
                        "scenario_name": "decode_token1_kv2048",
                        "mode": "decode",
                        "schedule_kind": "single-core",
                        "target_profile_name": "riscv_npu_single_core_v1",
                        "closure_report_path": "reports/memory_planner_closure_report.json",
                        "closure_status": "in_progress",
                        "planner_closure_status": "ready_for_acceptance",
                        "planner_remaining_gaps": [],
                        "downstream_closure_status": "in_progress",
                        "downstream_remaining_gaps": ["required downstream evidence missing"],
                        "downstream_missing_consumers": ["performance_estimation"],
                        "verified_required_consumer_count": 3,
                        "required_consumer_count": 4,
                        "remaining_gaps": ["required downstream evidence missing"],
                    },
                    {
                        "case_id": "dual-core:decode",
                        "run_id": "run-dual-decode",
                        "run_root": "workspace/runs/run-dual-decode",
                        "scenario_name": "decode_token1_kv2048",
                        "mode": "decode",
                        "schedule_kind": "dual-core",
                        "target_profile_name": "riscv_npu_dual_core_v1",
                        "closure_report_path": "reports/memory_planner_closure_report.json",
                        "closure_status": "ready_for_acceptance",
                        "planner_closure_status": "ready_for_acceptance",
                        "planner_remaining_gaps": [],
                        "downstream_closure_status": "ready_for_acceptance",
                        "downstream_remaining_gaps": [],
                        "downstream_missing_consumers": [],
                        "verified_required_consumer_count": 4,
                        "required_consumer_count": 4,
                        "remaining_gaps": [],
                    },
                ],
                "issues": [],
                "remaining_gaps": [
                    "single-core:prefill (run-single-prefill): planner_closure: overflow region: ping",
                    "single-core:decode (run-single-decode): required downstream evidence missing",
                    "missing canonical case: dual-core:prefill",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_cli(
        "run-visualization-catalog",
        "--catalog-root",
        str(catalog_root),
        "--workspace-root",
        str(workspace_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    index_html = (catalog_root / "catalog" / "index.html").read_text(encoding="utf-8")
    app_js = (catalog_root / "catalog" / "assets" / "app.js").read_text(encoding="utf-8")
    manifest = json.loads((catalog_root / "catalog" / "catalog_manifest.json").read_text(encoding="utf-8"))
    assert "Blocked Cases" in index_html
    assert "single-core:prefill" in index_html
    assert "single-core:decode" in index_html
    assert "dual-core:prefill" in index_html
    assert "planner" in index_html
    assert "downstream" in index_html
    assert "missing_case" in index_html
    assert "Open Memory" in index_html
    assert "Open Summary" in index_html
    assert "Open Workbench" not in index_html
    assert "../../workspace-root/runs/run-single-prefill/workbench/index.html?panel=memory&memory_query=ping" in index_html
    assert "../../workspace-root/runs/run-single-decode/workbench/index.html?panel=summary" in index_html
    assert 'class="blocked-case-workbench-link"' in index_html
    assert 'data-workbench-path="../../workspace-root/runs/run-single-prefill/workbench/index.html"' in index_html
    assert 'data-workbench-panel="memory"' in index_html
    assert 'data-workbench-memory-query="ping"' in index_html
    assert 'data-workbench-panel="summary"' in index_html
    assert "function refreshBlockedCaseWorkbenchLinks" in app_js
    assert 'document.querySelectorAll(".blocked-case-workbench-link")' in app_js
    assert "workbenchMemoryQuery" in app_js
    assert "refreshBlockedCaseWorkbenchLinks();" in app_js
    assert len(manifest["metadata"]["phase_c_blocked_cases"]) == 3
    assert (
        manifest["metadata"]["phase_c_blocked_cases"][0]["workbench_entry_path"]
        == "../../workspace-root/runs/run-single-prefill/workbench/index.html"
    )
    assert (
        manifest["metadata"]["phase_c_blocked_cases"][1]["workbench_entry_path"]
        == "../../workspace-root/runs/run-single-decode/workbench/index.html"
    )
    assert manifest["metadata"]["phase_c_blocked_cases"][1]["downstream_missing_consumers"] == [
        "performance_estimation"
    ]
    assert manifest["metadata"]["phase_c_blocked_cases"][2]["workbench_entry_path"] is None


def test_run_visualization_catalog_surfaces_descriptor_generation_focus_link(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    workspace_root = tmp_path / "workspace-root"
    runs_root = workspace_root / "runs"
    catalog_root = tmp_path / "catalog-root"
    _write_packaged_run(
        runs_root / "run-single-decode",
        run_id="run-single-decode",
        mode="decode",
        schedule_kind="single-core",
    )
    (workspace_root / "reports").mkdir(parents=True, exist_ok=True)
    (workspace_root / "reports" / "phase_c_acceptance_report.json").write_text(
        json.dumps(
            {
                "report_name": "phase-c-acceptance.workspace-root",
                "status": "in_progress",
                "matrix_coverage": {
                    "expected_case_ids": [
                        "single-core:prefill",
                        "single-core:decode",
                        "dual-core:prefill",
                        "dual-core:decode",
                    ],
                    "present_case_ids": ["single-core:decode"],
                    "missing_case_ids": [
                        "single-core:prefill",
                        "dual-core:prefill",
                        "dual-core:decode",
                    ],
                    "duplicate_case_ids": [],
                    "ready_case_count": 0,
                    "blocked_case_count": 1,
                    "planner_blocked_case_count": 0,
                    "downstream_blocked_case_count": 1,
                },
                "case_records": [
                    {
                        "case_id": "single-core:decode",
                        "run_id": "run-single-decode",
                        "run_root": "workspace/runs/run-single-decode",
                        "scenario_name": "decode_token1_kv2048",
                        "mode": "decode",
                        "schedule_kind": "single-core",
                        "target_profile_name": "riscv_npu_single_core_v1",
                        "closure_report_path": "reports/memory_planner_closure_report.json",
                        "closure_status": "in_progress",
                        "planner_closure_status": "ready_for_acceptance",
                        "planner_remaining_gaps": [],
                        "downstream_closure_status": "in_progress",
                        "downstream_remaining_gaps": [
                            "descriptor_generation: descriptor_ir exists but structured address fields lack storage provenance."
                        ],
                        "downstream_missing_consumers": ["descriptor_generation"],
                        "verified_required_consumer_count": 4,
                        "required_consumer_count": 5,
                        "remaining_gaps": [
                            "descriptor_generation: descriptor_ir exists but structured address fields lack storage provenance."
                        ],
                    }
                ],
                "issues": [],
                "remaining_gaps": [
                    "single-core:decode (run-single-decode): descriptor_generation: descriptor_ir exists but structured address fields lack storage provenance."
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_cli(
        "run-visualization-catalog",
        "--catalog-root",
        str(catalog_root),
        "--workspace-root",
        str(workspace_root),
        cwd=repo_root,
    )

    assert result.returncode == 0
    index_html = (catalog_root / "catalog" / "index.html").read_text(encoding="utf-8")
    app_js = (catalog_root / "catalog" / "assets" / "app.js").read_text(encoding="utf-8")
    assert (
        "../../workspace-root/runs/run-single-decode/workbench/index.html?panel=coverage&coverage_focus=packed-descriptor"
        in index_html
    )
    assert 'data-workbench-coverage-focus="packed-descriptor"' in index_html
    assert "workbenchCoverageFocus" in app_js


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
