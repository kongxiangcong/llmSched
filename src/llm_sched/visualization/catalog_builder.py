"""Builder for SPEC-19 static cross-run visualization catalogs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlencode

from llm_sched.contracts.visualization_catalog import (
    VisualizationCatalogArtifact,
    VisualizationCatalogPhaseCBlockedCase,
    VisualizationCatalogEntry,
    VisualizationCatalogMetadata,
    VisualizationCatalogPhaseCGateSummary,
)
from llm_sched.visualization.recommendation_detail_snippets import (
    build_recommendation_detail_helpers_js,
)


def build_visualization_catalog(
    *,
    catalog_id: str,
    title: str,
    entries: list[VisualizationCatalogEntry],
    phase_c_gate_summary: VisualizationCatalogPhaseCGateSummary | None = None,
    phase_c_blocked_cases: list[VisualizationCatalogPhaseCBlockedCase] | None = None,
    catalog_root: str | Path,
) -> tuple[VisualizationCatalogArtifact, dict[str, str]]:
    catalog_root_path = Path(catalog_root)
    artifact = VisualizationCatalogArtifact(
        catalog_id=catalog_id,
        title=title,
        metadata=VisualizationCatalogMetadata(
            generated_by="run-visualization-catalog",
            entry_count=len(entries),
            default_sort_key="primary_metric",
            phase_c_gate_summary=phase_c_gate_summary,
            phase_c_blocked_cases=list(phase_c_blocked_cases or []),
        ),
        entries=entries,
    )
    files = {
        _normalize(catalog_root_path / "index.html"): _build_index_html(artifact),
        _normalize(catalog_root_path / "assets" / "app.js"): _build_app_js(entries),
        _normalize(catalog_root_path / "assets" / "styles.css"): _build_styles_css(),
        _normalize(catalog_root_path / "catalog_manifest.json"): json.dumps(
            artifact.model_dump(mode="json"),
            indent=2,
        ),
    }
    return artifact, files


def _build_index_html(artifact: VisualizationCatalogArtifact) -> str:
    rows = _build_table_rows(artifact.entries)
    group_links = "\n".join(
        f'          <a class="group-chip" href="#group-{_slugify(group_name)}">{group_name}</a>'
        for group_name in _group_names(artifact.entries)
    )
    group_sections = "\n".join(_build_group_section(group_name, artifact.entries) for group_name in _group_names(artifact.entries))
    empty_state = (
        "<p class=\"empty\">No runs have been added to this catalog yet.</p>"
        if not artifact.entries
        else ""
    )
    stat_cards = _build_stat_cards(artifact.entries)
    phase_c_gate_banner = _build_phase_c_gate_banner(
        artifact.metadata.phase_c_gate_summary,
        artifact.metadata.phase_c_blocked_cases,
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{artifact.title}</title>
    <link rel="stylesheet" href="./assets/styles.css">
  </head>
  <body>
    <div class="shell">
      <header class="hero">
        <p class="eyebrow">SPEC-19 Catalog</p>
        <h1>{artifact.title}</h1>
        <p class="muted">Cross-run index for packaged workbenches</p>
      </header>
      {phase_c_gate_banner}
      <section class="toolbar">
        <label class="control" for="catalog-search-input">
          <span>Search</span>
          <input id="catalog-search-input" type="search" placeholder="Search run, scenario, target">
        </label>
        <label class="control" for="catalog-mode-filter">
          <span>Mode</span>
          <select id="catalog-mode-filter">
            <option value="all">All modes</option>
            <option value="prefill">prefill</option>
            <option value="decode">decode</option>
          </select>
        </label>
        <label class="control" for="catalog-schedule-filter">
          <span>Schedule</span>
          <select id="catalog-schedule-filter">
            <option value="all">All schedules</option>
            <option value="single-core">single-core</option>
            <option value="dual-core">dual-core</option>
          </select>
        </label>
      </section>
      {empty_state}
      <section class="stat-grid">
{stat_cards}
      </section>
      <section class="compare-tray" id="catalog-compare-tray">
        <div class="compare-tray-header">
          <div>
            <h2>Compare Selected Runs</h2>
            <p class="muted">Pick up to two runs from the table or grouped cards.</p>
          </div>
          <div class="compare-workspace-controls">
            <label class="control control-compact" for="catalog-workbench-panel-filter">
              <span>Workbench Panel</span>
              <select id="catalog-workbench-panel-filter">
                <option value="summary">summary</option>
                <option value="timeline">timeline</option>
                <option value="memory">memory</option>
                <option value="coverage">coverage</option>
              </select>
            </label>
            <label class="control control-compact" for="catalog-layer-delta-focus-filter">
              <span>Layer Delta Focus</span>
              <select id="catalog-layer-delta-focus-filter">
                <option value="top-cycle">Top By Cycles</option>
                <option value="regressions-only">Candidate Regressions</option>
                <option value="top-by-bytes">Top By Bytes</option>
                <option value="top-by-fitted-work">Top By Fitted Work</option>
                <option value="fitted-regressions-only">Fitted Work Regressions</option>
              </select>
            </label>
          </div>
        </div>
        <div id="catalog-compare-content">
          <p class="empty">Select one or two runs to compare primary metrics.</p>
        </div>
      </section>
      <section class="compare-workspace" id="catalog-compare-workspace">
        <div class="compare-tray-header">
          <div>
            <h2>Workspace Compare</h2>
            <p class="muted">The first selected run acts as the baseline for visible runs in the current compare scope.</p>
          </div>
        <div class="compare-workspace-controls">
          <label class="control control-compact" for="catalog-compare-scope-filter">
            <span>Compare Scope</span>
            <select id="catalog-compare-scope-filter">
              <option value="same-scenario">Same scenario</option>
              <option value="all-visible">All visible runs</option>
            </select>
          </label>
          <label class="control control-compact" for="catalog-compare-focus-filter">
            <span>Compare Focus</span>
            <select id="catalog-compare-focus-filter">
              <option value="summary">Summary Focus</option>
              <option value="throughput-latency">Throughput / Latency Focus</option>
              <option value="phase-shape">Phase Shape Focus</option>
              <option value="memory-pressure">Memory Pressure Focus</option>
              <option value="schedule-shape">Schedule Shape Focus</option>
              <option value="estimated-layer">Estimated Layer Focus</option>
              <option value="fitted-layer">Fitted Layer Focus</option>
            </select>
          </label>
          <button id="copy-workspace-link-button" type="button">Copy Workspace Link</button>
          <button id="download-workspace-json-button" type="button">Export Workspace JSON</button>
          <button id="download-workspace-svg-button" type="button">Export Workspace SVG</button>
          <button class="compare-toggle" id="swap-compare-order-button" type="button">Swap Baseline/Candidate</button>
        </div>
        </div>
        <p class="muted" id="catalog-workspace-action-status" aria-live="polite"></p>
        <div id="catalog-compare-workspace-content">
          <p class="empty">Select a baseline run to open the scenario compare workspace.</p>
        </div>
      </section>
      <nav class="group-nav" id="catalog-group-nav">
{group_links}
      </nav>
      <section class="table-card">
        <table class="catalog-table">
          <thead>
            <tr>
              <th>Compare</th>
              <th>Run</th>
              <th>Scenario</th>
              <th>Mode</th>
              <th>Schedule</th>
              <th>Target</th>
              <th>Primary Metric</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody id="catalog-entry-table">
{rows}
          </tbody>
        </table>
      </section>
      <section class="group-sections" id="catalog-group-sections">
{group_sections}
      </section>
    </div>
    <script src="./assets/app.js"></script>
  </body>
</html>
"""


