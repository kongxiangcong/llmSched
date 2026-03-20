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
        primary_metrics={"estimated_cycles": 4096.0, "tokens_per_cycle": 0.03125},
        include_sweep=True,
    )
    _write_packaged_run(
        run_root_b,
        run_id="run-b",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="dual-core",
        target_profile_name="riscv_npu_dual_core_v1",
        primary_metrics={"token_latency_cycles": 512.0, "tokens_per_second": 1953.125},
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
    assert artifact.entries[0].metric_values["estimated_cycles"] == 4096.0
    assert artifact.entries[0].metric_values["tokens_per_cycle"] == 0.03125
    assert artifact.entries[0].sweep_baseline_target_profile_name == "riscv_npu_single_core_v1"
    assert artifact.entries[0].sweep_comparisons[0].compare_summary is not None
    assert artifact.entries[0].sweep_comparisons[0].compare_summary.profile_diff_fields == [
        "core_mode",
        "num_cores",
    ]
    assert artifact.entries[0].sweep_comparisons[0].compare_summary.scalar_deltas[0].metric_name == (
        "estimated_cycles"
    )
    assert [
        focus.focus_id
        for focus in artifact.entries[0].sweep_comparisons[0].compare_summary.available_focus_modes
    ] == [
        "summary",
        "throughput-latency",
        "phase-shape",
        "memory-pressure",
        "schedule-shape",
        "estimated-layer",
    ]
    assert [
        mode.mode_id
        for mode in artifact.entries[0]
        .sweep_comparisons[0]
        .compare_summary.available_layer_delta_modes
    ] == [
        "top-cycle",
        "regressions-only",
        "top-by-bytes",
    ]
    assert artifact.entries[0].sweep_comparisons[0].compare_summary.bandwidth_pressure_compare is not None
    assert (
        artifact.entries[0]
        .sweep_comparisons[0]
        .compare_summary.bandwidth_pressure_compare.peak_pressure_subject_id.changed
        is True
    )
    assert artifact.entries[0].sweep_comparisons[0].compare_summary.vmem_pressure_compare is not None
    assert (
        artifact.entries[0]
        .sweep_comparisons[0]
        .compare_summary.vmem_pressure_compare.hottest_region.changed
        is True
    )
    assert [
        scalar.metric_name
        for scalar in artifact.entries[0].sweep_comparisons[0].compare_summary.highlighted_scalar_deltas
    ] == ["estimated_cycles", "tokens_per_cycle"]
    assert [
        group.group_id
        for group in artifact.entries[0].sweep_comparisons[0].compare_summary.scalar_delta_groups
    ] == [
        "headline",
        "throughput_latency",
        "phase_shape",
        "memory_pressure",
        "schedule_shape",
    ]
    assert (
        artifact.entries[0]
        .sweep_comparisons[0]
        .compare_summary.scalar_delta_groups[0]
        .scalar_deltas[0]
        .metric_name
        == "estimated_cycles"
    )
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].delta_cycles == -512.0
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].baseline_cycle_share == 0.5
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].delta_cycles_ratio == -0.25
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].change_direction == "down"
    assert artifact.entries[1].metric_values["token_latency_cycles"] == 512.0
    assert artifact.entries[1].metric_values["tokens_per_second"] == 1953.125
    assert (catalog_root / "catalog" / "index.html").is_file()
    app_js = (catalog_root / "catalog" / "assets" / "app.js").read_text(encoding="utf-8")
    assert "function buildSharedMetricDeltaRows" in app_js
    assert "function resolveSweepComparison" in app_js
    assert "function renderSweepLayerDeltaRows" in app_js
    assert "function orderedSweepLayerDeltas" in app_js
    assert "function buildSweepDrilldownLink" in app_js
    assert "function buildSweepLayerDrilldownLink" in app_js
    assert "function currentLayerDeltaFocus" in app_js
    assert "function currentCompareFocus" in app_js
    assert "function selectSweepLayerDeltas" in app_js
    assert "sweep_candidate" in app_js
    assert "sweep_layer_focus" in app_js
    assert "compare_focus" in app_js
    assert "workspace_candidate" in app_js
    assert "workspace_detail_focus" in app_js
    assert "workspace_secondary_detail_focus" in app_js
    assert "workspace_detail_preset" in app_js
    assert "workspace_analysis_flow" in app_js
    assert "Shared Metric Deltas" in app_js
    assert "Sweep Layer Deltas" in app_js
    assert "layer_delta_focus" in app_js
    assert "regressions-only" in app_js
    assert "top-by-bytes" in app_js
    assert "Workspace Compare Drilldown" in app_js
    assert "Grouped Metric Deltas" in app_js
    assert "Estimated Layer Deltas" in app_js
    assert "Fitted Layer Deltas" in app_js
    assert "function buildWorkspaceCompareDrilldownContent" in app_js
    assert "function renderWorkspaceCompareDrilldownSection" in app_js
    assert "function resolveFocusedWorkspaceCandidate" in app_js
    assert "function buildWorkspaceFocusLink" in app_js
    assert "function renderFocusedWorkspaceDrilldown" in app_js
    assert "function currentWorkspaceDetailFocus" in app_js
    assert "function currentWorkspaceDetailFocusLabel" in app_js
    assert "function currentWorkspaceSecondaryDetailFocus" in app_js
    assert "function currentWorkspaceSecondaryDetailFocusLabel" in app_js
    assert "function currentWorkspaceDetailPreset" in app_js
    assert "function resolveWorkspaceDetailPreset" in app_js
    assert "function currentWorkspaceAnalysisFlow" in app_js
    assert "function resolveWorkspaceAnalysisFlow" in app_js
    assert "function buildWorkspaceRowAnalysisFlowLink" in app_js
    assert "function buildWorkspaceDetailFocusLink" in app_js
    assert "function buildWorkspaceRowPresetLink" in app_js
    assert "function buildWorkspaceRowSectionFocusLink" in app_js
    assert "function orderWorkspaceDrilldownSections" in app_js
    assert "function buildCurrentCatalogWorkspaceUrl" in app_js
    assert "function copyCurrentWorkspaceLink" in app_js
    assert "function buildWorkspaceExportData" in app_js
    assert "function buildWorkspaceSnapshotSvg" in app_js
    assert "function downloadCurrentWorkspaceJson" in app_js
    assert "function downloadCurrentWorkspaceSvg" in app_js
    assert "function bindCatalogWorkspaceActions" in app_js
    assert "Exported workspace JSON." in app_js
    assert "Exported workspace SVG." in app_js
    assert "Workspace view link copied." in app_js
    assert "Focused Layer Delta Mode" in app_js
    assert "Focused Compare Focus" in app_js
    assert "Focused Compare Scope" in app_js
    assert "Focused Workspace Candidate" in app_js
    assert "Focused Workspace Detail" in app_js
    assert "Focused Workspace Compare-Against Detail" in app_js
    assert "Focused Workspace Compare Preset" in app_js
    assert "Focused Workspace Analysis Flow" in app_js
    assert "Focused Workspace Analysis Flow Summary" in app_js
    assert "Focused Workspace Analysis Recommendation" in app_js
    assert "focused_workspace_candidate" in app_js
    assert "focused_workspace_detail_focus" in app_js
    assert "focused_workspace_secondary_detail_focus" in app_js
    assert "focused_workspace_detail_preset" in app_js
    assert "focused_workspace_analysis_flow" in app_js
    assert "focused_workspace_analysis_flow_summary" in app_js
    assert "focused_workspace_analysis_recommendation" in app_js
    assert "Focused Workspace Compare Drilldown" in app_js
    assert "Focus In Workspace" in app_js
    assert "Focus Compare Section" in app_js
    assert 'buildWorkspaceRowSectionFocusLink(candidateEntry, "summary", "Summary Compare")' in app_js
    assert 'buildWorkspaceRowSectionFocusLink(candidateEntry, "grouped-metrics", "Grouped Metric Deltas")' in app_js
    assert 'buildWorkspaceRowSectionFocusLink(candidateEntry, "estimated-layer", "Estimated Layer Deltas")' in app_js
    assert 'buildWorkspaceRowPresetLink(candidateEntry, "grouped-vs-estimated-layer", "Grouped Metrics vs Estimated Layer")' in app_js
    assert 'buildWorkspaceRowPresetLink(candidateEntry, "summary-vs-estimated-layer", "Summary vs Estimated Layer")' in app_js
    assert 'buildWorkspaceRowAnalysisFlowLink(candidateEntry, "grouped-hotspots", "Grouped Hotspots")' in app_js
    assert 'buildWorkspaceRowAnalysisFlowLink(candidateEntry, "summary-hotspots", "Summary Hotspots")' in app_js
    assert "Analysis Flow Summary" in app_js
    assert "Analysis Flow Candidate Recommendation" in app_js
    assert "Recommended For Current Flow" in app_js
    assert "analysis_flow_recommendation" in app_js
    assert "recommendation_tier" in app_js
    assert "recommendation_reason" in app_js
    assert "analysis_flow: currentWorkspaceAnalysisFlow()" in app_js
    assert "Showing top 3 of" in app_js
    assert "|delta_cycles|" in app_js
    assert "|delta_bytes|" in app_js
    assert "Open Sweep Panel" in app_js
    assert "Open Layer In Sweep" in app_js
    assert 'buildWorkbenchHref(match.sourceEntry.workbench_entry_path, "sweep", { compare_focus: currentCompareFocus(), layer_delta_focus: currentLayerDeltaFocus(), analysis_flow: currentWorkspaceAnalysisFlow() })' in app_js
    assert 'buildWorkbenchHref(match.sourceEntry.workbench_entry_path, "sweep", { compare_focus: currentCompareFocus(), layer_delta_focus: currentLayerDeltaFocus(), analysis_flow: currentWorkspaceAnalysisFlow(), sweep_candidate: candidateEntry.target_profile_name, sweep_layer_focus: layerId })' in app_js
    assert "metric_values" in app_js
    assert "sweep_comparisons" in app_js
    assert "compare_summary" in app_js
    assert "profile_diff_fields" in app_js
    assert "baseline_schedule_kind" in app_js
    assert "highlighted_scalar_deltas" in app_js
    assert "bandwidth_pressure_compare" in app_js
    assert "vmem_pressure_compare" in app_js
    assert "function renderPressureCompareSummary" in app_js
    assert "Peak Bandwidth Pressure" in app_js
    assert "VMEM Pressure Shifts" in app_js
    assert "Highlighted Metric Shifts" in app_js
    assert "function currentWorkbenchPanel" in app_js
    assert "function buildComparePanelLinks" in app_js
    assert "function serializeCatalogState" in app_js
    assert "function hydrateCatalogStateFromUrl" in app_js
    assert "catalog_return" in app_js
    assert "compare_ids" in app_js
    assert "Open Selected Panel" in app_js
    index_html = (catalog_root / "catalog" / "index.html").read_text(encoding="utf-8")
    assert "catalog-workbench-panel-filter" in index_html
    assert "catalog-compare-focus-filter" in index_html
    assert "catalog-layer-delta-focus-filter" in index_html
    assert "copy-workspace-link-button" in index_html
    assert "download-workspace-json-button" in index_html
    assert "download-workspace-svg-button" in index_html
    assert "catalog-workspace-action-status" in index_html


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


