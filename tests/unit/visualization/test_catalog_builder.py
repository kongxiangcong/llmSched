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
    assert "catalog-compare-scope-filter" in files["catalog/index.html"]
    assert "catalog-workbench-panel-filter" in files["catalog/index.html"]
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
    assert "function currentWorkbenchPanel" in files["catalog/assets/app.js"]
    assert "function buildComparePanelLinks" in files["catalog/assets/app.js"]
    assert "function serializeCatalogState" in files["catalog/assets/app.js"]
    assert "function hydrateCatalogStateFromUrl" in files["catalog/assets/app.js"]
    assert "catalog_return" in files["catalog/assets/app.js"]
    assert "compare_ids" in files["catalog/assets/app.js"]
    assert "Open Selected Panel" in files["catalog/assets/app.js"]
    assert "function buildSharedMetricDeltaRows" in files["catalog/assets/app.js"]
    assert "Shared Metric Deltas" in files["catalog/assets/app.js"]
    assert "metric_values" in files["catalog/assets/app.js"]
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