def _build_app_js(entries: list[VisualizationCatalogEntry]) -> str:
    recommendation_detail_helpers = build_recommendation_detail_helpers_js()
    return ("""const CATALOG_ENTRIES = __CATALOG_ENTRIES__;

function normalizeText(value) {
  return String(value || "").toLowerCase();
}

function filterCatalogEntries(entries, query, mode, schedule) {
  const normalized = normalizeText(query).trim();
  return entries.filter((entry) => {
    const matchesQuery = !normalized || [entry.run_id, entry.scenario_name, entry.target_profile_name, entry.schedule_kind]
      .some((field) => normalizeText(field).includes(normalized));
    const matchesMode = mode === "all" || entry.mode === mode;
    const matchesSchedule = schedule === "all" || entry.schedule_kind === schedule;
    return matchesQuery && matchesMode && matchesSchedule;
  });
}

function slugifyGroupName(value) {
  return String(value || "ungrouped").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function panelLink(entry, panel) {
  return `${entry.workbench_entry_path}?panel=${panel}`;
}

const COMPARE_SELECTION = [];
let CURRENT_WORKSPACE_CANDIDATE_ID = "";
let CURRENT_WORKSPACE_DETAIL_FOCUS = "summary";
let CURRENT_WORKSPACE_SECONDARY_DETAIL_FOCUS = "";
let CURRENT_WORKSPACE_DETAIL_PRESET = "";
let CURRENT_WORKSPACE_ANALYSIS_FLOW = "";

function currentWorkspaceCandidate() {
  return CURRENT_WORKSPACE_CANDIDATE_ID || "";
}

function currentWorkspaceDetailFocus() {
  return CURRENT_WORKSPACE_DETAIL_FOCUS || "summary";
}

function currentWorkspaceSecondaryDetailFocus() {
  return CURRENT_WORKSPACE_SECONDARY_DETAIL_FOCUS || "";
}

function currentWorkspaceDetailPreset() {
  return CURRENT_WORKSPACE_DETAIL_PRESET || "";
}

function currentWorkspaceAnalysisFlow() {
  return CURRENT_WORKSPACE_ANALYSIS_FLOW || "";
}

function serializeCatalogState() {
  const searchInput = document.querySelector("#catalog-search-input");
  const modeFilter = document.querySelector("#catalog-mode-filter");
  const scheduleFilter = document.querySelector("#catalog-schedule-filter");
  const compareScopeFilter = document.querySelector("#catalog-compare-scope-filter");
  const compareFocusFilter = document.querySelector("#catalog-compare-focus-filter");
  const workbenchPanelFilter = document.querySelector("#catalog-workbench-panel-filter");
  const layerDeltaFocusFilter = document.querySelector("#catalog-layer-delta-focus-filter");
  return {
    search: searchInput ? searchInput.value : "",
    mode: modeFilter ? modeFilter.value : "all",
    schedule: scheduleFilter ? scheduleFilter.value : "all",
    compare_scope: compareScopeFilter ? compareScopeFilter.value : "same-scenario",
    compare_focus: compareFocusFilter ? compareFocusFilter.value : "summary",
    workbench_panel: workbenchPanelFilter ? workbenchPanelFilter.value : "summary",
    layer_delta_focus: layerDeltaFocusFilter ? layerDeltaFocusFilter.value : "top-cycle",
    workspace_candidate: currentWorkspaceCandidate(),
    workspace_detail_focus: currentWorkspaceDetailFocus(),
    workspace_secondary_detail_focus: currentWorkspaceSecondaryDetailFocus(),
    workspace_detail_preset: currentWorkspaceDetailPreset(),
    workspace_analysis_flow: currentWorkspaceAnalysisFlow(),
    compare_ids: COMPARE_SELECTION.join(","),
  };
}

function buildCatalogReturnUrl(extraState = {}) {
  const state = {
    ...serializeCatalogState(),
    ...extraState,
  };
  const params = new URLSearchParams();
  Object.entries(state).forEach(([key, value]) => {
    if (value === null || value === undefined || String(value) === "") {
      return;
    }
    if (key === "mode" && value === "all") {
      return;
    }
    if (key === "schedule" && value === "all") {
      return;
    }
    if (key === "compare_scope" && value === "same-scenario") {
      return;
    }
    if (key === "compare_focus" && value === "summary") {
      return;
    }
    if (key === "workbench_panel" && value === "summary") {
      return;
    }
    if (key === "layer_delta_focus" && value === "top-cycle") {
      return;
    }
    params.set(key, String(value));
  });
  const url = new URL(window.location.href);
  url.search = params.toString();
  url.hash = "";
  return url.toString();
}

function hydrateCatalogStateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const searchInput = document.querySelector("#catalog-search-input");
  const modeFilter = document.querySelector("#catalog-mode-filter");
  const scheduleFilter = document.querySelector("#catalog-schedule-filter");
  const compareScopeFilter = document.querySelector("#catalog-compare-scope-filter");
  const compareFocusFilter = document.querySelector("#catalog-compare-focus-filter");
  const workbenchPanelFilter = document.querySelector("#catalog-workbench-panel-filter");
  const layerDeltaFocusFilter = document.querySelector("#catalog-layer-delta-focus-filter");
  if (searchInput) {
    searchInput.value = params.get("search") || "";
  }
  if (modeFilter) {
    modeFilter.value = params.get("mode") || "all";
  }
  if (scheduleFilter) {
    scheduleFilter.value = params.get("schedule") || "all";
  }
  if (compareScopeFilter) {
    compareScopeFilter.value = params.get("compare_scope") || "same-scenario";
  }
  if (compareFocusFilter) {
    compareFocusFilter.value = params.get("compare_focus") || "summary";
  }
  if (workbenchPanelFilter) {
    workbenchPanelFilter.value = params.get("workbench_panel") || "summary";
  }
  if (layerDeltaFocusFilter) {
    layerDeltaFocusFilter.value = params.get("layer_delta_focus") || "top-cycle";
  }
  CURRENT_WORKSPACE_CANDIDATE_ID = params.get("workspace_candidate") || "";
  CURRENT_WORKSPACE_DETAIL_FOCUS = params.get("workspace_detail_focus") || "summary";
  CURRENT_WORKSPACE_SECONDARY_DETAIL_FOCUS = params.get("workspace_secondary_detail_focus") || "";
  CURRENT_WORKSPACE_DETAIL_PRESET = params.get("workspace_detail_preset") || "";
  CURRENT_WORKSPACE_ANALYSIS_FLOW = params.get("workspace_analysis_flow") || "";
  COMPARE_SELECTION.splice(0, COMPARE_SELECTION.length);
  (params.get("compare_ids") || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .slice(0, 2)
    .forEach((entryId) => {
      COMPARE_SELECTION.push(entryId);
    });
}

function buildWorkbenchLink(entry, panel) {
  return buildWorkbenchHref(entry.workbench_entry_path, panel);
}

function buildWorkbenchHref(workbenchPath, panel, extraParams = {}) {
  const params = new URLSearchParams();
  params.set("panel", panel);
  Object.entries(extraParams).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value) !== "") {
      params.set(key, String(value));
    }
  });
  params.set("catalog_return", buildCatalogReturnUrl());
  return `${workbenchPath}?${params.toString()}`;
}

function refreshBlockedCaseWorkbenchLinks() {
  document.querySelectorAll(".blocked-case-workbench-link").forEach((anchor) => {
    const workbenchPath = anchor.dataset.workbenchPath;
    const panel = anchor.dataset.workbenchPanel || "summary";
    const workbenchMemoryQuery = anchor.dataset.workbenchMemoryQuery || "";
    const workbenchCoverageFocus = anchor.dataset.workbenchCoverageFocus || "";
    if (!workbenchPath) {
      return;
    }
    const extraParams = {};
    if (workbenchMemoryQuery) {
      extraParams.memory_query = workbenchMemoryQuery;
    }
    if (workbenchCoverageFocus) {
      extraParams.coverage_focus = workbenchCoverageFocus;
    }
    anchor.href = buildWorkbenchHref(workbenchPath, panel, extraParams);
  });
}

function currentWorkbenchPanel() {
  const panelFilter = document.querySelector("#catalog-workbench-panel-filter");
  return panelFilter ? panelFilter.value : "summary";
}

function currentCompareFocus() {
  const compareFocusFilter = document.querySelector("#catalog-compare-focus-filter");
  return compareFocusFilter ? compareFocusFilter.value : "summary";
}

function currentCompareFocusLabel() {
  const labels = {
    summary: "Summary Focus",
    "throughput-latency": "Throughput / Latency Focus",
    "phase-shape": "Phase Shape Focus",
    "memory-pressure": "Memory Pressure Focus",
    "schedule-shape": "Schedule Shape Focus",
    "estimated-layer": "Estimated Layer Focus",
    "fitted-layer": "Fitted Layer Focus",
  };
  return labels[currentCompareFocus()] || "Summary Focus";
}

function currentWorkspaceDetailFocusLabel() {
  const labels = {
    summary: "Summary Compare",
    "grouped-metrics": "Grouped Metric Deltas",
    pressure: "Pressure Compare",
    "estimated-layer": "Estimated Layer Deltas",
    "fitted-layer": "Fitted Layer Deltas",
  };
  const preset = resolveWorkspaceDetailPreset();
  const focus = preset ? preset.primary : currentWorkspaceDetailFocus();
  return labels[focus] || "Summary Compare";
}

function currentWorkspaceSecondaryDetailFocusLabel() {
  const labels = {
    summary: "Summary Compare",
    "grouped-metrics": "Grouped Metric Deltas",
    pressure: "Pressure Compare",
    "estimated-layer": "Estimated Layer Deltas",
    "fitted-layer": "Fitted Layer Deltas",
  };
  const preset = resolveWorkspaceDetailPreset();
  const focus = preset ? preset.secondary : currentWorkspaceSecondaryDetailFocus();
  return labels[focus] || "";
}

function resolveWorkspaceDetailPreset() {
  const flow = resolveWorkspaceAnalysisFlow();
  if (flow) {
    return {
      label: flow.label,
      primary: flow.primary,
      secondary: flow.secondary,
      preset_id: flow.preset_id,
    };
  }
  const presets = {
    "summary-vs-estimated-layer": {
      label: "Summary vs Estimated Layer",
      primary: "summary",
      secondary: "estimated-layer",
    },
    "grouped-vs-estimated-layer": {
      label: "Grouped Metrics vs Estimated Layer",
      primary: "grouped-metrics",
      secondary: "estimated-layer",
    },
    "pressure-vs-fitted-layer": {
      label: "Pressure vs Fitted Layer",
      primary: "pressure",
      secondary: "fitted-layer",
    },
  };
  return presets[currentWorkspaceDetailPreset()] || null;
}

function resolveWorkspaceAnalysisFlow() {
  const flows = {
    "summary-hotspots": {
      label: "Summary Hotspots",
      preset_id: "summary-vs-estimated-layer",
      primary: "summary",
      secondary: "estimated-layer",
    },
    "grouped-hotspots": {
      label: "Grouped Hotspots",
      preset_id: "grouped-vs-estimated-layer",
      primary: "grouped-metrics",
      secondary: "estimated-layer",
    },
    "memory-regression": {
      label: "Memory Regression",
      preset_id: "pressure-vs-fitted-layer",
      primary: "pressure",
      secondary: "fitted-layer",
    },
  };
  return flows[currentWorkspaceAnalysisFlow()] || null;
}

function maxAbsoluteLayerDelta(layerDeltas, fieldName) {
  return (layerDeltas || []).reduce((best, layerDelta) => {
    const value = Math.abs(Number(layerDelta && layerDelta[fieldName] || 0));
    return value > best ? value : best;
  }, 0);
}

function resolveWorkspaceAnalysisFlowRecommendation(baselineEntry, candidateEntry, rowState) {
  const flow = resolveWorkspaceAnalysisFlow();
  if (!flow || !baselineEntry || !candidateEntry || !rowState) {
    return null;
  }
  const compareSummary = rowState.sweepComparison && rowState.sweepComparison.compare_summary
    ? rowState.sweepComparison.compare_summary
    : null;
  const groupedDeltaMagnitude = ((compareSummary && compareSummary.scalar_delta_groups) || [])
    .reduce((total, group) => total + ((group.scalar_deltas || []).reduce((groupTotal, scalarDelta) => (
      groupTotal + Math.abs(Number(scalarDelta.delta_value || 0))
    ), 0)), 0);
  const pressureMagnitude = Math.max(
    Math.abs(Number(compareSummary && compareSummary.bandwidth_pressure_compare
      && compareSummary.bandwidth_pressure_compare.peak_bandwidth_pressure
      && compareSummary.bandwidth_pressure_compare.peak_bandwidth_pressure.delta_value || 0)),
    Math.abs(Number(compareSummary && compareSummary.vmem_pressure_compare
      && compareSummary.vmem_pressure_compare.hottest_region_utilization
      && compareSummary.vmem_pressure_compare.hottest_region_utilization.delta_value || 0)),
  );
  const estimatedLayerMagnitude = maxAbsoluteLayerDelta(
    rowState.sweepComparison ? rowState.sweepComparison.layer_deltas : [],
    "delta_cycles",
  );
  const fittedLayerMagnitude = maxAbsoluteLayerDelta(
    rowState.sweepComparison ? rowState.sweepComparison.fitted_layer_deltas : [],
    "delta_fitted_work_cycles",
  );
  const topLineMagnitude = Math.abs(Number(rowState.delta || 0));
  const ratioMagnitude = Math.abs(Number((rowState.ratio || 1) - 1));
  const score = flow.preset_id === "summary-vs-estimated-layer"
    ? (topLineMagnitude * 1.0) + (estimatedLayerMagnitude * 0.5) + (ratioMagnitude * 100)
    : flow.preset_id === "grouped-vs-estimated-layer"
      ? (groupedDeltaMagnitude * 1.0) + (estimatedLayerMagnitude * 0.5)
      : (pressureMagnitude * 1000) + (fittedLayerMagnitude * 0.5) + (estimatedLayerMagnitude * 0.1);
  const reason = flow.preset_id === "summary-vs-estimated-layer"
    ? `Top-line delta ${formatMetricDelta(rowState.delta)} with strongest estimated-layer delta ${formatMetricValue(estimatedLayerMagnitude)} cycles.`
    : flow.preset_id === "grouped-vs-estimated-layer"
      ? `Grouped metric movement ${formatMetricValue(groupedDeltaMagnitude)} with strongest estimated-layer delta ${formatMetricValue(estimatedLayerMagnitude)} cycles.`
      : `Pressure shift ${formatMetricValue(pressureMagnitude)} with strongest fitted-layer delta ${formatMetricValue(fittedLayerMagnitude)} cycles.`;
  return {
    flow_id: currentWorkspaceAnalysisFlow(),
    flow_label: flow.label,
    preset_id: flow.preset_id,
    score,
    reason,
  };
}

function recommendationTierForRank(rankIndex, recommendation) {
  if (!recommendation) {
    return "";
  }
  if (rankIndex === 0) {
    return "primary";
  }
  if (rankIndex < 3) {
    return "watch";
  }
  return "background";
}

function groupedCompareGroupIdsForFocus(compareFocus) {
  const mapping = {
    summary: ["headline"],
    "throughput-latency": ["throughput_latency"],
    "phase-shape": ["phase_shape"],
    "memory-pressure": ["memory_pressure"],
    "schedule-shape": ["schedule_shape"],
  };
  return mapping[compareFocus] || [];
}

function focusedGroupedScalarDeltaGroups(compareSummary) {
  const focusGroupIds = groupedCompareGroupIdsForFocus(currentCompareFocus());
  const groups = compareSummary.scalar_delta_groups || [];
  if (!focusGroupIds.length) {
    return [];
  }
  return groups.filter((group) => focusGroupIds.includes(group.group_id));
}

function currentLayerDeltaFocus() {
  const layerDeltaFocusFilter = document.querySelector("#catalog-layer-delta-focus-filter");
  return layerDeltaFocusFilter ? layerDeltaFocusFilter.value : "top-cycle";
}

function escapeSvgText(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function setCatalogWorkspaceActionStatus(message) {
  const status = document.querySelector("#catalog-workspace-action-status");
  if (status) {
    status.textContent = message;
  }
}

function workbenchPanelLabel(panel) {
  const labels = {
    summary: "Summary",
    timeline: "Timeline",
    memory: "Memory",
    coverage: "Coverage",
  };
  return labels[panel] || "Summary";
}

function buildWorkspaceRecommendationParams(workspaceState, entry) {
  const queue = workspaceState && workspaceState.baselineEntry
    ? resolveWorkspaceRecommendationQueue(
      workspaceState.baselineEntry,
      workspaceState.candidates,
      workspaceState.candidates.find((candidate) => candidate.entry_id === entry.entry_id)
        || workspaceState.focusedWorkspaceCandidate,
    )
    : null;
  return {
    compare_focus: currentCompareFocus(),
    layer_delta_focus: currentLayerDeltaFocus(),
    analysis_flow: currentWorkspaceAnalysisFlow(),
    sweep_candidate: queue && queue.focused_candidate_entry_id === entry.entry_id
      ? entry.target_profile_name
      : "",
    recommendation_queue_position: queue ? queue.queue_position : "",
    recommendation_prev_candidate: queue ? queue.previous_candidate_target_profile_name : "",
    recommendation_next_candidate: queue ? queue.next_candidate_target_profile_name : "",
    recommendation_top_candidates: queue ? queue.top_recommendation_target_profile_names.join(",") : "",
    recommendation_queue_candidates: queue ? queue.recommendation_queue_candidates.join(",") : "",
  };
}

function buildComparePanelLinks(entry) {
  const panel = currentWorkbenchPanel();
  const workspaceState = resolveCurrentWorkspaceState();
  const workbenchCompareParams = buildWorkspaceRecommendationParams(workspaceState, entry);
  const links = [
    `<a class="panel-link" href="${buildWorkbenchHref(entry.workbench_entry_path, panel, workbenchCompareParams)}">Open Selected Panel (${workbenchPanelLabel(panel)})</a>`,
  ];
  if (panel !== "summary") {
    links.push(`<a class="panel-link" href="${buildWorkbenchHref(entry.workbench_entry_path, "summary", workbenchCompareParams)}">Open Summary</a>`);
  }
  return `<div class="compare-link-row">${links.join("")}</div>`;
}

const MAX_SWEEP_LAYER_DELTA_ROWS = 3;
const MAX_GROUPED_COMPARE_ROWS = 3;

function formatMetricValue(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return String(value);
  }
  if (Number.isInteger(numeric) || Math.abs(numeric) >= 1000) {
    return `${numeric}`;
  }
  return numeric.toFixed(4).replace(/\\.?0+$/, "");
}

function formatMetricDelta(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "n/a";
  }
  if (numeric === 0) {
    return "0";
  }
  return `${numeric > 0 ? "+" : "-"}${formatMetricValue(Math.abs(numeric))}`;
}

""" + recommendation_detail_helpers + """

function orderedMetricEntries(entry) {
  return Object.entries(entry.metric_values || {}).sort(([left], [right]) => {
    if (left === entry.primary_metric_name && right !== entry.primary_metric_name) {
      return -1;
    }
    if (right === entry.primary_metric_name && left !== entry.primary_metric_name) {
      return 1;
    }
    return left.localeCompare(right);
  });
}

function renderMetricValueList(entry, emptyMessage = "No summary metrics.") {
  const rows = orderedMetricEntries(entry);
  if (!rows.length) {
    return `<p class="empty">${emptyMessage}</p>`;
  }
  return `<ul class="metric-detail-list">${rows.map(([name, value]) => `
    <li>
      <span>${name}</span>
      <strong>${formatMetricValue(value)}</strong>
    </li>
  `).join("")}</ul>`;
}

function buildSharedMetricDeltaRows(baselineEntry, candidateEntry) {
  const baselineMetrics = baselineEntry.metric_values || {};
  const candidateMetrics = candidateEntry.metric_values || {};
  const sharedMetricNames = Object.keys(baselineMetrics)
    .filter((name) => Object.prototype.hasOwnProperty.call(candidateMetrics, name))
    .sort((left, right) => {
      if (left === baselineEntry.primary_metric_name && right !== baselineEntry.primary_metric_name) {
        return -1;
      }
      if (right === baselineEntry.primary_metric_name && left !== baselineEntry.primary_metric_name) {
        return 1;
      }
      return left.localeCompare(right);
    });
  if (!sharedMetricNames.length) {
    return '<p class="empty">No shared summary metrics.</p>';
  }
  return `<ul class="metric-detail-list">${sharedMetricNames.map((name) => {
    const baselineValue = Number(baselineMetrics[name]);
    const candidateValue = Number(candidateMetrics[name]);
    const delta = candidateValue - baselineValue;
    const ratio = baselineValue !== 0 ? candidateValue / baselineValue : null;
    const scalarDelta = {
      metric_name: name,
      baseline_value: baselineValue,
      candidate_value: candidateValue,
      delta_value: delta,
    };
    return `
      <li>
        <span>${name}</span>
        <div class="metric-detail-values">
          ${buildScalarDeltaDirectionTag(scalarDelta)}
          <strong>${formatMetricDelta(delta)}</strong>
          <em>${ratio !== null ? `${ratio.toFixed(3)}x` : "n/a"}</em>
        </div>
      </li>
    `;
  }).join("")}</ul>`;
}

function metricImprovesWhenHigher(metricName) {
  const normalized = String(metricName || "").toLowerCase();
  return (
    normalized.includes("tokens_per_cycle")
    || normalized.includes("bytes_per_cycle")
    || normalized.includes("tokens_per_second")
    || normalized.includes("bytes_per_second")
    || normalized.includes("throughput")
  );
}

function scalarDeltaIsPositive(metricName, deltaValue) {
  return metricImprovesWhenHigher(metricName)
    ? deltaValue > 0
    : deltaValue < 0;
}

function buildDirectionTagMarkup(semanticClass, label) {
  if (semanticClass === "is-positive") {
    return `<span class="direction-tag is-positive">${label}</span>`;
  }
  if (semanticClass === "is-negative") {
    return `<span class="direction-tag is-negative">${label}</span>`;
  }
  return `<span class="direction-tag is-neutral">${label}</span>`;
}

function buildTitledDirectionTagMarkup(title, semanticClass, label) {
  if (semanticClass === "is-positive") {
    return `<span class="direction-tag is-positive" title="${title}">${label}</span>`;
  }
  if (semanticClass === "is-negative") {
    return `<span class="direction-tag is-negative" title="${title}">${label}</span>`;
  }
  return `<span class="direction-tag is-neutral" title="${title}">${label}</span>`;
}

function buildScalarDeltaDirectionTag(scalarDelta) {
  const deltaValue = Number(scalarDelta.delta_value || 0);
  if (!Number.isFinite(deltaValue) || deltaValue === 0) {
    return '<span class="direction-tag is-neutral">steady</span>';
  }
  const positive = scalarDeltaIsPositive(scalarDelta.metric_name, deltaValue);
  return positive
    ? '<span class="direction-tag is-positive">improved</span>'
    : '<span class="direction-tag is-negative">regressed</span>';
}

function buildTitledScalarDeltaDirectionTag(title, scalarDelta) {
  const deltaValue = Number(scalarDelta.delta_value || 0);
  if (!Number.isFinite(deltaValue) || deltaValue === 0) {
    return buildTitledDirectionTagMarkup(title, "is-neutral", "steady");
  }
  const positive = scalarDeltaIsPositive(scalarDelta.metric_name, deltaValue);
  return positive
    ? buildTitledDirectionTagMarkup(title, "is-positive", "improved")
    : buildTitledDirectionTagMarkup(title, "is-negative", "regressed");
}

function resolveWorkspacePrimaryScalarDelta(baselineEntry, candidateEntry) {
  const baselineValue = Number(baselineEntry.primary_metric_value || 0);
  const candidateValue = Number(candidateEntry.primary_metric_value || 0);
  return {
    metric_name: candidateEntry.primary_metric_name || baselineEntry.primary_metric_name || "",
    baseline_value: baselineValue,
    candidate_value: candidateValue,
    delta_value: candidateValue - baselineValue,
  };
}

function buildWorkspaceCompareSummaryTag(baselineEntry, candidateEntry) {
  return buildTitledScalarDeltaDirectionTag(
    "workspace summary",
    resolveWorkspacePrimaryScalarDelta(baselineEntry, candidateEntry),
  );
}

function buildWorkspaceCompareRatioSummaryTag(baselineEntry, candidateEntry) {
  return buildTitledScalarDeltaDirectionTag(
    "workspace ratio summary",
    resolveWorkspacePrimaryScalarDelta(baselineEntry, candidateEntry),
  );
}

function resolveWorkspaceSweepSummaryState(sweepComparison) {
  if (!sweepComparison || !(sweepComparison.layer_deltas || []).length) {
    return { semanticClass: "is-neutral", label: "none" };
  }
  const layerDeltas = sweepComparison.layer_deltas || [];
  const hasRegressions = layerDeltas.some((layerDelta) => Number(layerDelta.delta_cycles || 0) > 0);
  const hasNonRegressions = layerDeltas.some((layerDelta) => Number(layerDelta.delta_cycles || 0) <= 0);
  if (hasRegressions && hasNonRegressions) {
    return { semanticClass: "is-neutral", label: "mixed" };
  }
  if (hasRegressions) {
    return { semanticClass: "is-negative", label: "candidate regressions" };
  }
  return { semanticClass: "is-neutral", label: "none" };
}

function buildWorkspaceSweepSummaryTag(sweepComparison) {
  const summaryState = resolveWorkspaceSweepSummaryState(sweepComparison);
  return buildTitledDirectionTagMarkup(
    "workspace sweep summary",
    summaryState.semanticClass,
    summaryState.label,
  );
}

function resolveWorkspaceCompareRowState(baselineEntry, candidateEntry) {
  const sameMetric = candidateEntry.primary_metric_name === baselineEntry.primary_metric_name;
  const delta = candidateEntry.primary_metric_value - baselineEntry.primary_metric_value;
  const ratio = baselineEntry.primary_metric_value !== 0 ? candidateEntry.primary_metric_value / baselineEntry.primary_metric_value : null;
  const sweepComparison = resolveSweepComparison(baselineEntry, candidateEntry);
  const baseRowState = {
    sameMetric,
    delta,
    ratio,
    sweepComparison,
    workspaceSummaryTag: buildWorkspaceCompareSummaryTag(baselineEntry, candidateEntry),
    workspaceRatioSummaryTag: buildWorkspaceCompareRatioSummaryTag(baselineEntry, candidateEntry),
    workspaceSweepSummaryTag: buildWorkspaceSweepSummaryTag(sweepComparison),
  };
  return {
    ...baseRowState,
    analysisFlowRecommendation: resolveWorkspaceAnalysisFlowRecommendation(
      baselineEntry,
      candidateEntry,
      baseRowState,
    ),
  };
}

function renderWorkspaceSummaryCell(tagMarkup, contentMarkup) {
  return `<td>${renderWorkspaceSummaryStack(tagMarkup, contentMarkup)}</td>`;
}

function buildWorkspaceRowSectionFocusLink(candidateEntry, sectionId, label) {
  return `
    <div class="compare-link-row">
      <a class="panel-link" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: candidateEntry.entry_id, workspace_detail_focus: sectionId, workspace_secondary_detail_focus: "", workspace_detail_preset: "" })}">Focus Compare Section: ${label}</a>
    </div>
  `;
}

function buildWorkspaceRowPresetLink(candidateEntry, presetId, label) {
  return `
    <div class="compare-link-row">
      <a class="panel-link" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: candidateEntry.entry_id, workspace_detail_preset: presetId })}">Open Compare Preset: ${label}</a>
    </div>
  `;
}

function buildWorkspaceRowAnalysisFlowLink(candidateEntry, flowId, label) {
  return `
    <div class="compare-link-row">
      <a class="panel-link" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: candidateEntry.entry_id, workspace_analysis_flow: flowId, workspace_detail_preset: "" })}">Open Analysis Flow: ${label}</a>
    </div>
  `;
}

function buildWorkspaceSweepSummaryContent(baselineEntry, candidateEntry, sweepComparison) {
  return `${buildWorkspaceRowSectionFocusLink(candidateEntry, "estimated-layer", "Estimated Layer Deltas")}${buildWorkspaceRowPresetLink(candidateEntry, "summary-vs-estimated-layer", "Summary vs Estimated Layer")}${buildWorkspaceRowAnalysisFlowLink(candidateEntry, "summary-hotspots", "Summary Hotspots")}${renderSweepComparisonSummary(sweepComparison)}${buildSweepDrilldownLink(baselineEntry, candidateEntry)}${renderSweepLayerDeltaRows(baselineEntry, candidateEntry, sweepComparison)}${buildWorkspaceCompareDrilldownContent(baselineEntry, candidateEntry, sweepComparison)}`;
}

function buildWorkspacePrimaryDeltaContent(candidateEntry, sameMetric, deltaValue) {
  return `${sameMetric ? formatMetricDelta(deltaValue) : "metric mismatch"}${buildWorkspaceRowSectionFocusLink(candidateEntry, "summary", "Summary Compare")}`;
}

function buildWorkspacePrimaryRatioContent(candidateEntry, sameMetric, ratioValue) {
  return `${sameMetric && ratioValue !== null ? `${ratioValue.toFixed(3)}x` : "n/a"}${buildWorkspaceRowSectionFocusLink(candidateEntry, "summary", "Summary Compare")}`;
}

function buildWorkspaceSharedMetricContent(baselineEntry, candidateEntry, sweepComparison) {
  return `${buildWorkspaceRowSectionFocusLink(candidateEntry, "grouped-metrics", "Grouped Metric Deltas")}${buildWorkspaceRowPresetLink(candidateEntry, "grouped-vs-estimated-layer", "Grouped Metrics vs Estimated Layer")}${buildWorkspaceRowAnalysisFlowLink(candidateEntry, "grouped-hotspots", "Grouped Hotspots")}${buildMatchedCompareSummaryRows(baselineEntry, candidateEntry, sweepComparison)}`;
}

function renderWorkspaceSummaryStack(tagMarkup, contentMarkup) {
  return `
      <div class="summary-stack">
        ${tagMarkup}
        <div class="summary-stack-value">${contentMarkup}</div>
    </div>
  `;
}

function renderScalarDeltaListItems(scalarDeltas) {
  return (scalarDeltas || []).map((scalarDelta) => `
      <li>
        <span>${scalarDelta.metric_name}</span>
        <div class="metric-detail-values">
          ${buildScalarDeltaDirectionTag(scalarDelta)}
          <strong>${formatMetricDelta(scalarDelta.delta_value)}</strong>
          <em>${formatMetricValue(scalarDelta.baseline_value)} -> ${formatMetricValue(scalarDelta.candidate_value)}</em>
        </div>
      </li>
    `).join("");
}

function hasScalarDeltaGroups(compareSummary) {
  return (compareSummary.scalar_delta_groups || []).some(
    (group) => (group.scalar_deltas || []).length
  );
}

function orderedGroupedScalarDeltas(scalarDeltas) {
  return [...(scalarDeltas || [])].sort((left, right) => {
    const ratioDiff = Math.abs(Number(right.delta_ratio || 0)) - Math.abs(Number(left.delta_ratio || 0));
    if (ratioDiff !== 0) {
      return ratioDiff;
    }
    const valueDiff = Math.abs(Number(right.delta_value || 0)) - Math.abs(Number(left.delta_value || 0));
    if (valueDiff !== 0) {
      return valueDiff;
    }
    return String(left.metric_name || "").localeCompare(String(right.metric_name || ""));
  });
}

function buildGroupedScalarDirectionTag(group, scalarDeltas) {
  const leadScalar = (scalarDeltas || [])[0];
  if (!leadScalar) {
    return "";
  }
  const deltaValue = Number(leadScalar.delta_value || 0);
  if (!Number.isFinite(deltaValue) || deltaValue === 0) {
    return buildDirectionTagMarkup("is-neutral", "steady");
  }
  const metricName = String(leadScalar.metric_name || "");
  const groupId = String(group.group_id || "");
  if (groupId === "headline" || groupId === "throughput_latency") {
    const faster = scalarDeltaIsPositive(metricName, deltaValue);
    return faster
      ? buildDirectionTagMarkup("is-positive", "candidate faster")
      : buildDirectionTagMarkup("is-negative", "candidate slower");
  }
  if (groupId === "memory_pressure") {
    return deltaValue > 0
      ? buildDirectionTagMarkup("is-negative", "pressure up")
      : buildDirectionTagMarkup("is-positive", "pressure down");
  }
  if (groupId === "schedule_shape") {
    return deltaValue > 0
      ? buildDirectionTagMarkup("is-neutral", "schedule shifted up")
      : buildDirectionTagMarkup("is-neutral", "schedule shifted down");
  }
  return deltaValue > 0
    ? buildDirectionTagMarkup("is-neutral", "shifted up")
    : buildDirectionTagMarkup("is-neutral", "shifted down");
}

function renderGroupedScalarDeltaSection(group) {
  const scalarDeltas = orderedGroupedScalarDeltas(group.scalar_deltas || []);
  if (!scalarDeltas.length) {
    return "";
  }
  const visibleRows = scalarDeltas.slice(0, MAX_GROUPED_COMPARE_ROWS);
  const hiddenRows = scalarDeltas.slice(MAX_GROUPED_COMPARE_ROWS);
  const directionTag = buildGroupedScalarDirectionTag(group, scalarDeltas);
  const overflowDetails = hiddenRows.length
    ? `
      <details class="compare-summary-details">
        <summary>Show all ${scalarDeltas.length} metrics</summary>
        <ul class="metric-detail-list">${renderScalarDeltaListItems(hiddenRows)}</ul>
      </details>
    `
    : "";
  return `
      <section class="compare-summary-group">
        <div class="compare-group-heading">
          <p class="muted">${group.title || group.group_id}</p>
          ${directionTag}
        </div>
        <ul class="metric-detail-list">${renderScalarDeltaListItems(visibleRows)}</ul>
        ${overflowDetails}
      </section>
    `;
}

function renderScalarDeltaGroups(compareSummary) {
  return focusedGroupedScalarDeltaGroups(compareSummary)
    .filter((group) => (group.scalar_deltas || []).length)
    .map((group) => renderGroupedScalarDeltaSection(group))
    .join("");
}

function renderPressureCompareLabelRow(label, deltaView) {
  if (!deltaView) {
    return "";
  }
  const baselineValue = deltaView.baseline_value || "n/a";
  const candidateValue = deltaView.candidate_value || "n/a";
  const changed = Boolean(deltaView.changed);
  const directionTag = changed
    ? buildDirectionTagMarkup("is-neutral", "changed")
    : buildDirectionTagMarkup("is-neutral", "steady");
  return `
      <li>
        <span>${label}</span>
        <div class="metric-detail-values">
          ${directionTag}
          <strong>${candidateValue}</strong>
          <em>${baselineValue} -> ${candidateValue}</em>
        </div>
      </li>
    `;
}

function renderPressureCompareScalarRow(label, scalarDelta) {
  if (!scalarDelta) {
    return "";
  }
  return `
      <li>
        <span>${label}</span>
        <div class="metric-detail-values">
          ${buildScalarDeltaDirectionTag(scalarDelta)}
          <strong>${formatMetricDelta(scalarDelta.delta_value)}</strong>
          <em>${formatMetricValue(scalarDelta.baseline_value)} -> ${formatMetricValue(scalarDelta.candidate_value)}</em>
        </div>
      </li>
    `;
}

function renderPressureCompareSummary(compareSummary) {
  if (!["summary", "memory-pressure"].includes(currentCompareFocus())) {
    return "";
  }
  const bandwidth = compareSummary.bandwidth_pressure_compare;
  const vmem = compareSummary.vmem_pressure_compare;
  if (!bandwidth && !vmem) {
    return "";
  }
  const bandwidthRows = [
    renderPressureCompareScalarRow("Peak Bandwidth Pressure", bandwidth && bandwidth.peak_bandwidth_pressure),
    renderPressureCompareLabelRow("Peak Pressure Subject", bandwidth && bandwidth.peak_pressure_subject_id),
    renderPressureCompareLabelRow("Read Backing Store", bandwidth && bandwidth.dominant_read_backing_store),
    renderPressureCompareLabelRow("Write Memory Class", bandwidth && bandwidth.dominant_write_memory_class),
  ].filter(Boolean).join("");
  const vmemRows = [
    renderPressureCompareLabelRow("Hottest Region", vmem && vmem.hottest_region),
    renderPressureCompareScalarRow("Region Utilization", vmem && vmem.hottest_region_utilization),
    renderPressureCompareLabelRow("Region Memory Class", vmem && vmem.hottest_region_dominant_memory_class),
    renderPressureCompareLabelRow("Region Backing Store", vmem && vmem.hottest_region_dominant_backing_store),
  ].filter(Boolean).join("");
  return `
    <section class="compare-summary-group">
      <div class="compare-group-heading">
        <p class="muted">Peak Bandwidth Pressure</p>
      </div>
      <ul class="metric-detail-list">${bandwidthRows || '<li class="empty-cell">No bandwidth pressure compare.</li>'}</ul>
    </section>
    <section class="compare-summary-group">
      <div class="compare-group-heading">
        <p class="muted">VMEM Pressure Shifts</p>
      </div>
      <ul class="metric-detail-list">${vmemRows || '<li class="empty-cell">No VMEM pressure compare.</li>'}</ul>
    </section>
  `;
}

function buildWorkspaceDetailFocusLink(sectionId, label) {
  const isActive = currentWorkspaceDetailFocus() === sectionId;
  return `<a class="panel-link workspace-detail-focus-link${isActive ? " is-active" : ""}" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: currentWorkspaceCandidate(), workspace_detail_focus: sectionId, workspace_secondary_detail_focus: "", workspace_detail_preset: "" })}">Focus Compare Section: ${label}${isActive ? " (Active)" : ""}</a>`;
}

function buildWorkspaceDetailPresetLink(presetId, label) {
  const isActive = currentWorkspaceDetailPreset() === presetId;
  return `<a class="panel-link workspace-detail-preset-link${isActive ? " is-active" : ""}" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: currentWorkspaceCandidate(), workspace_detail_preset: presetId, workspace_analysis_flow: "" })}">${label}${isActive ? " (Active)" : ""}</a>`;
}

function renderWorkspaceDetailPresetLinks() {
  return `
    <div class="compare-link-row">
      ${buildWorkspaceDetailPresetLink("summary-vs-estimated-layer", "Summary vs Estimated Layer")}
      ${buildWorkspaceDetailPresetLink("grouped-vs-estimated-layer", "Grouped Metrics vs Estimated Layer")}
      ${buildWorkspaceDetailPresetLink("pressure-vs-fitted-layer", "Pressure vs Fitted Layer")}
    </div>
  `;
}

function buildWorkspaceAnalysisFlowLink(flowId, label) {
  const isActive = currentWorkspaceAnalysisFlow() === flowId;
  return `<a class="panel-link workspace-analysis-flow-link${isActive ? " is-active" : ""}" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: currentWorkspaceCandidate(), workspace_analysis_flow: flowId, workspace_detail_preset: "" })}">${label}${isActive ? " (Active)" : ""}</a>`;
}

function renderWorkspaceAnalysisFlowLinks() {
  return `
    <div class="compare-link-row">
      ${buildWorkspaceAnalysisFlowLink("summary-hotspots", "Summary Hotspots")}
      ${buildWorkspaceAnalysisFlowLink("grouped-hotspots", "Grouped Hotspots")}
      ${buildWorkspaceAnalysisFlowLink("memory-regression", "Memory Regression")}
    </div>
  `;
}

function buildWorkspaceAnalysisFlowSummary() {
  const flow = resolveWorkspaceAnalysisFlow();
  if (!flow) {
    return '<p class="muted">No analysis flow selected.</p>';
  }
  return `
    <ul class="metric-detail-list">
      <li><span>Flow</span><div class="metric-detail-values"><strong>${flow.label}</strong><em>${currentWorkspaceAnalysisFlow()}</em></div></li>
      <li><span>Preset</span><div class="metric-detail-values"><strong>${flow.preset_id}</strong><em>${flow.primary} vs ${flow.secondary}</em></div></li>
    </ul>
  `;
}

function buildWorkspaceAnalysisFlowRecommendationSummary(rowState, recommendationRank) {
  const recommendation = rowState && rowState.analysisFlowRecommendation;
  if (!recommendation) {
    return '<p class="muted">No recommendation is available without an active analysis flow.</p>';
  }
  const recommendationTier = recommendationTierForRank(recommendationRank, recommendation);
  return `
    <ul class="metric-detail-list">
      <li><span>Recommended For Current Flow</span><div class="metric-detail-values"><strong>${recommendationTier}</strong><em>rank ${recommendationRank + 1}</em></div></li>
      <li><span>Reason</span><div class="metric-detail-values"><strong>${recommendation.reason}</strong><em>${recommendation.preset_id}</em></div></li>
      <li><span>Score</span><div class="metric-detail-values"><strong>${formatMetricValue(recommendation.score)}</strong><em>${recommendation.flow_label}</em></div></li>
    </ul>
  `;
}

function renderWorkspaceRecommendationBadge(rowState, recommendationRank) {
  const recommendation = rowState && rowState.analysisFlowRecommendation;
  if (!recommendation) {
    return "";
  }
  const tier = recommendationTierForRank(recommendationRank, recommendation);
  return `<p class="muted">Recommended For Current Flow: ${tier} (${recommendation.reason})</p>`;
}

function orderWorkspaceCandidatesForCurrentFlow(baselineEntry, candidates) {
  return [...(candidates || [])].sort((left, right) => {
    if (!currentWorkspaceAnalysisFlow()) {
      return left.primary_metric_value - right.primary_metric_value;
    }
    const leftRowState = resolveWorkspaceCompareRowState(baselineEntry, left);
    const rightRowState = resolveWorkspaceCompareRowState(baselineEntry, right);
    const leftScore = Number(leftRowState.analysisFlowRecommendation && leftRowState.analysisFlowRecommendation.score || 0);
    const rightScore = Number(rightRowState.analysisFlowRecommendation && rightRowState.analysisFlowRecommendation.score || 0);
    const scoreDiff = rightScore - leftScore;
    if (scoreDiff !== 0) {
      return scoreDiff;
    }
    return left.primary_metric_value - right.primary_metric_value;
  });
}

function resolveWorkspaceRecommendationQueue(baselineEntry, candidates, focusedCandidateEntry) {
  if (!baselineEntry || !currentWorkspaceAnalysisFlow()) {
    return null;
  }
  const rankedRecommendations = (candidates || []).map((entry, index) => {
    const rowState = resolveWorkspaceCompareRowState(baselineEntry, entry);
    const recommendation = rowState && rowState.analysisFlowRecommendation;
    return {
      entry,
      rowState,
      recommendation,
      queue_position: recommendation ? index + 1 : null,
    };
  }).filter((item) => item.recommendation);
  if (!rankedRecommendations.length) {
    return {
      queue_position: null,
      total_candidates: (candidates || []).length,
      recommended_candidate_count: 0,
      focused_candidate_entry_id: focusedCandidateEntry ? focusedCandidateEntry.entry_id : null,
      previous_candidate_entry_id: null,
      next_candidate_entry_id: null,
      top_recommendation_entry_ids: [],
      top_recommendations: [],
    };
  }
  const focusedIndex = rankedRecommendations.findIndex((item) => (
    focusedCandidateEntry && item.entry.entry_id === focusedCandidateEntry.entry_id
  ));
  const resolvedIndex = focusedIndex >= 0 ? focusedIndex : 0;
  const previousEntry = resolvedIndex > 0 ? rankedRecommendations[resolvedIndex - 1].entry : null;
  const nextEntry = resolvedIndex < rankedRecommendations.length - 1
    ? rankedRecommendations[resolvedIndex + 1].entry
    : null;
  return {
    queue_position: rankedRecommendations[resolvedIndex].queue_position,
    total_candidates: (candidates || []).length,
    recommended_candidate_count: rankedRecommendations.length,
    focused_candidate_entry_id: focusedCandidateEntry
      ? focusedCandidateEntry.entry_id
      : rankedRecommendations[resolvedIndex].entry.entry_id,
    previous_candidate_entry_id: previousEntry ? previousEntry.entry_id : null,
    next_candidate_entry_id: nextEntry ? nextEntry.entry_id : null,
    previous_candidate_target_profile_name: previousEntry ? previousEntry.target_profile_name : null,
    next_candidate_target_profile_name: nextEntry ? nextEntry.target_profile_name : null,
    recommendation_queue_candidates: rankedRecommendations.map((item) => item.entry.target_profile_name),
    top_recommendation_entry_ids: rankedRecommendations.slice(0, 3).map((item) => item.entry.entry_id),
    top_recommendation_target_profile_names: rankedRecommendations
      .slice(0, 3)
      .map((item) => item.entry.target_profile_name),
    top_recommendations: rankedRecommendations.slice(0, 3).map((item) => ({
      entry_id: item.entry.entry_id,
      run_id: item.entry.run_id,
      target_profile_name: item.entry.target_profile_name,
      queue_position: item.queue_position,
      recommendation_tier: recommendationTierForRank(item.queue_position - 1, item.recommendation),
      recommendation_reason: item.recommendation.reason,
      recommendation_score: item.recommendation.score,
      is_focused: Boolean(
        focusedCandidateEntry && focusedCandidateEntry.entry_id === item.entry.entry_id,
      ),
    })),
  };
}

function buildWorkspaceRecommendationDetailEntries(baselineEntry, candidates, focusedCandidateEntry) {
  if (!baselineEntry || !focusedCandidateEntry || !currentWorkspaceAnalysisFlow()) {
    return [];
  }
  const recommendationQueue = resolveWorkspaceRecommendationQueue(
    baselineEntry,
    candidates,
    focusedCandidateEntry,
  );
  if (!recommendationQueue || !(recommendationQueue.top_recommendation_entry_ids || []).length) {
    return [];
  }
  return recommendationQueue.top_recommendation_entry_ids.map((entryId, index) => {
    const candidateEntry = (candidates || []).find((entry) => entry.entry_id === entryId);
    if (!candidateEntry) {
      return null;
    }
    const rowState = resolveWorkspaceCompareRowState(baselineEntry, candidateEntry);
    const recommendation = rowState && rowState.analysisFlowRecommendation;
    const sweepComparison = rowState && rowState.sweepComparison;
    const topLayer = orderedSweepLayerDeltas((sweepComparison && sweepComparison.layer_deltas) || [])[0] || null;
    const topFittedLayer = orderedSweepLayerDeltas((sweepComparison && sweepComparison.fitted_layer_deltas) || [])[0] || null;
    const layerSummary = buildRecommendationDetailLayerSummary(topLayer, topFittedLayer, formatMetricDelta);
    return {
      entry_id: candidateEntry.entry_id,
      run_id: candidateEntry.run_id,
      target_profile_name: candidateEntry.target_profile_name,
      queue_position: index + 1,
      recommendation_tier: recommendation ? recommendationTierForRank(index, recommendation) : "",
      recommendation_reason: recommendation ? recommendation.reason : "",
      recommendation_score: recommendation ? recommendation.score : null,
      is_focused: candidateEntry.entry_id === focusedCandidateEntry.entry_id,
      estimated_layer_summary: layerSummary.estimated_layer_summary,
      fitted_layer_summary: layerSummary.fitted_layer_summary,
    };
  }).filter(Boolean);
}

function orderWorkspaceDrilldownSections(sections) {
  const preset = resolveWorkspaceDetailPreset();
  const activeSectionId = preset ? preset.primary : currentWorkspaceDetailFocus();
  const secondarySectionId = preset ? preset.secondary : currentWorkspaceSecondaryDetailFocus();
  return [...(sections || [])].sort((left, right) => {
    if (left.section_id === activeSectionId && right.section_id !== activeSectionId) {
      return -1;
    }
    if (right.section_id === activeSectionId && left.section_id !== activeSectionId) {
      return 1;
    }
    if (left.section_id === secondarySectionId && right.section_id !== secondarySectionId) {
      return -1;
    }
    if (right.section_id === secondarySectionId && left.section_id !== secondarySectionId) {
      return 1;
    }
    return left.title.localeCompare(right.title);
  });
}

function renderWorkspaceCompareDrilldownSection(sectionId, title, contentMarkup) {
  const content = contentMarkup || '<p class="empty">No compare details for this section.</p>';
  return `
    <section class="compare-summary-group${currentWorkspaceDetailFocus() === sectionId ? " is-focused-section" : ""}">
      <div class="compare-group-heading">
        <p class="muted">${title}</p>
        ${buildWorkspaceDetailFocusLink(sectionId, title)}
      </div>
      ${content}
    </section>
  `;
}

function renderWorkspaceLayerDrilldownRows(baselineEntry, candidateEntry, layerDeltas, mode) {
  const focus = currentLayerDeltaFocus();
  const fittedMode = mode === "fitted";
  const filteredLayerDeltas = fittedMode
    ? (
      focus === "fitted-regressions-only"
        ? (layerDeltas || []).filter((layerDelta) => Number(layerDelta.delta_fitted_work_cycles || 0) > 0)
        : (layerDeltas || [])
    )
    : (
      focus === "regressions-only"
        ? (layerDeltas || []).filter((layerDelta) => Number(layerDelta.delta_cycles || 0) > 0)
        : (layerDeltas || [])
    );
  const orderedLayerDeltas = [...filteredLayerDeltas].sort((left, right) => {
    const leftScore = fittedMode
      ? Math.abs(Number(left.delta_fitted_work_cycles || 0))
      : focus === "top-by-bytes"
        ? Math.abs(Number(left.delta_bytes || 0))
        : Math.abs(Number(left.delta_cycles || 0));
    const rightScore = fittedMode
      ? Math.abs(Number(right.delta_fitted_work_cycles || 0))
      : focus === "top-by-bytes"
        ? Math.abs(Number(right.delta_bytes || 0))
        : Math.abs(Number(right.delta_cycles || 0));
    const deltaDiff = rightScore - leftScore;
    if (deltaDiff !== 0) {
      return deltaDiff;
    }
    return Number(left.layer_id || 0) - Number(right.layer_id || 0);
  });
  const visibleLayerDeltas = orderedLayerDeltas.slice(0, MAX_SWEEP_LAYER_DELTA_ROWS);
  if (!visibleLayerDeltas.length) {
    return fittedMode
      ? '<p class="empty">No fitted layer deltas.</p>'
      : '<p class="empty">No estimated layer deltas.</p>';
  }
  const sortDescriptor = fittedMode
    ? "|delta_fitted_work_cycles|"
    : focus === "top-by-bytes"
      ? "|delta_bytes|"
      : "|delta_cycles|";
  const countDescriptor = fittedMode ? "fitted layers" : "estimated layers";
  const truncationNote = orderedLayerDeltas.length > MAX_SWEEP_LAYER_DELTA_ROWS
    ? `<p class="muted">Showing top 3 of ${orderedLayerDeltas.length} ${countDescriptor} by ${sortDescriptor}.</p>`
    : "";
  return `${truncationNote}<ul class="metric-detail-list">${visibleLayerDeltas.map((layerDelta) => `
    <li>
      <span>Layer ${layerDelta.layer_id}</span>
      <div class="metric-detail-values">
        ${fittedMode
          ? `<strong>${formatMetricDelta(layerDelta.delta_fitted_work_cycles)} fitted work cycles</strong>`
          : `<strong>${formatMetricDelta(layerDelta.delta_cycles)} cycles</strong>`
        }
        <em>${formatMetricDelta(layerDelta.delta_bytes)} bytes</em>
      </div>
      ${buildSweepLayerDrilldownLink(baselineEntry, candidateEntry, layerDelta.layer_id)}
    </li>
  `).join("")}</ul>`;
}

function buildMatchedCompareSummaryRows(baselineEntry, candidateEntry, sweepComparison) {
  if (!sweepComparison || !sweepComparison.compare_summary) {
    return buildSharedMetricDeltaRows(baselineEntry, candidateEntry);
  }
  const compareSummary = sweepComparison.compare_summary;
  const diffFields = (compareSummary.profile_diff_fields || []).join(", ");
  const highlightedRows = compareSummary.highlighted_scalar_deltas || [];
  const scalarRows = compareSummary.scalar_deltas || [];
  const groupedRows = hasScalarDeltaGroups(compareSummary)
    ? renderScalarDeltaGroups(compareSummary)
    : "";
  const pressureRows = renderPressureCompareSummary(compareSummary);
  const visibleRows = highlightedRows.length ? highlightedRows : scalarRows;
  if (!groupedRows && !pressureRows && !visibleRows.length) {
    return '<p class="empty">No matched Phase D compare summary rows.</p>';
  }
  const fullScalarDetails = scalarRows.length && (
    groupedRows || (highlightedRows.length && scalarRows.length > highlightedRows.length)
  )
    ? `
      <details class="compare-summary-details">
        <summary>All Scalar Deltas</summary>
        <ul class="metric-detail-list">${renderScalarDeltaListItems(scalarRows)}</ul>
      </details>
    `
    : "";
  return `
    <p class="muted">Schedule: ${compareSummary.baseline_schedule_kind} -> ${compareSummary.candidate_schedule_kind}</p>
    ${diffFields ? `<p class="muted">Profile Diff Fields: ${diffFields}</p>` : ""}
    ${groupedRows || `
      ${highlightedRows.length ? '<p class="muted">Highlighted Metric Shifts</p>' : ""}
      <ul class="metric-detail-list">${renderScalarDeltaListItems(visibleRows)}</ul>
    `}
    ${pressureRows}
    ${fullScalarDetails}
  `;
}

function buildWorkspaceCompareDrilldownContent(baselineEntry, candidateEntry, sweepComparison) {
  const compareSummary = sweepComparison && sweepComparison.compare_summary
    ? sweepComparison.compare_summary
    : null;
  const summaryContent = buildMatchedCompareSummaryRows(baselineEntry, candidateEntry, sweepComparison);
  const groupedScalarContent = compareSummary && hasScalarDeltaGroups(compareSummary)
    ? renderScalarDeltaGroups(compareSummary)
    : "";
  const pressureContent = compareSummary
    ? renderPressureCompareSummary(compareSummary)
    : "";
  const estimatedLayerContent = renderWorkspaceLayerDrilldownRows(
    baselineEntry,
    candidateEntry,
    sweepComparison ? sweepComparison.layer_deltas || [] : [],
    "estimated",
  );
  const fittedLayerContent = renderWorkspaceLayerDrilldownRows(
    baselineEntry,
    candidateEntry,
    sweepComparison ? sweepComparison.fitted_layer_deltas || [] : [],
    "fitted",
  );
  const orderedSections = orderWorkspaceDrilldownSections([
    {
      section_id: "summary",
      title: "Summary Compare",
      content: summaryContent,
    },
    {
      section_id: "grouped-metrics",
      title: "Grouped Metric Deltas",
      content: groupedScalarContent,
    },
    {
      section_id: "pressure",
      title: "Pressure Compare",
      content: pressureContent,
    },
    {
      section_id: "estimated-layer",
      title: "Estimated Layer Deltas",
      content: estimatedLayerContent,
    },
    {
      section_id: "fitted-layer",
      title: "Fitted Layer Deltas",
      content: fittedLayerContent,
    },
  ]);
  const preset = resolveWorkspaceDetailPreset();
  const activeSectionId = preset ? preset.primary : currentWorkspaceDetailFocus();
  const secondarySectionId = preset ? preset.secondary : currentWorkspaceSecondaryDetailFocus();
  const drilldownSections = orderedSections
    .filter((section, index) => {
      if (index === 0) {
        return true;
      }
      if (!secondarySectionId) {
        return section.section_id !== activeSectionId;
      }
      return section.section_id === secondarySectionId;
    })
    .filter((section, index, sections) =>
      sections.findIndex((candidate) => candidate.section_id === section.section_id) === index
    )
    .map((section) => renderWorkspaceCompareDrilldownSection(
      section.section_id,
      section.title,
      section.content,
    )).join("");
  if (!drilldownSections) {
    return "";
  }
  return `
    <details class="compare-summary-details">
      <summary>Workspace Compare Drilldown</summary>
      ${drilldownSections}
    </details>
  `;
}

function findSweepComparisonMatch(entry, baselineEntry, candidateEntry) {
  if (!entry || !baselineEntry || !candidateEntry) {
    return null;
  }
  const comparisons = entry.sweep_comparisons || [];
  const comparison = comparisons.find((comparison) =>
    entry.sweep_baseline_target_profile_name === baselineEntry.target_profile_name
    && comparison.candidate_target_profile_name === candidateEntry.target_profile_name
    && comparison.scenario_name === baselineEntry.scenario_name
    && comparison.scenario_name === candidateEntry.scenario_name
    && comparison.mode === baselineEntry.mode
    && comparison.mode === candidateEntry.mode
  );
  return comparison ? { sourceEntry: entry, comparison } : null;
}

function resolveSweepComparisonMatch(baselineEntry, candidateEntry) {
  return (
    findSweepComparisonMatch(baselineEntry, baselineEntry, candidateEntry)
    || findSweepComparisonMatch(candidateEntry, baselineEntry, candidateEntry)
    || null
  );
}

function resolveSweepComparison(baselineEntry, candidateEntry) {
  const match = resolveSweepComparisonMatch(baselineEntry, candidateEntry);
  return match ? match.comparison : null;
}

function orderedSweepLayerDeltas(layerDeltas) {
  const focus = currentLayerDeltaFocus();
  return [...(layerDeltas || [])].sort((left, right) => {
    const leftScore = focus === "top-by-bytes"
      ? Math.abs(Number(left.delta_bytes || 0))
      : focus === "top-by-fitted-work" || focus === "fitted-regressions-only"
        ? Math.abs(Number(left.delta_fitted_work_cycles || 0))
        : Math.abs(Number(left.delta_cycles || 0));
    const rightScore = focus === "top-by-bytes"
      ? Math.abs(Number(right.delta_bytes || 0))
      : focus === "top-by-fitted-work" || focus === "fitted-regressions-only"
        ? Math.abs(Number(right.delta_fitted_work_cycles || 0))
        : Math.abs(Number(right.delta_cycles || 0));
    const deltaDiff = rightScore - leftScore;
    if (deltaDiff !== 0) {
      return deltaDiff;
    }
    return Number(left.layer_id || 0) - Number(right.layer_id || 0);
  });
}

function selectSweepLayerDeltas(layerDeltas) {
  const focus = currentLayerDeltaFocus();
  const filteredLayerDeltas = focus === "regressions-only"
    ? (layerDeltas || []).filter((layerDelta) => Number(layerDelta.delta_cycles || 0) > 0)
    : focus === "fitted-regressions-only"
      ? (layerDeltas || []).filter((layerDelta) => Number(layerDelta.delta_fitted_work_cycles || 0) > 0)
      : (layerDeltas || []);
  return orderedSweepLayerDeltas(filteredLayerDeltas).slice(0, MAX_SWEEP_LAYER_DELTA_ROWS);
}

function buildSweepDrilldownLink(baselineEntry, candidateEntry) {
  const match = resolveSweepComparisonMatch(baselineEntry, candidateEntry);
  if (!match || !match.sourceEntry || !match.sourceEntry.workbench_entry_path) {
    return "";
  }
  const workbenchCompareParams = buildWorkspaceRecommendationParams(resolveCurrentWorkspaceState(), candidateEntry);
  return `<div class="compare-link-row"><a class="panel-link" href="${buildWorkbenchHref(match.sourceEntry.workbench_entry_path, "sweep", workbenchCompareParams)}">Open Sweep Panel (${match.sourceEntry.run_id})</a></div>`;
}

function buildSweepLayerDrilldownLink(baselineEntry, candidateEntry, layerId) {
  const match = resolveSweepComparisonMatch(baselineEntry, candidateEntry);
  if (!match || !match.sourceEntry || !match.sourceEntry.workbench_entry_path) {
    return "";
  }
  const workbenchCompareParams = {
    ...buildWorkspaceRecommendationParams(resolveCurrentWorkspaceState(), candidateEntry),
    sweep_candidate: candidateEntry.target_profile_name,
    sweep_layer_focus: layerId,
  };
  return `<a class="panel-link" href="${buildWorkbenchHref(match.sourceEntry.workbench_entry_path, "sweep", workbenchCompareParams)}">Open Layer In Sweep</a>`;
}

function renderSweepLayerDeltaRows(baselineEntry, candidateEntry, sweepComparison) {
  if (!sweepComparison) {
    return '<p class="empty">No matched sweep compare summary.</p>';
  }
  const sourceLayerDeltas = currentLayerDeltaFocus() === "top-by-fitted-work"
    || currentLayerDeltaFocus() === "fitted-regressions-only"
    ? (sweepComparison.fitted_layer_deltas || [])
    : (sweepComparison.layer_deltas || []);
  const orderedLayerDeltas = orderedSweepLayerDeltas(sourceLayerDeltas);
  const layerDeltas = selectSweepLayerDeltas(sourceLayerDeltas);
  const focus = currentLayerDeltaFocus();
  if (!layerDeltas.length) {
    return focus === "regressions-only"
      ? '<p class="empty">No candidate regression layers in matched sweep summary.</p>'
      : focus === "fitted-regressions-only"
        ? '<p class="empty">No fitted-work regression layers in matched sweep summary.</p>'
        : '<p class="empty">No matched sweep layer deltas.</p>';
  }
  const visibleLayerCount = focus === "regressions-only"
    ? sourceLayerDeltas.filter((layerDelta) => Number(layerDelta.delta_cycles || 0) > 0).length
    : focus === "fitted-regressions-only"
      ? sourceLayerDeltas.filter((layerDelta) => Number(layerDelta.delta_fitted_work_cycles || 0) > 0).length
    : orderedLayerDeltas.length;
  const sortDescriptor = focus === "top-by-bytes"
    ? "|delta_bytes|"
    : focus === "top-by-fitted-work" || focus === "fitted-regressions-only"
      ? "|delta_fitted_work_cycles|"
      : "|delta_cycles|";
  const countDescriptor = focus === "regressions-only"
    ? "regression layers"
    : focus === "fitted-regressions-only"
      ? "fitted regression layers"
      : "layers";
  const truncationNote = visibleLayerCount > MAX_SWEEP_LAYER_DELTA_ROWS
    ? `<p class="muted">Showing top 3 of ${visibleLayerCount} ${countDescriptor} by ${sortDescriptor}.</p>`
    : "";
  return `${truncationNote}<ul class="metric-detail-list">${layerDeltas.map((layerDelta) => `
    <li>
      <span>Layer ${layerDelta.layer_id}</span>
      <div class="metric-detail-values">
        <strong>${formatMetricDelta(layerDelta.delta_cycles)} cycles</strong>
        ${Object.prototype.hasOwnProperty.call(layerDelta, "delta_fitted_work_cycles")
          ? `<em>${formatMetricDelta(layerDelta.delta_fitted_work_cycles)} fitted work cycles</em>`
          : ""}
        <em>${formatMetricDelta(layerDelta.delta_bytes)} bytes</em>
      </div>
      ${buildSweepLayerDrilldownLink(baselineEntry, candidateEntry, layerDelta.layer_id)}
    </li>
  `).join("")}</ul>`;
}

function renderSweepComparisonSummary(sweepComparison) {
  if (!sweepComparison) {
    return '<p class="muted">No matched sweep compare summary.</p>';
  }
  const compareSummary = sweepComparison.compare_summary;
  const metricRows = compareSummary && hasScalarDeltaGroups(compareSummary)
    ? (compareSummary.scalar_delta_groups || [])
        .filter((group) => (group.scalar_deltas || []).length)
        .map((group) => {
          const scalarDelta = orderedGroupedScalarDeltas(group.scalar_deltas || [])[0];
          return [`${group.title || group.group_id}: ${scalarDelta.metric_name}`, scalarDelta.delta_value];
        })
    : compareSummary && (
      (compareSummary.highlighted_scalar_deltas || []).length
      || (compareSummary.scalar_deltas || []).length
    )
      ? (
        (compareSummary.highlighted_scalar_deltas || []).length
          ? (compareSummary.highlighted_scalar_deltas || [])
          : (compareSummary.scalar_deltas || [])
      ).map((scalarDelta) => [scalarDelta.metric_name, scalarDelta.delta_value])
      : Object.entries(sweepComparison.metric_deltas || {});
  if (!metricRows.length) {
    return '<p class="muted">No matched sweep metric deltas.</p>';
  }
  const focusLabels = {
    "top-cycle": "Top By Cycles",
    "regressions-only": "Candidate Regressions",
    "top-by-bytes": "Top By Bytes",
    "top-by-fitted-work": "Top By Fitted Work",
    "fitted-regressions-only": "Fitted Work Regressions",
  };
  return `<p class="muted">${focusLabels[currentLayerDeltaFocus()] || "Top By Cycles"} | ${metricRows.map(([name, delta]) => `${name}: ${formatMetricDelta(delta)}`).join(" | ")}</p>`;
}

function groupCatalogEntries(entries) {
  const groups = new Map();
  entries.forEach((entry) => {
    const key = entry.scenario_name;
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key).push(entry);
  });
  return Array.from(groups.entries()).sort(([left], [right]) => left.localeCompare(right));
}

function renderCatalogRows(entries) {
  const table = document.querySelector("#catalog-entry-table");
  if (!table) {
    return;
  }
  table.innerHTML = entries.map((entry) => `
    <tr data-mode="${entry.mode}" data-schedule="${entry.schedule_kind}">
      <td><button class="compare-toggle" data-entry-id="${entry.entry_id}" type="button">Compare</button></td>
      <td><a href="${buildWorkbenchLink(entry, "summary")}">${entry.run_id}</a></td>
      <td>${entry.scenario_name}</td>
      <td>${entry.mode}</td>
      <td>${entry.schedule_kind}</td>
      <td>${entry.target_profile_name}</td>
      <td>${entry.primary_metric_name}</td>
      <td>${entry.primary_metric_value}</td>
    </tr>
  `).join("");
  if (!entries.length) {
    table.innerHTML = '<tr><td colspan="8" class="empty-cell">No runs match the current filters.</td></tr>';
  }
}

function toggleCompareSelection(entryId) {
  const index = COMPARE_SELECTION.indexOf(entryId);
  if (index >= 0) {
    COMPARE_SELECTION.splice(index, 1);
    return;
  }
  if (COMPARE_SELECTION.length >= 2) {
    COMPARE_SELECTION.shift();
  }
  COMPARE_SELECTION.push(entryId);
}

function swapCompareSelectionOrder() {
  if (COMPARE_SELECTION.length < 2) {
    return;
  }
  COMPARE_SELECTION.splice(0, 2, COMPARE_SELECTION[1], COMPARE_SELECTION[0]);
}

function buildCompareSummary(selectedEntries) {
  if (!selectedEntries.length) {
    return '<p class="empty">Select one or two runs to compare primary metrics.</p>';
  }
  if (selectedEntries.length === 1) {
    const entry = selectedEntries[0];
    return `
      <article class="compare-card">
        <h3>${entry.run_id}</h3>
        <p>${entry.scenario_name} · ${entry.schedule_kind}</p>
        <p>${entry.primary_metric_name}: <strong>${entry.primary_metric_value}</strong></p>
        <h4>Available Metrics</h4>
        ${renderMetricValueList(entry)}
        ${buildComparePanelLinks(entry)}
      </article>
    `;
  }

  const [baseline, candidate] = selectedEntries;
  const sameMetric = baseline.primary_metric_name === candidate.primary_metric_name;
  const delta = candidate.primary_metric_value - baseline.primary_metric_value;
  const ratio = baseline.primary_metric_value !== 0 ? candidate.primary_metric_value / baseline.primary_metric_value : null;
  const sweepComparison = resolveSweepComparison(baseline, candidate);
  return `
    <article class="compare-card compare-grid">
      <div>
        <h3>Baseline</h3>
        <p>${baseline.run_id}</p>
        <p>${baseline.primary_metric_name}: <strong>${baseline.primary_metric_value}</strong></p>
        ${renderMetricValueList(baseline)}
        ${buildComparePanelLinks(baseline)}
      </div>
      <div>
        <h3>Candidate</h3>
        <p>${candidate.run_id}</p>
        <p>${candidate.primary_metric_name}: <strong>${candidate.primary_metric_value}</strong></p>
        ${renderMetricValueList(candidate)}
        ${buildComparePanelLinks(candidate)}
      </div>
      <div>
        <h3>Shared Metric Deltas</h3>
        <p>${sameMetric ? `${candidate.primary_metric_name} delta: ${formatMetricDelta(delta)}` : "Metric mismatch"}</p>
        <p>${sameMetric && ratio !== null ? `ratio: ${ratio.toFixed(3)}x` : "ratio unavailable"}</p>
        ${buildMatchedCompareSummaryRows(baseline, candidate, sweepComparison)}
      </div>
      <div>
        <h3>Sweep Layer Deltas</h3>
        ${renderSweepComparisonSummary(sweepComparison)}
        ${buildSweepDrilldownLink(baseline, candidate)}
        ${renderSweepLayerDeltaRows(baseline, candidate, sweepComparison)}
      </div>
    </article>
  `;
}

function renderCompareTray(entries) {
  const container = document.querySelector("#catalog-compare-content");
  if (!container) {
    return;
  }
  const selectedEntries = COMPARE_SELECTION
    .map((entryId) => entries.find((entry) => entry.entry_id === entryId))
    .filter(Boolean);
  container.innerHTML = buildCompareSummary(selectedEntries);
}

function currentCompareScope() {
  const scopeFilter = document.querySelector("#catalog-compare-scope-filter");
  return scopeFilter ? scopeFilter.value : "same-scenario";
}

function resolveCurrentWorkspaceState() {
  const state = serializeCatalogState();
  const visibleEntries = filterCatalogEntries(
    CATALOG_ENTRIES,
    state.search,
    state.mode,
    state.schedule,
  );
  const baselineEntryId = COMPARE_SELECTION[0];
  const baselineEntry = visibleEntries.find((entry) => entry.entry_id === baselineEntryId)
    || CATALOG_ENTRIES.find((entry) => entry.entry_id === baselineEntryId)
    || null;
  if (!baselineEntry) {
    CURRENT_WORKSPACE_CANDIDATE_ID = "";
    return {
      baselineEntry: null,
      visibleEntries,
      candidates: [],
      compareScope: currentCompareScope(),
      focusedWorkspaceCandidate: null,
      focusedWorkspaceDetailFocus: currentWorkspaceDetailFocus(),
      focusedWorkspaceSecondaryDetailFocus: currentWorkspaceSecondaryDetailFocus(),
      focusedWorkspaceDetailPreset: currentWorkspaceDetailPreset(),
      focusedWorkspaceAnalysisFlow: currentWorkspaceAnalysisFlow(),
      focusedSweepCandidate: null,
      focusedSweepLayer: null,
      focusedCompareFocus: currentCompareFocus(),
      focusedLayerDeltaMode: currentLayerDeltaFocus(),
    };
  }
  const urlParams = new URLSearchParams(window.location.search);
  const candidates = orderWorkspaceCandidatesForCurrentFlow(
    baselineEntry,
    buildWorkspaceCandidateSet(baselineEntry, visibleEntries, currentCompareScope()),
  );
  const focusedWorkspaceCandidate = resolveFocusedWorkspaceCandidate(
    candidates,
    currentWorkspaceCandidate() || urlParams.get("workspace_candidate") || "",
  );
  CURRENT_WORKSPACE_CANDIDATE_ID = focusedWorkspaceCandidate ? focusedWorkspaceCandidate.entry_id : "";
  return {
    baselineEntry,
    visibleEntries,
    candidates,
    compareScope: currentCompareScope(),
    focusedWorkspaceCandidate,
    focusedWorkspaceDetailFocus: currentWorkspaceDetailFocus(),
    focusedWorkspaceSecondaryDetailFocus: currentWorkspaceSecondaryDetailFocus(),
    focusedWorkspaceDetailPreset: currentWorkspaceDetailPreset(),
    focusedWorkspaceAnalysisFlow: currentWorkspaceAnalysisFlow(),
    focusedSweepCandidate: urlParams.get("sweep_candidate") || null,
    focusedSweepLayer: urlParams.get("sweep_layer_focus") || null,
    focusedCompareFocus: currentCompareFocus(),
    focusedLayerDeltaMode: currentLayerDeltaFocus(),
  };
}

function buildCurrentCatalogWorkspaceUrl(extraState = {}) {
  return buildCatalogReturnUrl(extraState);
}

async function copyCurrentWorkspaceLink() {
  const url = buildCurrentCatalogWorkspaceUrl();
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(url);
    setCatalogWorkspaceActionStatus("Workspace view link copied.");
    return;
  }
  setCatalogWorkspaceActionStatus(`Workspace view link ready: ${url}`);
}

function buildWorkspaceExportData() {
  const workspaceState = resolveCurrentWorkspaceState();
  const baselineEntry = workspaceState.baselineEntry;
  const focusedWorkspaceCandidate = workspaceState.focusedWorkspaceCandidate;
  const recommendationQueue = resolveWorkspaceRecommendationQueue(
    baselineEntry,
    workspaceState.candidates,
    focusedWorkspaceCandidate,
  );
  const focusedWorkspaceRowState = baselineEntry && focusedWorkspaceCandidate
    ? resolveWorkspaceCompareRowState(baselineEntry, focusedWorkspaceCandidate)
    : null;
  const focusedWorkspaceRecommendationRank = focusedWorkspaceCandidate
    ? workspaceState.candidates.findIndex((entry) => entry.entry_id === focusedWorkspaceCandidate.entry_id)
    : -1;
  const recommendationDetails = buildWorkspaceRecommendationDetailEntries(
    baselineEntry,
    workspaceState.candidates,
    focusedWorkspaceCandidate,
  );
  const snapshotHeaderRows = [
    {
      label: "Focused Compare Scope",
      value: workspaceState.compareScope,
    },
    {
      label: "Focused Compare Focus",
      value: currentCompareFocusLabel(),
    },
    {
      label: "Focused Layer Delta Mode",
      value: workspaceState.focusedLayerDeltaMode,
    },
    {
      label: "Focused Workspace Detail",
      value: currentWorkspaceDetailFocusLabel(),
    },
    {
      label: "Focused Workspace Compare-Against Detail",
      value: currentWorkspaceSecondaryDetailFocusLabel() || "none",
    },
    {
      label: "Focused Workspace Compare Preset",
      value: workspaceState.focusedWorkspaceDetailPreset || "none",
    },
    {
      label: "Focused Workspace Analysis Flow",
      value: workspaceState.focusedWorkspaceAnalysisFlow || "none",
    },
    {
      label: "Focused Workspace Analysis Flow Summary",
      value: workspaceState.focusedWorkspaceAnalysisFlow
        ? `${workspaceState.focusedWorkspaceAnalysisFlow} -> ${currentWorkspaceDetailFocusLabel()}${currentWorkspaceSecondaryDetailFocusLabel() ? ` + ${currentWorkspaceSecondaryDetailFocusLabel()}` : ""}`
        : "none",
    },
    {
      label: "Focused Workspace Analysis Recommendation",
      value: focusedWorkspaceRowState && focusedWorkspaceRowState.analysisFlowRecommendation
        ? `${recommendationTierForRank(focusedWorkspaceRecommendationRank, focusedWorkspaceRowState.analysisFlowRecommendation)} -> ${focusedWorkspaceRowState.analysisFlowRecommendation.reason}`
        : "none",
    },
    {
      label: "Focused Baseline",
      value: baselineEntry ? baselineEntry.run_id : "unselected",
    },
    {
      label: "Focused Candidate Count",
      value: String(workspaceState.candidates.length),
    },
  ];
  if (focusedWorkspaceCandidate) {
    snapshotHeaderRows.push({
      label: "Focused Workspace Candidate",
      value: `${focusedWorkspaceCandidate.run_id} (${focusedWorkspaceCandidate.target_profile_name})`,
    });
  }
  if (recommendationQueue && recommendationQueue.recommended_candidate_count) {
    snapshotHeaderRows.push({
      label: "Recommendation Queue",
      value: `${recommendationQueue.queue_position || "n/a"} of ${recommendationQueue.recommended_candidate_count}`,
    });
    snapshotHeaderRows.push({
      label: "Top Recommended Candidates",
      value: recommendationQueue.top_recommendation_entry_ids.join(", "),
    });
  }
  if (recommendationDetails.length) {
    snapshotHeaderRows.push({
      label: "Top Recommendation Detail Candidates",
      value: recommendationDetails.map((detail) => detail.run_id).join(", "),
    });
  }
  if (workspaceState.focusedSweepCandidate) {
    snapshotHeaderRows.push({
      label: "Focused Sweep Candidate",
      value: workspaceState.focusedSweepCandidate,
    });
  }
  if (workspaceState.focusedSweepLayer) {
    snapshotHeaderRows.push({
      label: "Focused Sweep Layer",
      value: workspaceState.focusedSweepLayer,
    });
  }
  return {
    exported_at: new Date().toISOString(),
    workspace_url: buildCurrentCatalogWorkspaceUrl(),
    compare_scope: workspaceState.compareScope,
    compare_focus: workspaceState.focusedCompareFocus,
    layer_delta_focus: workspaceState.focusedLayerDeltaMode,
    focused_workspace_detail_focus: workspaceState.focusedWorkspaceDetailFocus,
    focused_workspace_secondary_detail_focus: workspaceState.focusedWorkspaceSecondaryDetailFocus,
    focused_workspace_detail_preset: workspaceState.focusedWorkspaceDetailPreset,
    focused_workspace_analysis_flow: workspaceState.focusedWorkspaceAnalysisFlow,
    focused_workspace_analysis_flow_summary: workspaceState.focusedWorkspaceAnalysisFlow
      ? {
        flow_id: workspaceState.focusedWorkspaceAnalysisFlow,
        primary_detail: currentWorkspaceDetailFocusLabel(),
        secondary_detail: currentWorkspaceSecondaryDetailFocusLabel() || null,
      }
      : null,
    focused_workspace_analysis_recommendation: focusedWorkspaceRowState && focusedWorkspaceRowState.analysisFlowRecommendation
      ? {
        recommendation_tier: recommendationTierForRank(focusedWorkspaceRecommendationRank, focusedWorkspaceRowState.analysisFlowRecommendation),
        recommendation_rank: focusedWorkspaceRecommendationRank + 1,
        recommendation_reason: focusedWorkspaceRowState.analysisFlowRecommendation.reason,
        recommendation_score: focusedWorkspaceRowState.analysisFlowRecommendation.score,
      }
      : null,
    focused_workspace_recommendation_queue: recommendationQueue
      ? {
        queue_position: recommendationQueue.queue_position,
        total_candidates: recommendationQueue.total_candidates,
        recommended_candidate_count: recommendationQueue.recommended_candidate_count,
        previous_candidate_entry_id: recommendationQueue.previous_candidate_entry_id,
        next_candidate_entry_id: recommendationQueue.next_candidate_entry_id,
        top_recommendation_entry_ids: recommendationQueue.top_recommendation_entry_ids,
      }
      : null,
    focused_workspace_recommendation_details: recommendationDetails,
    baseline_entry_id: baselineEntry ? baselineEntry.entry_id : null,
    baseline_run_id: baselineEntry ? baselineEntry.run_id : null,
    focused_workspace_candidate: focusedWorkspaceCandidate ? {
      entry_id: focusedWorkspaceCandidate.entry_id,
      run_id: focusedWorkspaceCandidate.run_id,
      target_profile_name: focusedWorkspaceCandidate.target_profile_name,
    } : null,
    focused_sweep_candidate: workspaceState.focusedSweepCandidate,
    focused_sweep_layer: workspaceState.focusedSweepLayer,
    snapshot_metadata: {
      title: baselineEntry
        ? `catalog workspace snapshot ${baselineEntry.run_id}${focusedWorkspaceCandidate ? ` vs ${focusedWorkspaceCandidate.run_id}` : ""} (${workspaceState.focusedWorkspaceAnalysisFlow || workspaceState.focusedWorkspaceDetailPreset || `${workspaceState.focusedWorkspaceDetailFocus}${workspaceState.focusedWorkspaceSecondaryDetailFocus ? ` + ${workspaceState.focusedWorkspaceSecondaryDetailFocus}` : ""}`})`
        : "catalog workspace snapshot",
      header_rows: snapshotHeaderRows,
    },
    visible_entry_ids: workspaceState.visibleEntries.map((entry) => entry.entry_id),
    candidate_rows: workspaceState.candidates.map((entry, index) => {
      const rowState = baselineEntry ? resolveWorkspaceCompareRowState(baselineEntry, entry) : null;
      return {
        entry_id: entry.entry_id,
        run_id: entry.run_id,
        scenario_name: entry.scenario_name,
        mode: entry.mode,
        schedule_kind: entry.schedule_kind,
        target_profile_name: entry.target_profile_name,
        primary_metric_name: entry.primary_metric_name,
        primary_metric_value: entry.primary_metric_value,
        is_focused_workspace_candidate: Boolean(
          focusedWorkspaceCandidate && focusedWorkspaceCandidate.entry_id === entry.entry_id,
        ),
        metric_values: entry.metric_values || {},
        sweep_comparisons: entry.sweep_comparisons || [],
        compare_summary: rowState && rowState.sweepComparison ? rowState.sweepComparison.compare_summary || null : null,
        profile_diff_fields: rowState && rowState.sweepComparison && rowState.sweepComparison.compare_summary
          ? rowState.sweepComparison.compare_summary.profile_diff_fields || []
          : [],
        analysis_flow_recommendation: rowState && rowState.analysisFlowRecommendation
          ? {
            recommendation_tier: recommendationTierForRank(index, rowState.analysisFlowRecommendation),
            recommendation_rank: index + 1,
            queue_position: index + 1,
            recommendation_reason: rowState.analysisFlowRecommendation.reason,
            recommendation_score: rowState.analysisFlowRecommendation.score,
            previous_candidate_entry_id: index > 0 ? workspaceState.candidates[index - 1].entry_id : null,
            next_candidate_entry_id: index < workspaceState.candidates.length - 1
              ? workspaceState.candidates[index + 1].entry_id
              : null,
          }
          : null,
      };
    }),
  };
}

function buildWorkspaceSnapshotSvg() {
  const payload = buildWorkspaceExportData();
  const headerRows = payload.snapshot_metadata && Array.isArray(payload.snapshot_metadata.header_rows)
    ? payload.snapshot_metadata.header_rows
    : [];
  const recommendationLines = buildRecommendationDetailSnapshotLines(
    payload.focused_workspace_recommendation_details || []
  );
  const candidateLines = payload.candidate_rows.length
    ? payload.candidate_rows.slice(0, 6).map((row) => `${row.run_id} | ${row.primary_metric_name} | ${formatMetricValue(row.primary_metric_value)}`)
    : ["No workspace candidates available."];
  const bodyLines = headerRows
    .map((row) => `${row.label}: ${row.value}`)
    .concat(recommendationLines)
    .concat(candidateLines);
  const lineHeight = 20;
  const height = 160 + (bodyLines.length * lineHeight);
  const lineSvg = bodyLines.map((line, index) => {
    const y = 120 + (index * lineHeight);
    return `<text x="32" y="${y}" font-size="14" fill="#102033">${escapeSvgText(line)}</text>`;
  }).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="${height}" viewBox="0 0 960 ${height}">
  <rect width="960" height="${height}" fill="#f4efe3" />
  <rect x="24" y="24" width="912" height="${height - 48}" rx="18" fill="#ffffff" stroke="#d6c7ab" />
  <text x="32" y="64" font-size="24" fill="#102033">Catalog Workspace Snapshot</text>
  <text x="32" y="92" font-size="14" fill="#5b6980">${escapeSvgText(payload.baseline_run_id || "No baseline selected")}</text>
  ${lineSvg}
</svg>`;
}

function downloadCurrentWorkspaceJson() {
  const payload = buildWorkspaceExportData();
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = "catalog-workspace.view.json";
  anchor.click();
  URL.revokeObjectURL(downloadUrl);
  setCatalogWorkspaceActionStatus("Exported workspace JSON.");
}

function downloadCurrentWorkspaceSvg() {
  const svg = buildWorkspaceSnapshotSvg();
  const blob = new Blob([svg], { type: "image/svg+xml" });
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = "catalog-workspace.snapshot.svg";
  anchor.click();
  URL.revokeObjectURL(downloadUrl);
  setCatalogWorkspaceActionStatus("Exported workspace SVG.");
}

function bindCatalogWorkspaceActions() {
  const copyButton = document.querySelector("#copy-workspace-link-button");
  const jsonButton = document.querySelector("#download-workspace-json-button");
  const svgButton = document.querySelector("#download-workspace-svg-button");
  if (!copyButton || !jsonButton || !svgButton) {
    return;
  }
  copyButton.addEventListener("click", () => {
    copyCurrentWorkspaceLink().catch((error) => {
      setCatalogWorkspaceActionStatus(`Unable to copy workspace link: ${error}`);
    });
  });
  jsonButton.addEventListener("click", () => {
    downloadCurrentWorkspaceJson();
  });
  svgButton.addEventListener("click", () => {
    downloadCurrentWorkspaceSvg();
  });
}

function buildWorkspaceCandidateSet(baselineEntry, entries, scope) {
  const visibleCandidates = entries.filter((entry) => entry.entry_id !== baselineEntry.entry_id);
  if (scope === "all-visible") {
    return visibleCandidates;
  }
  return visibleCandidates.filter((entry) => entry.scenario_name === baselineEntry.scenario_name);
}

function resolveFocusedWorkspaceCandidate(candidates, focusedCandidateId) {
  if (!(candidates || []).length) {
    return null;
  }
  const explicitCandidateId = String(focusedCandidateId || "").trim();
  return candidates.find((entry) => entry.entry_id === explicitCandidateId) || candidates[0] || null;
}

function buildWorkspaceFocusLink(entry, focusedCandidateEntry) {
  const isFocused = Boolean(
    focusedCandidateEntry && entry.entry_id === focusedCandidateEntry.entry_id,
  );
  return `
    <div class="compare-link-row">
      <a class="panel-link workspace-focus-link${isFocused ? " is-active" : ""}" data-entry-id="${entry.entry_id}" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: entry.entry_id })}">Focus In Workspace${isFocused ? " (Focused)" : ""}</a>
    </div>
  `;
}

function renderWorkspaceRecommendationQueue(queue) {
  if (!queue) {
    return '<p class="muted">Recommendation Queue is available when an analysis flow is active.</p>';
  }
  if (!queue.recommended_candidate_count) {
    return '<p class="muted">Recommendation Queue has no ranked candidates for the current workspace.</p>';
  }
  const previousLink = queue.previous_candidate_entry_id
    ? `<a class="panel-link" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: queue.previous_candidate_entry_id })}">Previous Recommended Candidate</a>`
    : "";
  const nextLink = queue.next_candidate_entry_id
    ? `<a class="panel-link" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: queue.next_candidate_entry_id })}">Next Recommended Candidate</a>`
    : "";
  const topEntryId = queue.top_recommendation_entry_ids[0] || "";
  const topLink = topEntryId
    ? `<a class="panel-link" href="${buildCurrentCatalogWorkspaceUrl({ workspace_candidate: topEntryId })}">Open Top Recommendation</a>`
    : "";
  return `
    <ul class="metric-detail-list">
      <li><span>Queue Position</span><div class="metric-detail-values"><strong>${queue.queue_position || "n/a"}</strong><em>of ${queue.recommended_candidate_count}</em></div></li>
      <li><span>Top Recommended Candidates</span><div class="metric-detail-values"><strong>${queue.top_recommendation_entry_ids.join(", ") || "none"}</strong><em>${queue.total_candidates} visible candidates</em></div></li>
    </ul>
    <div class="compare-link-row">
      ${topLink}
      ${previousLink}
      ${nextLink}
    </div>
    <ul class="metric-detail-list">
      ${queue.top_recommendations.map((item) => `
        <li>
          <span>${item.queue_position}. ${item.run_id}${item.is_focused ? " (Focused)" : ""}</span>
          <div class="metric-detail-values">
            <strong>${item.recommendation_tier}</strong>
            <em>${item.recommendation_reason}</em>
          </div>
        </li>
      `).join("")}
    </ul>
  `;
}

function renderWorkspaceRecommendationDetailBlocks(detailEntries) {
  if (!(detailEntries || []).length) {
    return '<p class="muted">Recommendation Detail Blocks are available when ranked recommendations include compare detail.</p>';
  }
  return `
    <ul class="metric-detail-list">
      ${detailEntries.map((detail) => renderRecommendationDetailEntryMarkup(detail, {
        meta: detail.recommendation_reason || detail.target_profile_name,
        lead_label: "Estimated Layer",
        trail_label: "Fitted Layer",
      })).join("")}
    </ul>
  `;
}

function renderFocusedWorkspaceDrilldown(baselineEntry, focusedCandidateEntry, candidates, recommendationRank = -1) {
  if (!baselineEntry || !focusedCandidateEntry) {
    return `
      <article class="compare-card">
        <h3>Focused Workspace Compare Drilldown</h3>
        <p class="empty">No workspace candidate is currently focused.</p>
      </article>
    `;
  }
  const rowState = resolveWorkspaceCompareRowState(baselineEntry, focusedCandidateEntry);
  const sweepComparison = rowState.sweepComparison;
  const recommendationQueue = resolveWorkspaceRecommendationQueue(
    baselineEntry,
    candidates,
    focusedCandidateEntry,
  );
  const recommendationDetails = buildWorkspaceRecommendationDetailEntries(
    baselineEntry,
    candidates,
    focusedCandidateEntry,
  );
  const drilldownContent = buildWorkspaceCompareDrilldownContent(
    baselineEntry,
    focusedCandidateEntry,
    sweepComparison,
  ) || '<p class="empty">No matched compare drilldown sections.</p>';
  return `
    <article class="compare-card">
      <h3>Focused Workspace Compare Drilldown</h3>
      <p><strong>${baselineEntry.run_id}</strong> -> <strong>${focusedCandidateEntry.run_id}</strong></p>
      <p class="muted">Focused candidate: ${focusedCandidateEntry.target_profile_name} | Compare Focus: ${currentCompareFocusLabel()} | Workspace Detail: ${currentWorkspaceDetailFocusLabel()}${currentWorkspaceSecondaryDetailFocusLabel() ? ` | Compare-Against Detail: ${currentWorkspaceSecondaryDetailFocusLabel()}` : ""}${currentWorkspaceDetailPreset() ? ` | Compare Preset: ${currentWorkspaceDetailPreset()}` : ""}${currentWorkspaceAnalysisFlow() ? ` | Analysis Flow: ${currentWorkspaceAnalysisFlow()}` : ""} | Layer Mode: ${currentLayerDeltaFocus()}</p>
      ${renderWorkspaceAnalysisFlowLinks()}
      ${renderWorkspaceDetailPresetLinks()}
      <section class="compare-summary-group">
        <div class="compare-group-heading">
          <p class="muted">Analysis Flow Summary</p>
        </div>
        ${buildWorkspaceAnalysisFlowSummary()}
      </section>
      <section class="compare-summary-group">
        <div class="compare-group-heading">
          <p class="muted">Analysis Flow Candidate Recommendation</p>
        </div>
        ${buildWorkspaceAnalysisFlowRecommendationSummary(rowState, recommendationRank)}
      </section>
      <section class="compare-summary-group">
        <div class="compare-group-heading">
          <p class="muted">Recommendation Queue</p>
        </div>
        ${renderWorkspaceRecommendationQueue(recommendationQueue)}
      </section>
      <section class="compare-summary-group">
        <div class="compare-group-heading">
          <p class="muted">Recommendation Detail Blocks</p>
        </div>
        <p class="muted">Top Recommendation Detail Candidates</p>
        ${renderWorkspaceRecommendationDetailBlocks(recommendationDetails)}
      </section>
      ${buildComparePanelLinks(focusedCandidateEntry)}
      ${drilldownContent}
    </article>
  `;
}

function buildWorkspaceCompareRows(baselineEntry, candidates, scope, focusedCandidateEntry) {
  if (!candidates.length) {
    return scope === "all-visible"
      ? '<p class="empty">No additional visible runs are available for the current baseline.</p>'
      : '<p class="empty">No additional visible runs share the current baseline scenario.</p>';
  }

  return `
    <table class="catalog-table">
      <thead>
        <tr>
          <th>Run</th>
          <th>Schedule</th>
          <th>Target</th>
          <th>Metric</th>
          <th>Primary Delta</th>
          <th>Primary Ratio</th>
          <th>Shared Metric Deltas</th>
          <th>Sweep Layer Deltas</th>
          <th>Link</th>
        </tr>
      </thead>
      <tbody>
        ${candidates.map((entry) => {
          const rowState = resolveWorkspaceCompareRowState(baselineEntry, entry);
          const sweepComparison = rowState.sweepComparison;
          const recommendationRank = candidates.findIndex((candidate) => candidate.entry_id === entry.entry_id);
          const isFocusedWorkspaceCandidate = Boolean(
            focusedCandidateEntry && entry.entry_id === focusedCandidateEntry.entry_id,
          );
            return `
              <tr${isFocusedWorkspaceCandidate ? ' class="workspace-focused-row"' : ""}>
                <td>${entry.run_id}</td>
                <td>${entry.schedule_kind}</td>
                <td>${entry.target_profile_name}</td>
                <td>${entry.primary_metric_name}</td>
                ${renderWorkspaceSummaryCell(
                  rowState.workspaceSummaryTag,
                  buildWorkspacePrimaryDeltaContent(entry, rowState.sameMetric, rowState.delta)
                )}
                ${renderWorkspaceSummaryCell(
                  rowState.workspaceRatioSummaryTag,
                  buildWorkspacePrimaryRatioContent(entry, rowState.sameMetric, rowState.ratio)
                )}
                ${renderWorkspaceSummaryCell(
                  rowState.workspaceSummaryTag,
                  buildWorkspaceSharedMetricContent(baselineEntry, entry, sweepComparison)
                )}
                ${renderWorkspaceSummaryCell(
                  rowState.workspaceSweepSummaryTag,
                  buildWorkspaceSweepSummaryContent(baselineEntry, entry, sweepComparison)
                )}
                <td>${renderWorkspaceRecommendationBadge(rowState, recommendationRank)}${buildComparePanelLinks(entry)}${buildWorkspaceFocusLink(entry, focusedCandidateEntry)}</td>
              </tr>
            `;
          }).join("")}
      </tbody>
    </table>
  `;
}

function renderCompareWorkspace(entries) {
  const container = document.querySelector("#catalog-compare-workspace-content");
  if (!container) {
    return;
  }
  const workspaceState = resolveCurrentWorkspaceState();
  const baselineEntry = workspaceState.baselineEntry;
  if (!baselineEntry) {
    container.innerHTML = '<p class="empty">Select a baseline run to open the scenario compare workspace.</p>';
    return;
  }
  const scope = workspaceState.compareScope;
  container.innerHTML = `
    <article class="compare-card">
      <h3>Baseline: ${baselineEntry.run_id}</h3>
      <p>${baselineEntry.scenario_name} · ${baselineEntry.primary_metric_name}: <strong>${baselineEntry.primary_metric_value}</strong></p>
      <p class="muted">${scope === "all-visible" ? "Comparing against all visible runs." : "Comparing against visible runs in the same scenario."}</p>
      ${buildComparePanelLinks(baselineEntry)}
      ${buildWorkspaceCompareRows(baselineEntry, workspaceState.candidates, scope, workspaceState.focusedWorkspaceCandidate)}
      ${renderFocusedWorkspaceDrilldown(
        baselineEntry,
        workspaceState.focusedWorkspaceCandidate,
        workspaceState.candidates,
        workspaceState.focusedWorkspaceCandidate
          ? workspaceState.candidates.findIndex((entry) => entry.entry_id === workspaceState.focusedWorkspaceCandidate.entry_id)
          : -1,
      )}
    </article>
  `;
}

function bindCompareToggles(entries) {
  document.querySelectorAll(".compare-toggle").forEach((button) => {
    button.classList.toggle("is-active", COMPARE_SELECTION.includes(button.dataset.entryId));
    button.addEventListener("click", () => {
      toggleCompareSelection(button.dataset.entryId);
      bindCompareToggles(entries);
      renderCompareTray(entries);
      renderCompareWorkspace(entries);
    });
  });
}

function renderCatalogGroups(entries) {
  const nav = document.querySelector("#catalog-group-nav");
  const sections = document.querySelector("#catalog-group-sections");
  if (!nav || !sections) {
    return;
  }
  const groups = groupCatalogEntries(entries);
  nav.innerHTML = groups.map(([groupName]) => `
    <a class="group-chip" href="#group-${slugifyGroupName(groupName)}">${groupName}</a>
  `).join("");
  sections.innerHTML = groups.map(([groupName, groupEntries]) => `
    <article class="group-card" id="group-${slugifyGroupName(groupName)}">
      <div class="group-header">
        <h2>${groupName}</h2>
        <span class="group-count">${groupEntries.length} runs</span>
      </div>
      <ul class="group-entry-list">
        ${groupEntries.map((entry) => `
          <li>
            <div class="group-run-meta">
              <a href="${buildWorkbenchLink(entry, "summary")}">${entry.run_id}</a>
              <span>${entry.mode}</span>
              <span>${entry.schedule_kind}</span>
              <span>${entry.primary_metric_name}: ${entry.primary_metric_value}</span>
            </div>
            <div class="group-link-row">
              <button class="compare-toggle" data-entry-id="${entry.entry_id}" type="button">Compare</button>
              <a class="panel-link" href="${buildWorkbenchLink(entry, "summary")}">Summary</a>
              <a class="panel-link" href="${buildWorkbenchLink(entry, "timeline")}">Timeline</a>
              <a class="panel-link" href="${buildWorkbenchLink(entry, "memory")}">Memory</a>
              <a class="panel-link" href="${buildWorkbenchLink(entry, "coverage")}">Coverage</a>
            </div>
          </li>
        `).join("")}
      </ul>
    </article>
  `).join("");
  if (!groups.length) {
    nav.innerHTML = '<p class="empty">No groups available.</p>';
    sections.innerHTML = '<p class="empty">No grouped runs match the current filters.</p>';
  }
}

function bindCatalogFilters() {
  const searchInput = document.querySelector("#catalog-search-input");
  const modeFilter = document.querySelector("#catalog-mode-filter");
  const scheduleFilter = document.querySelector("#catalog-schedule-filter");
  const compareScopeFilter = document.querySelector("#catalog-compare-scope-filter");
  const compareFocusFilter = document.querySelector("#catalog-compare-focus-filter");
  const workbenchPanelFilter = document.querySelector("#catalog-workbench-panel-filter");
  const layerDeltaFocusFilter = document.querySelector("#catalog-layer-delta-focus-filter");
  const swapCompareOrderButton = document.querySelector("#swap-compare-order-button");
  if (!searchInput || !modeFilter || !scheduleFilter || !compareScopeFilter || !compareFocusFilter || !workbenchPanelFilter || !layerDeltaFocusFilter || !swapCompareOrderButton) {
    return;
  }
  hydrateCatalogStateFromUrl();
  const refresh = () => {
    const filtered = filterCatalogEntries(
      CATALOG_ENTRIES,
      searchInput.value,
      modeFilter.value,
      scheduleFilter.value,
    );
    resolveCurrentWorkspaceState();
    renderCatalogRows(filtered);
    renderCatalogGroups(filtered);
    bindCompareToggles(CATALOG_ENTRIES);
    renderCompareTray(CATALOG_ENTRIES);
    renderCompareWorkspace(filtered);
    refreshBlockedCaseWorkbenchLinks();
  };
  searchInput.addEventListener("input", refresh);
  modeFilter.addEventListener("change", refresh);
  scheduleFilter.addEventListener("change", refresh);
  compareScopeFilter.addEventListener("change", refresh);
  compareFocusFilter.addEventListener("change", refresh);
  workbenchPanelFilter.addEventListener("change", refresh);
  layerDeltaFocusFilter.addEventListener("change", refresh);
  swapCompareOrderButton.addEventListener("click", () => {
    swapCompareSelectionOrder();
    refresh();
  });
  bindCatalogWorkspaceActions();
  refresh();
}

bindCatalogFilters();
""").replace("__CATALOG_ENTRIES__", json.dumps([entry.model_dump(mode="json") for entry in entries]))