def test_run_visualization_catalog_copies_phase_c_gate_summary_from_workspace_report(
    tmp_path: Path,
) -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact
    from llm_sched.pipeline import run_visualization_catalog

    workspace_root = tmp_path / "workspace-root"
    runs_root = workspace_root / "runs"
    run_root = runs_root / "run-single-prefill"
    _write_packaged_run(
        run_root,
        run_id="run-single-prefill",
        scenario_name="prefill_seq128",
        mode="prefill",
        schedule_kind="single-core",
        target_profile_name="riscv_npu_single_core_v1",
        primary_metrics={"estimated_cycles": 4096.0},
    )
    _write_packaged_run(
        runs_root / "run-single-decode",
        run_id="run-single-decode",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="single-core",
        target_profile_name="riscv_npu_single_core_v1",
        primary_metrics={"token_latency_cycles": 512.0},
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
                        "dual-core:prefill",
                    ],
                    "missing_case_ids": ["dual-core:decode"],
                    "duplicate_case_ids": [],
                    "ready_case_count": 3,
                    "blocked_case_count": 1,
                    "planner_blocked_case_count": 1,
                    "downstream_blocked_case_count": 0,
                },
                "case_records": [],
                "issues": [],
                "remaining_gaps": ["missing canonical case: dual-core:decode"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_visualization_catalog(
        tmp_path / "catalog-root",
        [],
        workspace_root=workspace_root,
    )

    assert result.status == "completed"
    artifact = VisualizationCatalogArtifact.model_validate_json(
        result.catalog_manifest_path.read_text(encoding="utf-8")
    )
    assert artifact.metadata.phase_c_gate_summary is not None
    assert artifact.metadata.phase_c_gate_summary.status == "in_progress"
    assert artifact.metadata.phase_c_gate_summary.planner_blocked_case_count == 1
    assert artifact.metadata.phase_c_gate_summary.missing_case_count == 1


def test_run_visualization_catalog_copies_phase_c_blocked_cases_from_workspace_report(
    tmp_path: Path,
) -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact
    from llm_sched.pipeline import run_visualization_catalog

    workspace_root = tmp_path / "workspace-root"
    runs_root = workspace_root / "runs"
    run_root = runs_root / "run-single-prefill"
    _write_packaged_run(
        run_root,
        run_id="run-single-prefill",
        scenario_name="prefill_seq128",
        mode="prefill",
        schedule_kind="single-core",
        target_profile_name="riscv_npu_single_core_v1",
        primary_metrics={"estimated_cycles": 4096.0},
    )
    _write_packaged_run(
        runs_root / "run-single-decode",
        run_id="run-single-decode",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="single-core",
        target_profile_name="riscv_npu_single_core_v1",
        primary_metrics={"token_latency_cycles": 512.0},
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

    result = run_visualization_catalog(
        tmp_path / "catalog-root",
        [],
        workspace_root=workspace_root,
    )

    assert result.status == "completed"
    artifact = VisualizationCatalogArtifact.model_validate_json(
        result.catalog_manifest_path.read_text(encoding="utf-8")
    )
    assert [case.case_id for case in artifact.metadata.phase_c_blocked_cases] == [
        "single-core:prefill",
        "single-core:decode",
        "dual-core:prefill",
    ]
    assert artifact.metadata.phase_c_blocked_cases[0].blocker_kind == "planner"
    assert artifact.metadata.phase_c_blocked_cases[1].blocker_kind == "downstream"
    assert artifact.metadata.phase_c_blocked_cases[2].blocker_kind == "missing_case"
    assert artifact.metadata.phase_c_blocked_cases[1].downstream_missing_consumers == [
        "performance_estimation"
    ]
    assert (
        artifact.metadata.phase_c_blocked_cases[0].workbench_entry_path
        == "../../workspace-root/runs/run-single-prefill/workbench/index.html"
    )
    assert (
        artifact.metadata.phase_c_blocked_cases[1].workbench_entry_path
        == "../../workspace-root/runs/run-single-decode/workbench/index.html"
    )
    assert artifact.metadata.phase_c_blocked_cases[2].workbench_entry_path is None


def _write_packaged_run(
    run_root: Path,
    *,
    run_id: str,
    scenario_name: str,
    mode: str,
    schedule_kind: str,
    target_profile_name: str,
    primary_metrics: dict[str, float],
    include_sweep: bool = False,
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
                include_sweep=include_sweep,
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
    include_sweep: bool = False,
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
        "sweep_view": (
            {
                "baseline_target_profile_name": "riscv_npu_single_core_v1",
                "comparison_count": 1,
                "issue_count": 0,
                "comparisons": [
                    {
                        "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                        "scenario_name": scenario_name,
                        "mode": mode,
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
                                {
                                    "group_id": "phase_shape",
                                    "title": "Phase Shape",
                                    "scalar_deltas": [
                                        {
                                            "metric_name": "projection_cycle_share",
                                            "baseline_value": 0.375,
                                            "candidate_value": 0.3333333333,
                                            "delta_value": -0.0416666667,
                                            "delta_ratio": -0.1111111112,
                                        }
                                    ],
                                },
                                {
                                    "group_id": "memory_pressure",
                                    "title": "Memory Pressure",
                                    "scalar_deltas": [
                                        {
                                            "metric_name": "projection_read_bytes_ddr",
                                            "baseline_value": 32768.0,
                                            "candidate_value": 24576.0,
                                            "delta_value": -8192.0,
                                            "delta_ratio": -0.25,
                                        }
                                    ],
                                },
                                {
                                    "group_id": "schedule_shape",
                                    "title": "Schedule Shape",
                                    "scalar_deltas": [
                                        {
                                            "metric_name": "projection_schedule_compression_cycles",
                                            "baseline_value": 384.0,
                                            "candidate_value": 192.0,
                                            "delta_value": -192.0,
                                            "delta_ratio": -0.5,
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
                                "baseline_cycle_share": 0.25,
                                "candidate_cycle_share": 0.2051282051,
                                "delta_cycle_share": -0.0448717949,
                                "delta_cycles_ratio": -0.125,
                                "baseline_bytes": 32768.0,
                                "candidate_bytes": 30720.0,
                                "delta_bytes": -2048.0,
                                "delta_bytes_ratio": -0.0625,
                                "change_direction": "down",
                            },
                            {
                                "layer_id": 0,
                                "baseline_cycles": 2048.0,
                                "candidate_cycles": 1536.0,
                                "delta_cycles": -512.0,
                                "baseline_cycle_share": 0.5,
                                "candidate_cycle_share": 0.4444444444,
                                "delta_cycle_share": -0.0555555556,
                                "delta_cycles_ratio": -0.25,
                                "baseline_bytes": 65536.0,
                                "candidate_bytes": 49152.0,
                                "delta_bytes": -16384.0,
                                "delta_bytes_ratio": -0.25,
                                "change_direction": "down",
                            },
                            {
                                "layer_id": 3,
                                "baseline_cycles": 1536.0,
                                "candidate_cycles": 1280.0,
                                "delta_cycles": -256.0,
                                "baseline_cycle_share": 0.375,
                                "candidate_cycle_share": 0.3162393162,
                                "delta_cycle_share": -0.0587606838,
                                "delta_cycles_ratio": -0.1666666667,
                                "baseline_bytes": 49152.0,
                                "candidate_bytes": 45056.0,
                                "delta_bytes": -4096.0,
                                "delta_bytes_ratio": -0.0833333333,
                                "change_direction": "down",
                            },
                            {
                                "layer_id": 1,
                                "baseline_cycles": 768.0,
                                "candidate_cycles": 640.0,
                                "delta_cycles": -128.0,
                                "baseline_cycle_share": 0.1875,
                                "candidate_cycle_share": 0.1709401709,
                                "delta_cycle_share": -0.0165598291,
                                "delta_cycles_ratio": -0.1666666667,
                                "baseline_bytes": 24576.0,
                                "candidate_bytes": 22528.0,
                                "delta_bytes": -2048.0,
                                "delta_bytes_ratio": -0.0833333333,
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
