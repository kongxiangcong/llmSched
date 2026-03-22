from pathlib import Path


def test_build_visualization_workbench_generates_static_assets_with_sweep_panel() -> None:
    from llm_sched.visualization import build_visualization_workbench

    artifact, files = build_visualization_workbench(
        _bundle(include_sweep=True),
        bundle_relative_path="../reports/visualization_bundle.json",
        workbench_root=Path("workbench"),
    )

    assert artifact.entry_html_path == "workbench/index.html"
    assert artifact.bundle_path == "../reports/visualization_bundle.json"
    assert artifact.default_panel == "summary"
    assert "sweep" in artifact.available_panels
    assert set(files) == {
        "workbench/index.html",
        "workbench/assets/app.js",
        "workbench/assets/styles.css",
        "workbench/workbench_manifest.json",
    }
    assert "Gemma3 Prefill / Single Core" in files["workbench/index.html"]
    assert "data-panel=\"graph\"" in files["workbench/index.html"]
    assert "data-panel=\"sweep\"" in files["workbench/index.html"]
    assert "graph-search-input" in files["workbench/index.html"]
    assert "timeline-stage-filter" in files["workbench/index.html"]
    assert "timeline-core-filter" in files["workbench/index.html"]
    assert "timeline-detail-panel" in files["workbench/index.html"]
    assert "memory-search-input" in files["workbench/index.html"]
    assert "coverage-search-input" in files["workbench/index.html"]
    assert "copy-view-link-button" in files["workbench/index.html"]
    assert "download-view-json-button" in files["workbench/index.html"]
    assert "download-panel-svg-button" in files["workbench/index.html"]
    assert "workbench-action-status" in files["workbench/index.html"]
    assert "back-to-catalog-link" in files["workbench/index.html"]
    assert 'id="visualization-bundle-data"' in files["workbench/index.html"]
    assert '"bundle_id":"viz.run-prefill-001"' in files["workbench/index.html"]
    assert "../reports/visualization_bundle.json" in files["workbench/assets/app.js"]
    assert "function readEmbeddedBundle" in files["workbench/assets/app.js"]
    assert "function loadBundle" in files["workbench/assets/app.js"]
    assert 'document.querySelector("#visualization-bundle-data")' in files["workbench/assets/app.js"]
    assert "const embeddedBundle = readEmbeddedBundle();" in files["workbench/assets/app.js"]
    assert "const response = await fetch(BUNDLE_PATH);" in files["workbench/assets/app.js"]
    assert "function serializeUiState" in files["workbench/assets/app.js"]
    assert "function buildCurrentViewUrl" in files["workbench/assets/app.js"]
    assert "function updateCatalogReturnLink" in files["workbench/assets/app.js"]
    assert "function copyCurrentViewLink" in files["workbench/assets/app.js"]
    assert "function downloadCurrentViewJson" in files["workbench/assets/app.js"]
    assert "function buildPanelExportData" in files["workbench/assets/app.js"]
    assert "function buildPanelSnapshotLines" in files["workbench/assets/app.js"]
    assert "function buildPanelSnapshotTitle" in files["workbench/assets/app.js"]
    assert "function renderPanelSnapshotHeader" in files["workbench/assets/app.js"]
    assert "function escapeSvgText" in files["workbench/assets/app.js"]
    assert "function buildPanelSnapshotSvg" in files["workbench/assets/app.js"]
    assert "function slugifyFileSegment" in files["workbench/assets/app.js"]
    assert "function buildPanelExportFilename" in files["workbench/assets/app.js"]
    assert "function downloadCurrentPanelSvg" in files["workbench/assets/app.js"]
    assert "function buildPanelLink" in files["workbench/assets/app.js"]
    assert "function groupedCompareGroupIdsForFocus" in files["workbench/assets/app.js"]
    assert "function focusedGroupedScalarDeltaGroups" in files["workbench/assets/app.js"]
    assert "function filterCoverageIssues" in files["workbench/assets/app.js"]
    assert "function filterGraphNodes" in files["workbench/assets/app.js"]
    assert "function filterTimelineBlocks" in files["workbench/assets/app.js"]
    assert "function renderTimelineDetail" in files["workbench/assets/app.js"]
    assert "URLSearchParams(window.location.search)" in files["workbench/assets/app.js"]
    assert "function hydrateStateFromUrl" in files["workbench/assets/app.js"]
    assert "catalog_return" in files["workbench/assets/app.js"]
    assert "compare_focus" in files["workbench/assets/app.js"]
    assert "layer_delta_focus" in files["workbench/assets/app.js"]
    assert "analysis_flow" in files["workbench/assets/app.js"]
    assert "sweep_candidate" in files["workbench/assets/app.js"]
    assert "sweep_layer_focus" in files["workbench/assets/app.js"]
    assert "recommendation_queue_position" in files["workbench/assets/app.js"]
    assert "recommendation_prev_candidate" in files["workbench/assets/app.js"]
    assert "recommendation_next_candidate" in files["workbench/assets/app.js"]
    assert "recommendation_top_candidates" in files["workbench/assets/app.js"]
    assert "memory_query" in files["workbench/assets/app.js"]
    assert "coverage_query" in files["workbench/assets/app.js"]
    assert "detail_block" in files["workbench/assets/app.js"]
    assert "timeline_stage" in files["workbench/assets/app.js"]
    assert "timeline_core" in files["workbench/assets/app.js"]
    assert "Back to Catalog Compare" in files["workbench/assets/app.js"]
    assert "Open Coverage" in files["workbench/assets/app.js"]
    assert "Open Timeline" in files["workbench/assets/app.js"]
    assert "Saved view link copied." in files["workbench/assets/app.js"]
    assert "Export current panel JSON" in files["workbench/index.html"]
    assert "Export current panel SVG" in files["workbench/index.html"]
    assert "const initialPanel = resolveInitialPanel" in files["workbench/assets/app.js"]
    assert "graph-search-input" in files["workbench/assets/app.js"]
    assert "timeline-detail-panel" in files["workbench/assets/app.js"]
    assert "Packed Descriptor Summary" in files["workbench/assets/app.js"]
    assert "Packed Layout Templates" in files["workbench/assets/app.js"]
    assert "Packed Field Placements" in files["workbench/assets/app.js"]
    assert "packed_record_count" in files["workbench/assets/app.js"]
    assert "packed_stream_total_bytes" in files["workbench/assets/app.js"]
    assert "packed_layout_template_counts" in files["workbench/assets/app.js"]
    assert "packed_field_name_counts" in files["workbench/assets/app.js"]
    assert "Layer Deltas" in files["workbench/assets/app.js"]
    assert "layer_deltas" in files["workbench/assets/app.js"]
    assert "fitted_layer_deltas" in files["workbench/assets/app.js"]
    assert "delta_cycles" in files["workbench/assets/app.js"]
    assert "delta_fitted_work_cycles" in files["workbench/assets/app.js"]
    assert "compare_summary" in files["workbench/assets/app.js"]
    assert "baseline_schedule_kind" in files["workbench/assets/app.js"]
    assert "profile_diff_fields" in files["workbench/assets/app.js"]
    assert "highlighted_scalar_deltas" in files["workbench/assets/app.js"]
    assert "bandwidth_pressure_compare" in files["workbench/assets/app.js"]
    assert "vmem_pressure_compare" in files["workbench/assets/app.js"]
    assert "function renderPressureCompareSummary" in files["workbench/assets/app.js"]
    assert "Peak Bandwidth Pressure" in files["workbench/assets/app.js"]
    assert "VMEM Pressure Shifts" in files["workbench/assets/app.js"]
    assert "Highlighted Metric Shifts" in files["workbench/assets/app.js"]
    assert "scalar_delta_groups" in files["workbench/assets/app.js"]
    assert "function scalarDeltaIsPositive" in files["workbench/assets/app.js"]
    assert "scalarDeltaIsPositive(scalarDelta.metric_name, deltaValue)" in files["workbench/assets/app.js"]
    assert "scalarDeltaIsPositive(metricName, deltaValue)" in files["workbench/assets/app.js"]
    assert "function buildDirectionTagMarkup" in files["workbench/assets/app.js"]
    assert 'buildDirectionTagMarkup("is-positive", "candidate faster")' in files["workbench/assets/app.js"]
    assert "function buildScalarDeltaDirectionTag" in files["workbench/assets/app.js"]
    assert "buildScalarDeltaDirectionTag(scalarDelta)" in files["workbench/assets/app.js"]
    assert "function renderScalarDeltaGroups" in files["workbench/assets/app.js"]
    assert "const MAX_GROUPED_COMPARE_ROWS = 3" in files["workbench/assets/app.js"]
    assert "function orderedGroupedScalarDeltas" in files["workbench/assets/app.js"]
    assert "function buildGroupedScalarDirectionTag" in files["workbench/assets/app.js"]
    assert "function renderGroupedScalarDeltaSection" in files["workbench/assets/app.js"]
    assert "Math.abs(Number(right.delta_ratio || 0))" in files["workbench/assets/app.js"]
    assert "Math.abs(Number(right.delta_value || 0))" in files["workbench/assets/app.js"]
    assert "orderedGroupedScalarDeltas(group.scalar_deltas || [])" in files["workbench/assets/app.js"]
    assert 'direction-tag is-positive' in files["workbench/assets/app.js"]
    assert 'direction-tag is-negative' in files["workbench/assets/app.js"]
    assert 'direction-tag is-neutral' in files["workbench/assets/app.js"]
    assert 'direction-tag is-up' not in files["workbench/assets/app.js"]
    assert 'direction-tag is-down' not in files["workbench/assets/app.js"]
    assert 'direction-tag is-positive">improved<' in files["workbench/assets/app.js"]
    assert 'direction-tag is-negative">regressed<' in files["workbench/assets/app.js"]
    assert 'direction-tag is-neutral">steady<' in files["workbench/assets/app.js"]
    assert "candidate faster" in files["workbench/assets/app.js"]
    assert "candidate slower" in files["workbench/assets/app.js"]
    assert "pressure up" in files["workbench/assets/app.js"]
    assert "pressure down" in files["workbench/assets/app.js"]
    assert "buildGroupedScalarDirectionTag(group, scalarDeltas)" in files["workbench/assets/app.js"]
    assert "Show all " in files["workbench/assets/app.js"]
    assert "group.title || group.group_id" in files["workbench/assets/app.js"]
    assert "scalar_deltas" in files["workbench/assets/app.js"]
    assert "function buildSweepExportData" in files["workbench/assets/app.js"]
    assert "function buildSweepSnapshotMetadata" in files["workbench/assets/app.js"]
    assert "function currentAnalysisFlow" in files["workbench/assets/app.js"]
    assert "function resolveAnalysisFlowState" in files["workbench/assets/app.js"]
    assert "function orderedSweepLayerDeltas" in files["workbench/assets/app.js"]
    assert "snapshot_metadata" in files["workbench/assets/app.js"]
    assert "header_rows" in files["workbench/assets/app.js"]
    assert "focused_analysis_flow" in files["workbench/assets/app.js"]
    assert "focused_analysis_flow_summary" in files["workbench/assets/app.js"]
    assert "focused_compare_focus" in files["workbench/assets/app.js"]
    assert "focused_layer_delta_mode" in files["workbench/assets/app.js"]
    assert "focused_sweep_candidate" in files["workbench/assets/app.js"]
    assert "focused_sweep_layer" in files["workbench/assets/app.js"]
    assert "focused_recommendation_queue" in files["workbench/assets/app.js"]
    assert "focused_comparison_count" in files["workbench/assets/app.js"]
    assert "focused_layer_delta_count" in files["workbench/assets/app.js"]
    assert "focused_layer_delta_summary" in files["workbench/assets/app.js"]
    assert "Snapshot Focus" in files["workbench/assets/app.js"]
    assert "Analysis Workflow" in files["workbench/assets/app.js"]
    assert "Recommendation Queue" in files["workbench/assets/app.js"]
    assert "Top Recommended Candidates" in files["workbench/assets/app.js"]
    assert "Top Recommendation Compare Strip" in files["workbench/assets/app.js"]
    assert "Top Recommended Candidate Comparisons" in files["workbench/assets/app.js"]
    assert "Recommendation Detail Blocks" in files["workbench/assets/app.js"]
    assert "Side-by-Side Candidate Detail" in files["workbench/assets/app.js"]
    assert "Previous Recommended Candidate" in files["workbench/assets/app.js"]
    assert "Next Recommended Candidate" in files["workbench/assets/app.js"]
    assert "Open Top Recommendation" in files["workbench/assets/app.js"]
    assert "Focused Analysis Workflow" in files["workbench/assets/app.js"]
    assert "Focused Compare Focus" in files["workbench/assets/app.js"]
    assert "Focused Layer Delta Mode" in files["workbench/assets/app.js"]
    assert "Baseline Sweep Target" in files["workbench/assets/app.js"]
    assert "Focused Comparisons" in files["workbench/assets/app.js"]
    assert "Focused Layer Deltas" in files["workbench/assets/app.js"]
    assert "function currentRecommendationQueueState" in files["workbench/assets/app.js"]
    assert "function buildRecommendationQueuePanelLink" in files["workbench/assets/app.js"]
    assert "function buildSweepRecommendationQueueSummary" in files["workbench/assets/app.js"]
    assert "function buildTopRecommendationComparisonCards" in files["workbench/assets/app.js"]
    assert "function renderTopRecommendationComparisonCard" in files["workbench/assets/app.js"]
    assert "function buildTopRecommendationDetailBlocks" in files["workbench/assets/app.js"]
    assert "function renderRecommendationDetailBlock" in files["workbench/assets/app.js"]
    assert "focused_recommendation_details" in files["workbench/assets/app.js"]
    assert "Top Recommendation Detail Candidates" in files["workbench/assets/app.js"]
    assert "function buildRecommendationDetailEntries" in files["workbench/assets/app.js"]
    assert "function buildRecommendationDetailLayerSummary" in files["workbench/assets/app.js"]
    assert "function buildRecommendationDetailSnapshotLines" in files["workbench/assets/app.js"]
    assert "function renderRecommendationDetailEntryMarkup" in files["workbench/assets/app.js"]
    assert "recommendation-strip" in files["workbench/assets/styles.css"]
    assert "recommendation-detail-grid" in files["workbench/assets/styles.css"]
    assert "Focused Layer Summary" in files["workbench/assets/app.js"]
    assert "Focused Fitted Layer Deltas" in files["workbench/assets/app.js"]
    assert "Focused Fitted Layer Summary" in files["workbench/assets/app.js"]
    assert "Focused Sweep Layer" in files["workbench/assets/app.js"]
    assert "focused-sweep-row" in files["workbench/assets/app.js"]
    assert "Summary Focus" in files["workbench/assets/app.js"]
    assert "Throughput / Latency Focus" in files["workbench/assets/app.js"]
    assert "Phase Shape Focus" in files["workbench/assets/app.js"]
    assert "Top By Fitted Work" in files["workbench/assets/app.js"]
    assert 'groupedCompareGroupIdsForFocus(UI_STATE.compareFocus)' in files["workbench/assets/app.js"]