def _build_styles_css() -> str:
    return """html, body {
  margin: 0;
  min-height: 100%;
  background: linear-gradient(180deg, #07111d 0%, #0d1829 36%, #f3efe4 36%, #f3efe4 100%);
  color: #102033;
  font-family: "Trebuchet MS", "Segoe UI", sans-serif;
}

.shell {
  max-width: 1280px;
  margin: 0 auto;
  padding: 28px 20px 56px;
}

.hero {
  color: #f5f1e6;
  padding: 24px 28px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(10, 21, 39, 0.92), rgba(23, 46, 74, 0.92));
}

.eyebrow {
  margin: 0 0 8px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 12px;
  color: #ffd60a;
}

.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin: 20px 0;
}

.control {
  display: grid;
  gap: 6px;
  min-width: 180px;
}

.control span {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5b6980;
}

.control input,
.control select {
  border: 1px solid rgba(16, 32, 51, 0.16);
  border-radius: 14px;
  padding: 10px 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.stat-card,
.phase-c-gate-card,
.table-card,
.compare-tray,
.group-card {
  background: rgba(255, 251, 244, 0.94);
  border-radius: 22px;
  padding: 18px;
  box-shadow: 0 16px 40px rgba(16, 32, 51, 0.08);
}

.stat-card strong {
  display: block;
  font-size: 28px;
  margin-top: 6px;
}

.phase-c-gate-card {
  display: grid;
  gap: 12px;
  margin: 18px 0;
}

.phase-c-gate-card h2 {
  margin: 0;
}

.phase-c-gate-card .metric-list {
  margin: 0;
}

.group-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 18px 0;
}

.compare-tray {
  margin: 18px 0;
}

.compare-workspace {
  margin: 18px 0;
}

.compare-tray-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
  margin-bottom: 12px;
}

.compare-workspace-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: end;
}

.control-compact {
  min-width: 160px;
}

.compare-card {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(16, 32, 51, 0.08);
  border-radius: 18px;
  padding: 14px;
}

.workspace-focused-row {
  background: rgba(214, 199, 171, 0.18);
}

.workspace-focus-link.is-active {
  font-weight: 700;
}

.workspace-detail-focus-link.is-active {
  font-weight: 700;
}

.workspace-detail-preset-link.is-active {
  font-weight: 700;
}

.workspace-analysis-flow-link.is-active {
  font-weight: 700;
}

.compare-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.metric-detail-list {
  list-style: none;
  padding: 0;
  margin: 10px 0 0;
}

.metric-detail-list li {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(16, 32, 51, 0.08);
}

.metric-detail-list li:last-child {
  border-bottom: 0;
}

.metric-detail-values {
  display: grid;
  justify-items: end;
  gap: 2px;
}

.summary-stack {
  display: grid;
  gap: 6px;
  align-content: start;
}

.summary-stack-value {
  display: grid;
  gap: 6px;
}

.compare-summary-group + .compare-summary-group {
  margin-top: 12px;
}

.compare-group-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.compare-summary-group.is-focused-section {
  border-left: 3px solid rgba(160, 120, 56, 0.45);
  padding-left: 10px;
}

.compare-group-heading .muted {
  margin: 0;
}

.direction-tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: rgba(16, 32, 51, 0.08);
  color: #5b6980;
}

.direction-tag.is-positive {
  background: rgba(28, 181, 224, 0.14);
  color: #0b4f6c;
}

.direction-tag.is-negative {
  background: rgba(181, 35, 35, 0.1);
  color: #8d2424;
}

.direction-tag.is-neutral {
  background: rgba(16, 32, 51, 0.08);
  color: #5b6980;
}

.compare-summary-group .compare-summary-details {
  margin-top: 8px;
}

.metric-detail-values em {
  color: #5b6980;
  font-style: normal;
}

.compare-link-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.group-chip {
  text-decoration: none;
  color: #102033;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(16, 32, 51, 0.12);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
}

.table-card {
  overflow-x: auto;
}

.catalog-table {
  width: 100%;
  border-collapse: collapse;
}

.catalog-table th,
.catalog-table td {
  text-align: left;
  padding: 12px 10px;
  border-bottom: 1px solid rgba(16, 32, 51, 0.08);
}

.catalog-table th {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #5b6980;
}

.catalog-table a,
.group-entry-list a {
  color: #0d4f8b;
  text-decoration: none;
  font-weight: 700;
}

.group-sections {
  display: grid;
  gap: 16px;
  margin-top: 18px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.group-entry-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.group-entry-list li {
  display: grid;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(16, 32, 51, 0.08);
}

.group-run-meta {
  display: grid;
  grid-template-columns: 1.5fr repeat(3, 1fr);
  gap: 12px;
}

.group-link-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.compare-toggle,
.panel-link {
  text-decoration: none;
  color: #102033;
  background: rgba(16, 32, 51, 0.06);
  border: 1px solid rgba(16, 32, 51, 0.08);
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
}

.compare-toggle {
  cursor: pointer;
}

.compare-toggle.is-active {
  background: #102033;
  color: #f5f1e6;
  border-color: #102033;
}

.group-count,
.muted,
.empty,
.empty-cell {
  color: #5b6980;
}
"""


