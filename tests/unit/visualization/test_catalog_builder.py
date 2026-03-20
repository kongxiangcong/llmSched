from pathlib import Path


def test_build_visualization_catalog_generates_static_index_assets() -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogEntry
    from llm_sched.visualization import build_visualization_catalog

    artifact, files = build_visualization_catalog(
        catalog_id="catalog.phase-e",
        title="Phase E Catalog",
        entries=[
            VisualizationCatalogEntry(
                entry_id="run.prefill.single",
                run_id="run-prefill-single",
                scenario_name="prefill_seq128",
                mode="prefill",
                schedule_kind="single-core",
                target_profile_name="riscv_npu_single_core_v1",
                primary_metric_name="estimated_cycles",
                primary_metric_value=4096.0,
                metric_values={
                    "estimated_cycles": 4096.0,
                    "tokens_per_cycle": 0.03125,
                },
                sweep_baseline_target_profile_name="riscv_npu_single_core_v1",
                sweep_comparisons=[
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
                                "layer_id": 2,
                                "baseline_cycles": 1024.0,
                                "candidate_cycles": 896.0,
                                "delta_cycles": -128.0,
                                "baseline_bytes": 32768.0,
                                "candidate_bytes": 30720.0,
                                "delta_bytes": -2048.0,
                            },
                            {
                                "layer_id": 0,
                                "baseline_cycles": 2048.0,
                                "candidate_cycles": 1536.0,
                                "delta_cycles": -512.0,
                                "baseline_bytes": 65536.0,
                                "candidate_bytes": 49152.0,
                                "delta_bytes": -16384.0,
                            },
                            {
                                "layer_id": 3,
                                "baseline_cycles": 1536.0,
                                "candidate_cycles": 1280.0,
                                "delta_cycles": -256.0,
                                "baseline_bytes": 49152.0,
                                "candidate_bytes": 45056.0,
                                "delta_bytes": -4096.0,
                            },
                            {
                                "layer_id": 1,
                                "baseline_cycles": 768.0,
                                "candidate_cycles": 640.0,
                                "delta_cycles": -128.0,
                                "baseline_bytes": 24576.0,
                                "candidate_bytes": 22528.0,
                                "delta_bytes": -2048.0,
                            }
                        ],
                        "fitted_layer_deltas": [
                            {
                                "layer_id": 3,
                                "baseline_fitted_work_cycles": 1408.0,
                                "candidate_fitted_work_cycles": 1088.0,
                                "delta_fitted_work_cycles": -320.0,
                                "baseline_fitted_cycle_share": 0.22,
                                "candidate_fitted_cycle_share": 0.19,
                                "delta_fitted_cycle_share": -0.03,
                                "delta_fitted_work_cycles_ratio": -0.2272727273,
                                "baseline_bytes": 49152.0,
                                "candidate_bytes": 45056.0,
                                "delta_bytes": -4096.0,
                                "delta_bytes_ratio": -0.0833333333,
                                "change_direction": "down",
                            },
                            {
                                "layer_id": 0,
                                "baseline_fitted_work_cycles": 1792.0,
                                "candidate_fitted_work_cycles": 1280.0,
                                "delta_fitted_work_cycles": -512.0,
                                "baseline_fitted_cycle_share": 0.28,
                                "candidate_fitted_cycle_share": 0.225,
                                "delta_fitted_cycle_share": -0.055,
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
                workbench_entry_path="../run-prefill-single/workbench/index.html",
            ),
            VisualizationCatalogEntry(
                entry_id="run.decode.dual",
                run_id="run-decode-dual",
                scenario_name="decode_token1_kv2048",
                mode="decode",
                schedule_kind="dual-core",
                target_profile_name="riscv_npu_dual_core_v1",
                primary_metric_name="token_latency_cycles",
                primary_metric_value=512.0,
                metric_values={
                    "token_latency_cycles": 512.0,
                    "tokens_per_second": 1953.125,
                },
                workbench_entry_path="../run-decode-dual/workbench/index.html",
            ),
        ],
        catalog_root=Path("catalog"),
    )

    assert artifact.catalog_id == "catalog.phase-e"
    assert artifact.metadata.entry_count == 2
    assert set(files) == {
        "catalog/index.html",
        "catalog/assets/app.js",
        "catalog/assets/styles.css",
        "catalog/catalog_manifest.json",
    }
    assert "Phase E Catalog" in files["catalog/index.html"]
    assert "catalog-search-input" in files["catalog/index.html"]
    assert "catalog-mode-filter" in files["catalog/index.html"]
    assert "catalog-schedule-filter" in files["catalog/index.html"]
    assert "catalog-group-nav" in files["catalog/index.html"]
    assert "catalog-group-sections" in files["catalog/index.html"]
    assert "catalog-compare-tray" in files["catalog/index.html"]
    assert "catalog-compare-workspace" in files["catalog/index.html"]
    assert "catalog-compare-workspace-content" in files["catalog/index.html"]
    assert "copy-workspace-link-button" in files["catalog/index.html"]
    assert "download-workspace-json-button" in files["catalog/index.html"]
    assert "download-workspace-svg-button" in files["catalog/index.html"]
    assert "catalog-workspace-action-status" in files["catalog/index.html"]
    assert "catalog-compare-scope-filter" in files["catalog/index.html"]
    assert "catalog-workbench-panel-filter" in files["catalog/index.html"]
    assert "catalog-layer-delta-focus-filter" in files["catalog/index.html"]
    assert "swap-compare-order-button" in files["catalog/index.html"]
    assert "compare-toggle" in files["catalog/index.html"]
    assert "../run-prefill-single/workbench/index.html" in files["catalog/index.html"]
    assert "../run-prefill-single/workbench/index.html?panel=timeline" in files["catalog/index.html"]
    assert "../run-prefill-single/workbench/index.html?panel=memory" in files["catalog/index.html"]
    assert "../run-prefill-single/workbench/index.html?panel=coverage" in files["catalog/index.html"]
    assert "group-link-row" in files["catalog/index.html"]
    assert "function toggleCompareSelection" in files["catalog/assets/app.js"]
    assert "function buildCompareSummary" in files["catalog/assets/app.js"]
    assert "function renderCompareTray" in files["catalog/assets/app.js"]
    assert "function swapCompareSelectionOrder" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceCandidateSet" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceCompareRows" in files["catalog/assets/app.js"]
    assert "function renderCompareWorkspace" in files["catalog/assets/app.js"]
    assert "function buildCurrentCatalogWorkspaceUrl" in files["catalog/assets/app.js"]
    assert "function copyCurrentWorkspaceLink" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceExportData" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceSnapshotSvg" in files["catalog/assets/app.js"]
    assert "function downloadCurrentWorkspaceJson" in files["catalog/assets/app.js"]
    assert "function downloadCurrentWorkspaceSvg" in files["catalog/assets/app.js"]
    assert "function bindCatalogWorkspaceActions" in files["catalog/assets/app.js"]
    assert "function currentWorkbenchPanel" in files["catalog/assets/app.js"]
    assert "function buildComparePanelLinks" in files["catalog/assets/app.js"]
    assert "function currentLayerDeltaFocus" in files["catalog/assets/app.js"]
    assert "function selectSweepLayerDeltas" in files["catalog/assets/app.js"]
    assert "function serializeCatalogState" in files["catalog/assets/app.js"]
    assert "function hydrateCatalogStateFromUrl" in files["catalog/assets/app.js"]
    assert "layer_delta_focus" in files["catalog/assets/app.js"]
    assert "sweep_candidate" in files["catalog/assets/app.js"]
    assert "sweep_layer_focus" in files["catalog/assets/app.js"]
    assert "catalog_return" in files["catalog/assets/app.js"]
    assert "compare_ids" in files["catalog/assets/app.js"]
    assert "Open Selected Panel" in files["catalog/assets/app.js"]
    assert "function buildSharedMetricDeltaRows" in files["catalog/assets/app.js"]
    assert "function resolveSweepComparison" in files["catalog/assets/app.js"]
    assert "function renderSweepLayerDeltaRows" in files["catalog/assets/app.js"]
    assert "function orderedSweepLayerDeltas" in files["catalog/assets/app.js"]
    assert "function buildSweepDrilldownLink" in files["catalog/assets/app.js"]
    assert "function buildSweepLayerDrilldownLink" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceCompareSummaryTag" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceCompareRatioSummaryTag" in files["catalog/assets/app.js"]
    assert "function resolveWorkspacePrimaryScalarDelta" in files["catalog/assets/app.js"]
    assert "function resolveWorkspaceSweepSummaryState" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceSweepSummaryTag" in files["catalog/assets/app.js"]
    assert "workspaceSummaryTag: buildWorkspaceCompareSummaryTag(baselineEntry, candidateEntry)," in files["catalog/assets/app.js"]
    assert "workspaceRatioSummaryTag: buildWorkspaceCompareRatioSummaryTag(baselineEntry, candidateEntry)," in files["catalog/assets/app.js"]
    assert "workspaceSweepSummaryTag: buildWorkspaceSweepSummaryTag(sweepComparison)," in files["catalog/assets/app.js"]
    assert "function buildWorkspaceSweepSummaryContent" in files["catalog/assets/app.js"]
    assert "function renderWorkspaceCompareDrilldownSection" in files["catalog/assets/app.js"]
    assert "function buildWorkspaceCompareDrilldownContent" in files["catalog/assets/app.js"]
    assert "function buildWorkspacePrimaryDeltaContent" in files["catalog/assets/app.js"]
    assert "function buildWorkspacePrimaryRatioContent" in files["catalog/assets/app.js"]
    assert "function renderWorkspaceSummaryCell" in files["catalog/assets/app.js"]
    assert "function renderWorkspaceSummaryStack" in files["catalog/assets/app.js"]
    assert "renderWorkspaceSummaryStack(" in files["catalog/assets/app.js"]
    assert 'class="summary-stack"' in files["catalog/assets/app.js"]
    assert 'class="summary-stack-value"' in files["catalog/assets/app.js"]
    assert "MAX_SWEEP_LAYER_DELTA_ROWS" in files["catalog/assets/app.js"]
    assert "regressions-only" in files["catalog/assets/app.js"]
    assert "top-by-bytes" in files["catalog/assets/app.js"]
    assert "top-by-fitted-work" in files["catalog/assets/app.js"]
    assert "fitted-regressions-only" in files["catalog/assets/app.js"]
    assert "Shared Metric Deltas" in files["catalog/assets/app.js"]
    assert "Sweep Layer Deltas" in files["catalog/assets/app.js"]
    assert "Candidate Regressions" in files["catalog/assets/app.js"]
    assert "Top By Bytes" in files["catalog/assets/app.js"]
    assert "Top By Fitted Work" in files["catalog/assets/app.js"]
    assert "Fitted Work Regressions" in files["catalog/assets/app.js"]
    assert "Showing top 3 of" in files["catalog/assets/app.js"]
    assert "|delta_cycles|" in files["catalog/assets/app.js"]
    assert "|delta_bytes|" in files["catalog/assets/app.js"]
    assert "|delta_fitted_work_cycles|" in files["catalog/assets/app.js"]
    assert "fitted_layer_deltas" in files["catalog/assets/app.js"]
    assert "Workspace Compare Drilldown" in files["catalog/assets/app.js"]
    assert "Focused Layer Delta Mode" in files["catalog/assets/app.js"]
    assert "Focused Compare Scope" in files["catalog/assets/app.js"]
    assert "Focused Baseline" in files["catalog/assets/app.js"]
    assert "Focused Candidate Count" in files["catalog/assets/app.js"]
    assert "Focused Sweep Candidate" in files["catalog/assets/app.js"]
    assert "Focused Sweep Layer" in files["catalog/assets/app.js"]
    assert "Grouped Metric Deltas" in files["catalog/assets/app.js"]
    assert "Estimated Layer Deltas" in files["catalog/assets/app.js"]
    assert "Fitted Layer Deltas" in files["catalog/assets/app.js"]
    assert "Exported workspace JSON." in files["catalog/assets/app.js"]
    assert "Exported workspace SVG." in files["catalog/assets/app.js"]
    assert "Workspace view link copied." in files["catalog/assets/app.js"]
    assert "Open Sweep Panel" in files["catalog/assets/app.js"]
    assert "Open Layer In Sweep" in files["catalog/assets/app.js"]
    assert "metric_values" in files["catalog/assets/app.js"]
    assert "sweep_comparisons" in files["catalog/assets/app.js"]
    assert "compare_summary" in files["catalog/assets/app.js"]
    assert "baseline_schedule_kind" in files["catalog/assets/app.js"]
    assert "profile_diff_fields" in files["catalog/assets/app.js"]
    assert "highlighted_scalar_deltas" in files["catalog/assets/app.js"]
    assert "bandwidth_pressure_compare" in files["catalog/assets/app.js"]
    assert "vmem_pressure_compare" in files["catalog/assets/app.js"]
    assert "function renderPressureCompareSummary" in files["catalog/assets/app.js"]
    assert "Peak Bandwidth Pressure" in files["catalog/assets/app.js"]
    assert "VMEM Pressure Shifts" in files["catalog/assets/app.js"]
    assert "Highlighted Metric Shifts" in files["catalog/assets/app.js"]
    assert "scalar_delta_groups" in files["catalog/assets/app.js"]
    assert "function scalarDeltaIsPositive" in files["catalog/assets/app.js"]
    assert "scalarDeltaIsPositive(scalarDelta.metric_name, deltaValue)" in files["catalog/assets/app.js"]
    assert "scalarDeltaIsPositive(metricName, deltaValue)" in files["catalog/assets/app.js"]
    assert "function buildDirectionTagMarkup" in files["catalog/assets/app.js"]
    assert 'buildDirectionTagMarkup("is-positive", "candidate faster")' in files["catalog/assets/app.js"]
    assert "function buildTitledDirectionTagMarkup" in files["catalog/assets/app.js"]
    assert "function buildTitledScalarDeltaDirectionTag" in files["catalog/assets/app.js"]
    assert "function buildScalarDeltaDirectionTag" in files["catalog/assets/app.js"]
    assert "buildScalarDeltaDirectionTag(scalarDelta)" in files["catalog/assets/app.js"]
    assert "function renderScalarDeltaGroups" in files["catalog/assets/app.js"]
    assert "const MAX_GROUPED_COMPARE_ROWS = 3" in files["catalog/assets/app.js"]
    assert "function orderedGroupedScalarDeltas" in files["catalog/assets/app.js"]
    assert "function buildGroupedScalarDirectionTag" in files["catalog/assets/app.js"]
    assert "function renderGroupedScalarDeltaSection" in files["catalog/assets/app.js"]
    assert "Math.abs(Number(right.delta_ratio || 0))" in files["catalog/assets/app.js"]
    assert "Math.abs(Number(right.delta_value || 0))" in files["catalog/assets/app.js"]
    assert "orderedGroupedScalarDeltas(group.scalar_deltas || [])" in files["catalog/assets/app.js"]
    assert 'direction-tag is-positive' in files["catalog/assets/app.js"]
    assert 'direction-tag is-negative' in files["catalog/assets/app.js"]
    assert 'direction-tag is-neutral' in files["catalog/assets/app.js"]
    assert 'direction-tag is-up' not in files["catalog/assets/app.js"]
    assert 'direction-tag is-down' not in files["catalog/assets/app.js"]
    assert 'direction-tag is-positive">improved<' in files["catalog/assets/app.js"]
    assert 'direction-tag is-negative">regressed<' in files["catalog/assets/app.js"]
    assert 'direction-tag is-neutral">steady<' in files["catalog/assets/app.js"]
    assert 'workspace summary' in files["catalog/assets/app.js"]
    assert 'workspace ratio summary' in files["catalog/assets/app.js"]
    assert 'workspace sweep summary' in files["catalog/assets/app.js"]
    assert "function resolveWorkspaceCompareRowState" in files["catalog/assets/app.js"]
    assert 'const rowState = resolveWorkspaceCompareRowState(baselineEntry, entry);' in files["catalog/assets/app.js"]
    assert "sameMetric," in files["catalog/assets/app.js"]
    assert "delta," in files["catalog/assets/app.js"]
    assert "ratio," in files["catalog/assets/app.js"]
    assert "sweepComparison," in files["catalog/assets/app.js"]
    assert 'resolveWorkspacePrimaryScalarDelta(baselineEntry, candidateEntry)' in files["catalog/assets/app.js"]
    assert 'resolveWorkspaceSweepSummaryState(sweepComparison)' in files["catalog/assets/app.js"]
    assert 'const sweepComparison = rowState.sweepComparison;' in files["catalog/assets/app.js"]
    assert 'buildWorkspaceSweepSummaryContent(baselineEntry, entry, sweepComparison)' in files["catalog/assets/app.js"]
    assert 'buildWorkspaceCompareDrilldownContent(baselineEntry, candidateEntry, sweepComparison)' in files["catalog/assets/app.js"]
    assert 'buildWorkspacePrimaryDeltaContent(rowState.sameMetric, rowState.delta)' in files["catalog/assets/app.js"]
    assert 'buildWorkspacePrimaryRatioContent(rowState.sameMetric, rowState.ratio)' in files["catalog/assets/app.js"]
    assert "const sameMetric = entry.primary_metric_name === baselineEntry.primary_metric_name;" not in files["catalog/assets/app.js"]
    assert "const delta = entry.primary_metric_value - baselineEntry.primary_metric_value;" not in files["catalog/assets/app.js"]
    assert "const ratio = baselineEntry.primary_metric_value !== 0 ? entry.primary_metric_value / baselineEntry.primary_metric_value : null;" not in files["catalog/assets/app.js"]
    assert "const sweepComparison = resolveSweepComparison(baselineEntry, entry);" not in files["catalog/assets/app.js"]
    assert "renderWorkspaceSummaryCell(" in files["catalog/assets/app.js"]
    assert "return buildTitledDirectionTagMarkup(" in files["catalog/assets/app.js"]
    assert "return buildTitledScalarDeltaDirectionTag(" in files["catalog/assets/app.js"]
    assert 'candidate regressions' in files["catalog/assets/app.js"]
    assert 'mixed' in files["catalog/assets/app.js"]
    assert 'none' in files["catalog/assets/app.js"]
    assert "candidate faster" in files["catalog/assets/app.js"]
    assert "candidate slower" in files["catalog/assets/app.js"]
    assert "pressure up" in files["catalog/assets/app.js"]
    assert "pressure down" in files["catalog/assets/app.js"]
    assert "buildGroupedScalarDirectionTag(group, scalarDeltas)" in files["catalog/assets/app.js"]
    assert ".summary-stack {" in files["catalog/assets/styles.css"]
    assert ".summary-stack-value {" in files["catalog/assets/styles.css"]
    assert "Show all " in files["catalog/assets/app.js"]
    assert "Headline" in files["catalog/assets/app.js"]
    assert "Throughput / Latency" in files["catalog/assets/app.js"]
    assert "scalar_deltas" in files["catalog/assets/app.js"]
    assert "layer_deltas" in files["catalog/assets/app.js"]
    assert "Workspace Compare" in files["catalog/index.html"]
    assert "function filterCatalogEntries" in files["catalog/assets/app.js"]
    assert "function groupCatalogEntries" in files["catalog/assets/app.js"]
    assert "function renderCatalogGroups" in files["catalog/assets/app.js"]
    assert "CATALOG_ENTRIES" in files["catalog/assets/app.js"]


def test_build_visualization_catalog_supports_empty_entries() -> None:
    from llm_sched.visualization import build_visualization_catalog

    artifact, files = build_visualization_catalog(
        catalog_id="catalog.empty",
        title="Empty Catalog",
        entries=[],
        catalog_root=Path("catalog"),
    )

    assert artifact.metadata.entry_count == 0
    assert "No runs have been added" in files["catalog/index.html"]


def test_build_visualization_catalog_renders_phase_c_gate_summary_when_present() -> None:
    from llm_sched.contracts.visualization_catalog import (
        VisualizationCatalogPhaseCBlockedCase,
        VisualizationCatalogEntry,
        VisualizationCatalogPhaseCGateSummary,
    )
    from llm_sched.visualization import build_visualization_catalog

    artifact, files = build_visualization_catalog(
        catalog_id="catalog.phase-c",
        title="Phase C Catalog",
        entries=[
            VisualizationCatalogEntry(
                entry_id="run.prefill.single",
                run_id="run-prefill-single",
                scenario_name="prefill_seq128",
                mode="prefill",
                schedule_kind="single-core",
                target_profile_name="riscv_npu_single_core_v1",
                primary_metric_name="estimated_cycles",
                primary_metric_value=4096.0,
                workbench_entry_path="../run-prefill-single/workbench/index.html",
            )
        ],
        phase_c_gate_summary=VisualizationCatalogPhaseCGateSummary(
            status="in_progress",
            ready_case_count=2,
            blocked_case_count=2,
            planner_blocked_case_count=1,
            downstream_blocked_case_count=1,
            missing_case_count=1,
            duplicate_case_count=0,
        ),
        phase_c_blocked_cases=[
            VisualizationCatalogPhaseCBlockedCase(
                case_id="single-core:prefill",
                run_id="run-prefill-single",
                workbench_entry_path="../run-prefill-single/workbench/index.html",
                blocker_kind="planner",
                planner_closure_status="in_progress",
                downstream_closure_status="ready_for_acceptance",
                downstream_missing_consumers=[],
                remaining_gaps=["planner_closure: overflow region: ping"],
            ),
            VisualizationCatalogPhaseCBlockedCase(
                case_id="single-core:decode",
                run_id="run-decode-single",
                workbench_entry_path="../run-decode-single/workbench/index.html",
                blocker_kind="downstream",
                planner_closure_status="ready_for_acceptance",
                downstream_closure_status="in_progress",
                downstream_missing_consumers=["performance_estimation"],
                remaining_gaps=["required downstream evidence missing"],
            ),
            VisualizationCatalogPhaseCBlockedCase(
                case_id="dual-core:prefill",
                run_id=None,
                blocker_kind="missing_case",
                planner_closure_status=None,
                downstream_closure_status=None,
                downstream_missing_consumers=[],
                remaining_gaps=["missing canonical case: dual-core:prefill"],
            ),
        ],
        catalog_root=Path("catalog"),
    )

    assert artifact.metadata.phase_c_gate_summary is not None
    assert len(artifact.metadata.phase_c_blocked_cases) == 3
    assert "Phase C Gate" in files["catalog/index.html"]
    assert "Blocked Cases" in files["catalog/index.html"]
    assert "single-core:prefill" in files["catalog/index.html"]
    assert "single-core:decode" in files["catalog/index.html"]
    assert "dual-core:prefill" in files["catalog/index.html"]
    assert "missing_case" in files["catalog/index.html"]
    assert "Open Memory" in files["catalog/index.html"]
    assert "Open Summary" in files["catalog/index.html"]
    assert "Open Workbench" not in files["catalog/index.html"]
    assert "../run-prefill-single/workbench/index.html?panel=memory&memory_query=ping" in files["catalog/index.html"]
    assert "../run-decode-single/workbench/index.html?panel=summary" in files["catalog/index.html"]
    assert 'class="blocked-case-workbench-link"' in files["catalog/index.html"]
    assert 'data-workbench-path="../run-prefill-single/workbench/index.html"' in files["catalog/index.html"]
    assert 'data-workbench-panel="memory"' in files["catalog/index.html"]
    assert 'data-workbench-memory-query="ping"' in files["catalog/index.html"]
    assert 'data-workbench-panel="summary"' in files["catalog/index.html"]
    assert "planner_blocked" in files["catalog/index.html"]
    assert "downstream_blocked" in files["catalog/index.html"]
    assert "status: in_progress" in files["catalog/index.html"]
    assert "function refreshBlockedCaseWorkbenchLinks" in files["catalog/assets/app.js"]
    assert 'document.querySelectorAll(".blocked-case-workbench-link")' in files["catalog/assets/app.js"]
    assert "workbenchMemoryQuery" in files["catalog/assets/app.js"]
    assert "refreshBlockedCaseWorkbenchLinks();" in files["catalog/assets/app.js"]


def test_build_visualization_catalog_renders_descriptor_generation_focus_link() -> None:
    from llm_sched.contracts.visualization_catalog import (
        VisualizationCatalogPhaseCBlockedCase,
        VisualizationCatalogEntry,
        VisualizationCatalogPhaseCGateSummary,
    )
    from llm_sched.visualization import build_visualization_catalog

    _artifact, files = build_visualization_catalog(
        catalog_id="catalog.phase-c",
        title="Phase C Catalog",
        entries=[
            VisualizationCatalogEntry(
                entry_id="run.decode.single",
                run_id="run-decode-single",
                scenario_name="decode_token1_kv2048",
                mode="decode",
                schedule_kind="single-core",
                target_profile_name="riscv_npu_single_core_v1",
                primary_metric_name="token_latency_cycles",
                primary_metric_value=512.0,
                workbench_entry_path="../run-decode-single/workbench/index.html",
            )
        ],
        phase_c_gate_summary=VisualizationCatalogPhaseCGateSummary(
            status="in_progress",
            ready_case_count=0,
            blocked_case_count=1,
            planner_blocked_case_count=0,
            downstream_blocked_case_count=1,
            missing_case_count=0,
            duplicate_case_count=0,
        ),
        phase_c_blocked_cases=[
            VisualizationCatalogPhaseCBlockedCase(
                case_id="single-core:decode",
                run_id="run-decode-single",
                workbench_entry_path="../run-decode-single/workbench/index.html",
                blocker_kind="downstream",
                planner_closure_status="ready_for_acceptance",
                downstream_closure_status="in_progress",
                downstream_missing_consumers=["descriptor_generation"],
                remaining_gaps=[
                    "descriptor_generation: descriptor_ir exists but structured address fields lack storage provenance."
                ],
            )
        ],
        catalog_root=Path("catalog"),
    )

    assert (
        "../run-decode-single/workbench/index.html?panel=coverage&coverage_focus=packed-descriptor"
        in files["catalog/index.html"]
    )
    assert 'data-workbench-panel="coverage"' in files["catalog/index.html"]
    assert 'data-workbench-coverage-focus="packed-descriptor"' in files["catalog/index.html"]
    assert "workbenchCoverageFocus" in files["catalog/assets/app.js"]