def test_build_visualization_workbench_omits_sweep_panel_when_bundle_has_no_sweep() -> None:
    from llm_sched.visualization import build_visualization_workbench

    artifact, files = build_visualization_workbench(
        _bundle(include_sweep=False),
        bundle_relative_path="../reports/visualization_bundle.json",
        workbench_root=Path("workbench"),
    )

    assert "sweep" not in artifact.available_panels
    assert "data-panel=\"sweep\"" not in files["workbench/index.html"]


def test_build_visualization_workbench_renders_vmem_backing_store_mix_in_memory_panel() -> None:
    from llm_sched.visualization import build_visualization_workbench

    _artifact, files = build_visualization_workbench(
        _bundle(include_sweep=False),
        bundle_relative_path="../reports/visualization_bundle.json",
        workbench_root=Path("workbench"),
    )

    assert "Region Backing Store Mix" in files["workbench/assets/app.js"]
    assert "peak_bytes_by_backing_store" in files["workbench/assets/app.js"]
    assert "Top Region Backing Stores" in files["workbench/assets/app.js"]


def test_build_visualization_workbench_renders_vmem_memory_class_mix_in_memory_panel() -> None:
    from llm_sched.visualization import build_visualization_workbench

    _artifact, files = build_visualization_workbench(
        _bundle(include_sweep=False),
        bundle_relative_path="../reports/visualization_bundle.json",
        workbench_root=Path("workbench"),
    )

    assert "Region Memory Class Mix" in files["workbench/assets/app.js"]
    assert "peak_bytes_by_memory_class" in files["workbench/assets/app.js"]
    assert "Top Region Memory Classes" in files["workbench/assets/app.js"]