def _build_stat_cards(entries: list[VisualizationCatalogEntry]) -> str:
    total_runs = len(entries)
    prefill_count = sum(1 for entry in entries if entry.mode == "prefill")
    decode_count = sum(1 for entry in entries if entry.mode == "decode")
    scenario_count = len(set(entry.scenario_name for entry in entries))
    cards = [
        ("Runs", str(total_runs)),
        ("Scenarios", str(scenario_count)),
        ("Prefill", str(prefill_count)),
        ("Decode", str(decode_count)),
    ]
    return "\n".join(
        f"""        <article class="stat-card">
          <span>{label}</span>
          <strong>{value}</strong>
        </article>"""
        for label, value in cards
    )


def _build_phase_c_gate_banner(
    summary: VisualizationCatalogPhaseCGateSummary | None,
    blocked_cases: list[VisualizationCatalogPhaseCBlockedCase],
) -> str:
    if summary is None:
        return ""
    blocked_cases_html = _build_phase_c_blocked_cases_table(blocked_cases)
    return f"""      <section class="phase-c-gate-card">
        <article class="phase-c-gate-card">
          <div>
            <p class="eyebrow">Phase C Gate</p>
            <h2>Phase C Gate</h2>
            <p class="muted">Workspace-level canonical matrix readiness from phase_c_acceptance_report.json</p>
            <p class="muted">status: {summary.status}</p>
          </div>
          <ul class="metric-list">
            <li><span>ready</span><strong>{summary.ready_case_count}</strong></li>
            <li><span>blocked</span><strong>{summary.blocked_case_count}</strong></li>
            <li><span>planner_blocked</span><strong>{summary.planner_blocked_case_count}</strong></li>
            <li><span>downstream_blocked</span><strong>{summary.downstream_blocked_case_count}</strong></li>
            <li><span>missing</span><strong>{summary.missing_case_count}</strong></li>
            <li><span>duplicate</span><strong>{summary.duplicate_case_count}</strong></li>
          </ul>
          {blocked_cases_html}
        </article>
      </section>"""


