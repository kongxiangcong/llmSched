import json
from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary


def test_run_visualization_workbench_writes_assets_and_updates_manifest(tmp_path: Path) -> None:
    from llm_sched.contracts.visualization_bundle import VisualizationBundle
    from llm_sched.contracts.visualization_workbench import VisualizationWorkbenchArtifact
    from llm_sched.pipeline import run_visualization_workbench

    run_root = tmp_path / "run-workbench"
    _write_initialized_run(run_root)
    bundle_path = run_root / "reports" / "visualization_bundle.json"
    bundle_path.write_text(
        json.dumps(_bundle(include_sweep=True).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    result = run_visualization_workbench(run_root)

    assert result.status == "completed"
    assert result.entry_html_path == run_root / "workbench" / "index.html"
    assert result.workbench_manifest_path == run_root / "workbench" / "workbench_manifest.json"

    bundle = VisualizationBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
    workbench = VisualizationWorkbenchArtifact.model_validate_json(
        result.workbench_manifest_path.read_text(encoding="utf-8")
    )
    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = RunSummary.model_validate_json((run_root / "run-summary.json").read_text(encoding="utf-8"))
    app_js = (run_root / "workbench" / "assets" / "app.js").read_text(encoding="utf-8")

    assert bundle.metadata.run_id == "run-workbench"
    assert workbench.entry_html_path == "workbench/index.html"
    assert workbench.bundle_path == "../reports/visualization_bundle.json"
    assert "sweep" in workbench.available_panels
    assert manifest.artifact_index["visualization_workbench_manifest"] == "workbench/workbench_manifest.json"
    assert manifest.artifact_index["visualization_workbench_entry"] == "workbench/index.html"
    assert summary.status == "completed"
    assert summary.exit_code == 0
    assert "Packed Descriptor Summary" in app_js
    assert "Packed Layout Templates" in app_js
    assert "Packed Field Placements" in app_js
    assert "packed_record_count" in app_js
    assert "packed_layout_template_counts" in app_js
    assert "packed_field_name_counts" in app_js
    assert "Layer Deltas" in app_js
    assert "layer_deltas" in app_js
    assert "compare_focus" in app_js
    assert "layer_delta_focus" in app_js
    assert "analysis_flow" in app_js
    assert "sweep_candidate" in app_js
    assert "sweep_layer_focus" in app_js
    assert "function currentAnalysisFlow" in app_js
    assert "function resolveAnalysisFlowState" in app_js
    assert "focused_analysis_flow" in app_js
    assert "focused_analysis_flow_summary" in app_js
    assert "focused_compare_focus" in app_js
    assert "focused_layer_delta_mode" in app_js
    assert "focused_sweep_candidate" in app_js
    assert "focused_sweep_layer" in app_js
    assert "focused_comparison_count" in app_js
    assert "focused_layer_delta_count" in app_js
    assert "focused_layer_delta_summary" in app_js
    assert "Analysis Workflow" in app_js
    assert "Baseline Sweep Target" in app_js
    assert "Focused Analysis Workflow" in app_js
    assert "Focused Comparisons" in app_js
    assert "Focused Layer Deltas" in app_js
    assert "Focused Layer Summary" in app_js
    assert "function buildPanelSnapshotTitle" in app_js
    assert "function renderPanelSnapshotHeader" in app_js
    assert "function buildPanelExportFilename" in app_js
    assert "Focused Sweep Layer" in app_js
    assert "focused-sweep-row" in app_js
    assert "function buildSweepSnapshotMetadata" in app_js
    assert "snapshot_metadata" in app_js
    assert "header_rows" in app_js
    assert "Snapshot Focus" in app_js
    assert "Focused Compare Focus" in app_js
    assert "Throughput / Latency Focus" in app_js
    assert "Phase Shape Focus" in app_js
    assert "Focused Layer Delta Mode" in app_js
    index_html = (run_root / "workbench" / "index.html").read_text(encoding="utf-8")
    assert "back-to-catalog-link" in index_html
    assert "function updateCatalogReturnLink" in app_js
    assert "catalog_return" in app_js
    assert "Back to Catalog Compare" in app_js


def test_run_visualization_workbench_rejects_missing_bundle(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_visualization_workbench

    run_root = tmp_path / "missing-bundle"
    _write_initialized_run(run_root)

    result = run_visualization_workbench(run_root)

    assert result.status == "failed"
    assert result.entry_html_path is None
    assert result.workbench_manifest_path is None
    assert "visualization_bundle" in result.diagnostics[0].message


def test_run_visualization_workbench_surfaces_vmem_backing_store_mix_in_assets(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_visualization_workbench

    run_root = tmp_path / "run-workbench-backing-store"
    _write_initialized_run(run_root)
    bundle_path = run_root / "reports" / "visualization_bundle.json"
    bundle_path.write_text(
        json.dumps(_bundle(include_sweep=False).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    result = run_visualization_workbench(run_root)

    assert result.status == "completed"
    app_js = (run_root / "workbench" / "assets" / "app.js").read_text(encoding="utf-8")
    assert "Region Backing Store Mix" in app_js
    assert "peak_bytes_by_backing_store" in app_js
    assert "Top Region Backing Stores" in app_js


def test_run_visualization_workbench_surfaces_vmem_memory_class_mix_in_assets(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_visualization_workbench

    run_root = tmp_path / "run-workbench-memory-class"
    _write_initialized_run(run_root)
    bundle_path = run_root / "reports" / "visualization_bundle.json"
    bundle_path.write_text(
        json.dumps(_bundle(include_sweep=False).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    result = run_visualization_workbench(run_root)

    assert result.status == "completed"
    app_js = (run_root / "workbench" / "assets" / "app.js").read_text(encoding="utf-8")
    assert "Region Memory Class Mix" in app_js
    assert "peak_bytes_by_memory_class" in app_js
    assert "Top Region Memory Classes" in app_js


def _write_initialized_run(run_root: Path) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    for relative in ("artifacts", "reports", "logs", "dumps"):
        (run_root / relative).mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_root.name,
        contract_version="phase-a.v1",
        status="initialized",
        model_path="models/gemma3_1b/model_q4f16.onnx",
        target_profile_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_profile_path="profiles/scenarios/prefill_seq128.json",
        artifact_index={
            "manifest": "manifest.json",
            "artifacts_dir": "artifacts",
            "reports_dir": "reports",
            "logs_dir": "logs",
            "dumps_dir": "dumps",
            "visualization_bundle": "reports/visualization_bundle.json",
        },
    )
    (run_root / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(
            RunSummary(
                run_id=run_root.name,
                status="initialized",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _bundle(*, include_sweep: bool) -> object:
    from llm_sched.contracts.visualization_bundle import VisualizationBundle

    return VisualizationBundle.model_validate(
        {
            "bundle_id": "viz.run-workbench",
            "metadata": {
                "run_id": "run-workbench",
                "graph_id": "gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "mode": "prefill",
                "schedule_kind": "single-core",
                "target_profile_name": "riscv_npu_single_core_v1",
                "target_profile_path": "profiles/targets/riscv_npu_single_core_v1.json",
                "scenario_profile_path": "profiles/scenarios/prefill_seq128.json",
                "run_root": "tmp/run-workbench",
                "sweep_root": "tmp/sweep" if include_sweep else None,
            },
            "view_index": {
                "available_views": ["graph", "timeline", "kv", "vmem", "coverage"]
                + (["sweep"] if include_sweep else []),
                "section_ids": {
                    "graph": "graph_view",
                    "timeline": "timeline_view",
                    "kv": "kv_view",
                    "vmem": "vmem_view",
                    "coverage": "coverage_view",
                    **({"sweep": "sweep_view"} if include_sweep else {}),
                },
            },
            "report_summary": {
                "report_kind": "prefill",
                "primary_metrics": {"estimated_cycles": 4096.0, "tokens_per_cycle": 0.03125},
                "hotspot_macro_ops": ["WDQ_GEMM", "SDPA"],
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
                "core_mode": "single-core",
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
                "kv_formula_count": 1,
                "unresolved_address_count": 0,
                "formulas": [
                    {
                        "node_id": "nig.kv.0",
                        "tensor_kind": "key",
                        "layout": "LBHSD",
                        "formula": "KV_BASE + layer * 1024",
                    }
                ],
            },
            "vmem_view": {
                "max_region_utilization": 0.75,
                "overflow_region_count": 0,
                "regions": [
                    {
                        "region_name": "ping",
                        "capacity_bytes": 65536,
                        "peak_bytes": 49152,
                        "utilization_ratio": 0.75,
                        "fits": True,
                        "peak_bytes_by_memory_class": {
                            "ACTIVATION": 40960,
                            "QUANT_PARAM": 8192,
                        },
                        "peak_bytes_by_backing_store": {
                            "vmem-local": 40960,
                            "ddr-backed-staged": 8192,
                            "ddr-persistent": 0,
                        },
                    }
                ],
                "diagnostics": [],
            },
            "coverage_view": {
                "mapped_descriptor_count": 32,
                "unmapped_block_count": 1,
                "opcode_counts": {"WDQ_GEMM": 16},
                "gap_counts": {"opcode_not_supported": 1},
                "packed_record_count": 2,
                "packed_stream_total_bytes": 192,
                "packed_layout_template_counts": {
                    "dma_load_v1": 1,
                    "core_link_transfer_v1": 1,
                },
                "packed_field_name_counts": {
                    "base_addr": 2,
                    "transfer_kind": 1,
                },
                "issues": [],
            },
            "sweep_view": (
                {
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "comparison_count": 1,
                    "issue_count": 0,
                    "comparisons": [
                        {
                            "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                            "scenario_name": "prefill_seq128",
                            "mode": "prefill",
                            "metric_deltas": {"estimated_cycles": -1024.0},
                            "layer_deltas": [
                                {
                                    "layer_id": 0,
                                    "baseline_cycles": 2048.0,
                                    "candidate_cycles": 1536.0,
                                    "delta_cycles": -512.0,
                                    "baseline_bytes": 65536.0,
                                    "candidate_bytes": 49152.0,
                                    "delta_bytes": -16384.0,
                                }
                            ],
                        }
                    ],
                }
                if include_sweep
                else None
            ),
            "issues": [],
        }
    )