def test_build_visualization_workbench_supports_coverage_focus_deep_links() -> None:
    from llm_sched.visualization import build_visualization_workbench

    _artifact, files = build_visualization_workbench(
        _bundle(include_sweep=False),
        bundle_relative_path="../reports/visualization_bundle.json",
        workbench_root=Path("workbench"),
    )

    assert "coverage_focus" in files["workbench/assets/app.js"]
    assert "function scrollCoverageFocusIntoView" in files["workbench/assets/app.js"]
    assert 'data-coverage-focus-target="packed-descriptor"' in files["workbench/assets/app.js"]
    assert "is-focused" in files["workbench/assets/styles.css"]


def test_build_visualization_workbench_escapes_embedded_bundle_script_boundaries() -> None:
    from llm_sched.visualization import build_visualization_workbench

    bundle = _bundle(include_sweep=False)
    bundle.graph_view.nodes[0].label = "</script><div>unsafe</div>"

    _artifact, files = build_visualization_workbench(
        bundle,
        bundle_relative_path="../reports/visualization_bundle.json",
        workbench_root=Path("workbench"),
    )

    assert "</script><div>unsafe</div>" not in files["workbench/index.html"]
    assert "\\u003c/script>\\u003cdiv>unsafe\\u003c/div>" in files["workbench/index.html"]