def _build_phase_c_blocked_cases_table(
    blocked_cases: list[VisualizationCatalogPhaseCBlockedCase],
) -> str:
    if not blocked_cases:
        return ""
    rows = "\n".join(
        f"""              <tr>
                <td>{case.case_id}</td>
                <td>{case.run_id or "-"}</td>
                <td>{case.blocker_kind}</td>
                <td>{case.planner_closure_status or "-"}</td>
                <td>{case.downstream_closure_status or "-"}</td>
                <td>{", ".join(case.remaining_gaps) if case.remaining_gaps else "-"}</td>
                <td>{_build_blocked_case_workbench_link(case)}</td>
              </tr>"""
        for case in blocked_cases
    )
    return f"""
          <div>
            <h3>Blocked Cases</h3>
            <table class="catalog-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Run</th>
                  <th>Blocker</th>
                  <th>Planner</th>
                  <th>Downstream</th>
                  <th>Gaps</th>
                  <th>Workbench</th>
                </tr>
              </thead>
              <tbody>
{rows}
              </tbody>
            </table>
          </div>"""


def _build_blocked_case_workbench_link(case: VisualizationCatalogPhaseCBlockedCase) -> str:
    if not case.workbench_entry_path:
        return "-"
    panel = _blocked_case_panel(case)
    if panel is None:
        return "-"
    memory_query = _blocked_case_memory_query(case)
    coverage_focus = _blocked_case_coverage_focus(case)
    href = _blocked_case_workbench_href(
        case.workbench_entry_path,
        panel,
        memory_query=memory_query,
        coverage_focus=coverage_focus,
    )
    memory_query_attr = (
        f' data-workbench-memory-query="{memory_query}"' if memory_query else ""
    )
    coverage_focus_attr = (
        f' data-workbench-coverage-focus="{coverage_focus}"' if coverage_focus else ""
    )
    return (
        f'<a class="blocked-case-workbench-link" '
        f'href="{href}" '
        f'data-workbench-path="{case.workbench_entry_path}" '
        f'data-workbench-panel="{panel}"'
        f'{memory_query_attr}'
        f'{coverage_focus_attr}>'
        f'Open {_blocked_case_panel_label(panel)}'
        "</a>"
    )


