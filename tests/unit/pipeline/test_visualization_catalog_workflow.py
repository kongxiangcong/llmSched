import json
from pathlib import Path


def test_run_visualization_catalog_writes_static_index_from_run_roots(tmp_path: Path) -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact
    from llm_sched.pipeline import run_visualization_catalog

    run_root_a = tmp_path / "run-a"
    run_root_b = tmp_path / "run-b"
    _write_packaged_run(
        run_root_a,
        run_id="run-a",
        scenario_name="prefill_seq128",
        mode="prefill",
        schedule_kind="single-core",
        target_profile_name="riscv_npu_single_core_v1",
        primary_metrics={"estimated_cycles": 4096.0},
    )
    _write_packaged_run(
        run_root_b,
        run_id="run-b",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="dual-core",
        target_profile_name="riscv_npu_dual_core_v1",
        primary_metrics={"token_latency_cycles": 512.0},
    )
    catalog_root = tmp_path / "catalog-root"

    result = run_visualization_catalog(catalog_root, [run_root_a, run_root_b])

    assert result.status == "completed"
    assert result.entry_html_path == catalog_root / "catalog" / "index.html"
    assert result.catalog_manifest_path == catalog_root / "catalog" / "catalog_manifest.json"

    artifact = VisualizationCatalogArtifact.model_validate_json(
        result.catalog_manifest_path.read_text(encoding="utf-8")
    )
    assert artifact.metadata.entry_count == 2
    assert artifact.entries[0].workbench_entry_path.endswith("workbench/index.html")
    assert (catalog_root / "catalog" / "index.html").is_file()


def test_run_visualization_catalog_rejects_missing_workbench_manifest(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_visualization_catalog

    run_root = tmp_path / "run-missing-workbench"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "reports").mkdir(parents=True, exist_ok=True)
    (run_root / "reports" / "visualization_bundle.json").write_text(
        json.dumps(_bundle_payload(run_id="run-missing-workbench"), indent=2),
        encoding="utf-8",
    )

    result = run_visualization_catalog(tmp_path / "catalog-root", [run_root])

    assert result.status == "failed"
    assert result.entry_html_path is None
    assert result.catalog_manifest_path is None
    assert "workbench_manifest" in result.diagnostics[0].message


def test_run_visualization_catalog_discovers_runs_from_sweep_root(tmp_path: Path) -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact
    from llm_sched.pipeline import run_visualization_catalog

    sweep_root = tmp_path / "sweep-root"
    run_root = sweep_root / "runs" / "run-a"
    _write_packaged_run(
        run_root,
        run_id="run-a",
        scenario_name="prefill_seq128",
        mode="prefill",
        schedule_kind="single-core",
        target_profile_name="riscv_npu_single_core_v1",
        primary_metrics={"estimated_cycles": 4096.0},
    )
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

    result = run_visualization_catalog(tmp_path / "catalog-root", [], sweep_root=sweep_root)

    assert result.status == "completed"
    artifact = VisualizationCatalogArtifact.model_validate_json(
        result.catalog_manifest_path.read_text(encoding="utf-8")
    )
    assert artifact.metadata.entry_count == 1
    assert artifact.entries[0].run_id == "run-a"


def test_run_visualization_catalog_discovers_runs_from_workspace_root_and_deduplicates(
    tmp_path: Path,
) -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact
    from llm_sched.pipeline import run_visualization_catalog

    workspace_root = tmp_path / "workspace-root"
    run_root = workspace_root / "run-a"
    _write_packaged_run(
        run_root,
        run_id="run-a",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="dual-core",
        target_profile_name="riscv_npu_dual_core_v1",
        primary_metrics={"token_latency_cycles": 512.0},
    )

    result = run_visualization_catalog(
        tmp_path / "catalog-root",
        [run_root],
        workspace_root=workspace_root,
    )

    assert result.status == "completed"
    artifact = VisualizationCatalogArtifact.model_validate_json(
        result.catalog_manifest_path.read_text(encoding="utf-8")
    )
    assert artifact.metadata.entry_count == 1
    assert artifact.entries[0].run_id == "run-a"


def test_run_visualization_catalog_rejects_empty_sources(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_visualization_catalog

    result = run_visualization_catalog(tmp_path / "catalog-root", [])

    assert result.status == "failed"
    assert result.entry_html_path is None
    assert "no run roots" in result.diagnostics[0].message.lower()


def _write_packaged_run(
    run_root: Path,
    *,
    run_id: str,
    scenario_name: str,
    mode: str,
    schedule_kind: str,
    target_profile_name: str,
    primary_metrics: dict[str, float],
) -> None:
    (run_root / "reports").mkdir(parents=True, exist_ok=True)
    (run_root / "workbench" / "assets").mkdir(parents=True, exist_ok=True)
    (run_root / "workbench" / "index.html").write_text("<html></html>", encoding="utf-8")
    (run_root / "workbench" / "workbench_manifest.json").write_text(
        json.dumps(
            {
                "workbench_id": f"workbench.{run_id}",
                "metadata": {
                    "run_id": run_id,
                    "graph_id": "gemma3-prefill",
                    "scenario_name": scenario_name,
                    "mode": mode,
                    "schedule_kind": schedule_kind,
                    "title": f"{run_id} title",
                },
                "entry_html_path": "workbench/index.html",
                "bundle_path": "../reports/visualization_bundle.json",
                "default_panel": "summary",
                "available_panels": ["summary", "graph", "timeline", "memory", "coverage"],
                "asset_files": [
                    {
                        "path": "workbench/index.html",
                        "media_type": "text/html",
                        "role": "entry_html",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_root / "reports" / "visualization_bundle.json").write_text(
        json.dumps(
            _bundle_payload(
                run_id=run_id,
                scenario_name=scenario_name,
                mode=mode,
                schedule_kind=schedule_kind,
                target_profile_name=target_profile_name,
                primary_metrics=primary_metrics,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )


def _bundle_payload(
    *,
    run_id: str,
    scenario_name: str = "prefill_seq128",
    mode: str = "prefill",
    schedule_kind: str = "single-core",
    target_profile_name: str = "riscv_npu_single_core_v1",
    primary_metrics: dict[str, float] | None = None,
) -> dict[str, object]:
    return {
        "bundle_id": f"viz.{run_id}",
        "metadata": {
            "run_id": run_id,
            "graph_id": "gemma3-prefill",
            "scenario_name": scenario_name,
            "mode": mode,
            "schedule_kind": schedule_kind,
            "target_profile_name": target_profile_name,
            "target_profile_path": f"profiles/targets/{target_profile_name}.json",
            "scenario_profile_path": f"profiles/scenarios/{scenario_name}.json",
            "run_root": str(run_id),
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
            "primary_metrics": primary_metrics or {"estimated_cycles": 4096.0},
            "hotspot_macro_ops": ["WDQ_GEMM"],
        },
        "graph_view": {
            "graph_id": "gemma3-prefill",
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
    }