def _bundle(*, include_sweep: bool) -> object:
    from llm_sched.contracts.visualization_bundle import VisualizationBundle

    return VisualizationBundle.model_validate(
        {
            "bundle_id": "viz.run-prefill-001",
            "metadata": {
                "run_id": "run-prefill-001",
                "graph_id": "gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "mode": "prefill",
                "schedule_kind": "single-core",
                "target_profile_name": "riscv_npu_single_core_v1",
                "target_profile_path": "profiles/targets/riscv_npu_single_core_v1.json",
                "scenario_profile_path": "profiles/scenarios/prefill_seq128.json",
                "run_root": "tmp/run-prefill-001",
                "sweep_root": "tmp/sweep-phase-d" if include_sweep else None,
            },
            "view_index": {
                "available_views": ["graph", "timeline", "kv", "vmem", "coverage"] + (["sweep"] if include_sweep else []),
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
                        "node_id": "nig.linear.0",
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
                "issues": [
                    {
                        "schedule_block_id": "sched.0",
                        "requested_opcode": "WDQ_GEMM",
                        "code": "opcode_not_supported",
                        "message": "Descriptor opcode is not available on the current ISA profile.",
                    }
                ],
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
                            "compare_summary": {
                                "baseline_schedule_kind": "single-core",
                                "candidate_schedule_kind": "dual-core",
                                "profile_diff_fields": ["core_mode", "num_cores"],
                                "highlighted_scalar_deltas": [
                                    {
                                        "metric_name": "estimated_cycles",
                                        "baseline_value": 4096.0,
                                        "candidate_value": 3072.0,
                                        "delta_value": -1024.0,
                                        "delta_ratio": -0.25,
                                    },
                                    {
                                        "metric_name": "tokens_per_cycle",
                                        "baseline_value": 0.03125,
                                        "candidate_value": 0.0416666667,
                                        "delta_value": 0.0104166667,
                                        "delta_ratio": 0.3333333344,
                                    },
                                ],
                                "scalar_deltas": [
                                    {
                                        "metric_name": "estimated_cycles",
                                        "baseline_value": 4096.0,
                                        "candidate_value": 3072.0,
                                        "delta_value": -1024.0,
                                        "delta_ratio": -0.25,
                                    },
                                {
                                    "metric_name": "tokens_per_cycle",
                                    "baseline_value": 0.03125,
                                    "candidate_value": 0.0416666667,
                                    "delta_value": 0.0104166667,
                                    "delta_ratio": 0.3333333344,
                                },
                            ],
                            "scalar_delta_groups": [
                                {
                                    "group_id": "headline",
                                    "title": "Headline",
                                    "scalar_deltas": [
                                        {
                                            "metric_name": "estimated_cycles",
                                            "baseline_value": 4096.0,
                                            "candidate_value": 3072.0,
                                            "delta_value": -1024.0,
                                            "delta_ratio": -0.25,
                                        }
                                    ],
                                },
                                {
                                    "group_id": "throughput_latency",
                                    "title": "Throughput / Latency",
                                    "scalar_deltas": [
                                        {
                                            "metric_name": "tokens_per_cycle",
                                            "baseline_value": 0.03125,
                                            "candidate_value": 0.0416666667,
                                            "delta_value": 0.0104166667,
                                            "delta_ratio": 0.3333333344,
                                        }
                                    ],
                                },
                            ],
                            "bandwidth_pressure_compare": {
                                "peak_bandwidth_pressure": {
                                    "metric_name": "peak_bandwidth_pressure",
                                    "baseline_value": 640.0,
                                    "candidate_value": 512.0,
                                    "delta_value": -128.0,
                                    "delta_ratio": -0.2,
                                },
                                "peak_pressure_subject_id": {
                                    "baseline_value": "nig.node.sdpa.0",
                                    "candidate_value": "nig.node.linear.0",
                                    "changed": True,
                                },
                            },
                            "vmem_pressure_compare": {
                                "hottest_region": {
                                    "baseline_value": "ping",
                                    "candidate_value": "pong",
                                    "changed": True,
                                },
                                "hottest_region_utilization": {
                                    "metric_name": "hottest_region_utilization",
                                    "baseline_value": 0.75,
                                    "candidate_value": 0.625,
                                    "delta_value": -0.125,
                                    "delta_ratio": -0.1666666667,
                                },
                            },
                        },
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
                            "fitted_layer_deltas": [
                                {
                                    "layer_id": 0,
                                    "baseline_fitted_work_cycles": 1792.0,
                                    "candidate_fitted_work_cycles": 1280.0,
                                    "delta_fitted_work_cycles": -512.0,
                                    "baseline_fitted_cycle_share": 0.7,
                                    "candidate_fitted_cycle_share": 0.625,
                                    "delta_fitted_cycle_share": -0.075,
                                    "delta_fitted_work_cycles_ratio": -0.2857142857,
                                    "baseline_bytes": 65536.0,
                                    "candidate_bytes": 49152.0,
                                    "delta_bytes": -16384.0,
                                    "delta_bytes_ratio": -0.25,
                                    "change_direction": "down",
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