def _blocked_case_panel(case: VisualizationCatalogPhaseCBlockedCase) -> str | None:
    if case.blocker_kind in {"planner", "planner_and_downstream"}:
        return "memory"
    if case.blocker_kind == "downstream":
        return _downstream_blocked_case_panel(case)
    return None


def _blocked_case_memory_query(case: VisualizationCatalogPhaseCBlockedCase) -> str | None:
    if case.blocker_kind not in {"planner", "planner_and_downstream"}:
        return None
    for gap in case.remaining_gaps:
        match = re.search(r"overflow region:\s*([A-Za-z0-9_.-]+)", gap)
        if match is not None:
            return match.group(1)
    return None


def _blocked_case_coverage_focus(case: VisualizationCatalogPhaseCBlockedCase) -> str | None:
    if case.blocker_kind != "downstream":
        return None
    if "descriptor_generation" in case.downstream_missing_consumers:
        return "packed-descriptor"
    return None


def _blocked_case_workbench_href(
    workbench_entry_path: str,
    panel: str,
    *,
    memory_query: str | None = None,
    coverage_focus: str | None = None,
) -> str:
    params = {"panel": panel}
    if memory_query:
        params["memory_query"] = memory_query
    if coverage_focus:
        params["coverage_focus"] = coverage_focus
    return f"{workbench_entry_path}?{urlencode(params)}"


def _blocked_case_panel_label(panel: str) -> str:
    labels = {
        "summary": "Summary",
        "memory": "Memory",
        "coverage": "Coverage",
    }
    return labels[panel]


def _downstream_blocked_case_panel(case: VisualizationCatalogPhaseCBlockedCase) -> str:
    missing_consumers = set(case.downstream_missing_consumers)
    if not missing_consumers:
        return "coverage"
    if missing_consumers & {"visualization_packaging", "visualization_workbench"}:
        return "memory"
    if missing_consumers & {"descriptor_generation"}:
        return "coverage"
    if missing_consumers & {
        "tile_planning",
        "performance_estimation",
        "prefill_evaluation",
        "decode_evaluation",
    }:
        return "summary"
    return "coverage"


def _build_table_rows(entries: list[VisualizationCatalogEntry]) -> str:
    return "\n".join(
        f"""              <tr data-mode="{entry.mode}" data-schedule="{entry.schedule_kind}">
                <td><button class="compare-toggle" data-entry-id="{entry.entry_id}" type="button">Compare</button></td>
                <td><a href="{entry.workbench_entry_path}">{entry.run_id}</a></td>
                <td>{entry.scenario_name}</td>
                <td>{entry.mode}</td>
                <td>{entry.schedule_kind}</td>
                <td>{entry.target_profile_name}</td>
                <td>{entry.primary_metric_name}</td>
                <td>{entry.primary_metric_value}</td>
              </tr>"""
        for entry in entries
    )


def _build_group_section(group_name: str, entries: list[VisualizationCatalogEntry]) -> str:
    group_entries = [entry for entry in entries if entry.scenario_name == group_name]
    items = "\n".join(
        f"""          <li>
            <div class="group-run-meta">
              <a href="{entry.workbench_entry_path}">{entry.run_id}</a>
              <span>{entry.mode}</span>
              <span>{entry.schedule_kind}</span>
              <span>{entry.primary_metric_name}: {entry.primary_metric_value}</span>
            </div>
            <div class="group-link-row">
              <button class="compare-toggle" data-entry-id="{entry.entry_id}" type="button">Compare</button>
              <a class="panel-link" href="{_panel_link(entry, 'summary')}">Summary</a>
              <a class="panel-link" href="{_panel_link(entry, 'timeline')}">Timeline</a>
              <a class="panel-link" href="{_panel_link(entry, 'memory')}">Memory</a>
              <a class="panel-link" href="{_panel_link(entry, 'coverage')}">Coverage</a>
            </div>
          </li>"""
        for entry in group_entries
    )
    return f"""        <article class="group-card" id="group-{_slugify(group_name)}">
          <div class="group-header">
            <h2>{group_name}</h2>
            <span class="group-count">{len(group_entries)} runs</span>
          </div>
          <ul class="group-entry-list">
{items}
          </ul>
        </article>"""


def _group_names(entries: list[VisualizationCatalogEntry]) -> list[str]:
    return sorted({entry.scenario_name for entry in entries})


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "ungrouped"


def _panel_link(entry: VisualizationCatalogEntry, panel: str) -> str:
    return f"{entry.workbench_entry_path}?panel={panel}"


def _normalize(path: Path) -> str:
    return str(path).replace("\\", "/")
