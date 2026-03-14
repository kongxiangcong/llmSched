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
            <button class="compare-toggle" id="swap-compare-order-button" type="button">Swap Baseline/Candidate</button>
          </div>
        </div>
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
    return """const CATALOG_ENTRIES = __CATALOG_ENTRIES__;

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

function serializeCatalogState() {
  const searchInput = document.querySelector("#catalog-search-input");
  const modeFilter = document.querySelector("#catalog-mode-filter");
  const scheduleFilter = document.querySelector("#catalog-schedule-filter");
  const compareScopeFilter = document.querySelector("#catalog-compare-scope-filter");
  const workbenchPanelFilter = document.querySelector("#catalog-workbench-panel-filter");
  const layerDeltaFocusFilter = document.querySelector("#catalog-layer-delta-focus-filter");
  return {
    search: searchInput ? searchInput.value : "",
    mode: modeFilter ? modeFilter.value : "all",
    schedule: scheduleFilter ? scheduleFilter.value : "all",
    compare_scope: compareScopeFilter ? compareScopeFilter.value : "same-scenario",
    workbench_panel: workbenchPanelFilter ? workbenchPanelFilter.value : "summary",
    layer_delta_focus: layerDeltaFocusFilter ? layerDeltaFocusFilter.value : "top-cycle",
    compare_ids: COMPARE_SELECTION.join(","),
  };
}

function buildCatalogReturnUrl() {
  const state = serializeCatalogState();
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
  if (workbenchPanelFilter) {
    workbenchPanelFilter.value = params.get("workbench_panel") || "summary";
  }
  if (layerDeltaFocusFilter) {
    layerDeltaFocusFilter.value = params.get("layer_delta_focus") || "top-cycle";
  }
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

function currentLayerDeltaFocus() {
  const layerDeltaFocusFilter = document.querySelector("#catalog-layer-delta-focus-filter");
  return layerDeltaFocusFilter ? layerDeltaFocusFilter.value : "top-cycle";
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

function buildComparePanelLinks(entry) {
  const panel = currentWorkbenchPanel();
  const links = [
    `<a class="panel-link" href="${buildWorkbenchLink(entry, panel)}">Open Selected Panel (${workbenchPanelLabel(panel)})</a>`,
  ];
  if (panel !== "summary") {
    links.push(`<a class="panel-link" href="${buildWorkbenchLink(entry, "summary")}">Open Summary</a>`);
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

function buildScalarDeltaDirectionTag(scalarDelta) {
  const deltaValue = Number(scalarDelta.delta_value || 0);
  if (!Number.isFinite(deltaValue) || deltaValue === 0) {
    return '<span class="direction-tag is-neutral">steady</span>';
  }
  const positive = metricImprovesWhenHigher(scalarDelta.metric_name)
    ? deltaValue > 0
    : deltaValue < 0;
  return positive
    ? '<span class="direction-tag is-positive">improved</span>'
    : '<span class="direction-tag is-negative">regressed</span>';
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
    return '<span class="direction-tag is-neutral">steady</span>';
  }
  const metricName = String(leadScalar.metric_name || "");
  const groupId = String(group.group_id || "");
  if (groupId === "headline" || groupId === "throughput_latency") {
    const improvesWhenHigher = (
      metricName.includes("tokens_per_cycle")
      || metricName.includes("bytes_per_cycle")
    );
    const faster = improvesWhenHigher ? deltaValue > 0 : deltaValue < 0;
    return faster
      ? '<span class="direction-tag is-positive">candidate faster</span>'
      : '<span class="direction-tag is-negative">candidate slower</span>';
  }
  if (groupId === "memory_pressure") {
    return deltaValue > 0
      ? '<span class="direction-tag is-negative">pressure up</span>'
      : '<span class="direction-tag is-positive">pressure down</span>';
  }
  if (groupId === "schedule_shape") {
    return deltaValue > 0
      ? '<span class="direction-tag is-neutral">schedule shifted up</span>'
      : '<span class="direction-tag is-neutral">schedule shifted down</span>';
  }
  return deltaValue > 0
    ? '<span class="direction-tag is-neutral">shifted up</span>'
    : '<span class="direction-tag is-neutral">shifted down</span>';
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
  return (compareSummary.scalar_delta_groups || [])
    .filter((group) => (group.scalar_deltas || []).length)
    .map((group) => renderGroupedScalarDeltaSection(group))
    .join("");
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
  const visibleRows = highlightedRows.length ? highlightedRows : scalarRows;
  if (!groupedRows && !visibleRows.length) {
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
    ${fullScalarDetails}
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
      : Math.abs(Number(left.delta_cycles || 0));
    const rightScore = focus === "top-by-bytes"
      ? Math.abs(Number(right.delta_bytes || 0))
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
    : (layerDeltas || []);
  return orderedSweepLayerDeltas(filteredLayerDeltas).slice(0, MAX_SWEEP_LAYER_DELTA_ROWS);
}

function buildSweepDrilldownLink(baselineEntry, candidateEntry) {
  const match = resolveSweepComparisonMatch(baselineEntry, candidateEntry);
  if (!match || !match.sourceEntry || !match.sourceEntry.workbench_entry_path) {
    return "";
  }
  return `<div class="compare-link-row"><a class="panel-link" href="${buildWorkbenchHref(match.sourceEntry.workbench_entry_path, "sweep")}">Open Sweep Panel (${match.sourceEntry.run_id})</a></div>`;
}

function buildSweepLayerDrilldownLink(baselineEntry, candidateEntry, layerId) {
  const match = resolveSweepComparisonMatch(baselineEntry, candidateEntry);
  if (!match || !match.sourceEntry || !match.sourceEntry.workbench_entry_path) {
    return "";
  }
  return `<a class="panel-link" href="${buildWorkbenchHref(match.sourceEntry.workbench_entry_path, "sweep", { sweep_candidate: candidateEntry.target_profile_name, sweep_layer_focus: layerId })}">Open Layer In Sweep</a>`;
}

function renderSweepLayerDeltaRows(baselineEntry, candidateEntry, sweepComparison) {
  if (!sweepComparison) {
    return '<p class="empty">No matched sweep compare summary.</p>';
  }
  const orderedLayerDeltas = orderedSweepLayerDeltas(sweepComparison.layer_deltas || []);
  const layerDeltas = selectSweepLayerDeltas(sweepComparison.layer_deltas || []);
  const focus = currentLayerDeltaFocus();
  if (!layerDeltas.length) {
    return focus === "regressions-only"
      ? '<p class="empty">No candidate regression layers in matched sweep summary.</p>'
      : '<p class="empty">No matched sweep layer deltas.</p>';
  }
  const visibleLayerCount = focus === "regressions-only"
    ? (sweepComparison.layer_deltas || []).filter((layerDelta) => Number(layerDelta.delta_cycles || 0) > 0).length
    : orderedLayerDeltas.length;
  const sortDescriptor = focus === "top-by-bytes" ? "|delta_bytes|" : "|delta_cycles|";
  const countDescriptor = focus === "regressions-only" ? "regression layers" : "layers";
  const truncationNote = visibleLayerCount > MAX_SWEEP_LAYER_DELTA_ROWS
    ? `<p class="muted">Showing top 3 of ${visibleLayerCount} ${countDescriptor} by ${sortDescriptor}.</p>`
    : "";
  return `${truncationNote}<ul class="metric-detail-list">${layerDeltas.map((layerDelta) => `
    <li>
      <span>Layer ${layerDelta.layer_id}</span>
      <div class="metric-detail-values">
        <strong>${formatMetricDelta(layerDelta.delta_cycles)} cycles</strong>
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

function buildWorkspaceCandidateSet(baselineEntry, entries, scope) {
  const visibleCandidates = entries.filter((entry) => entry.entry_id !== baselineEntry.entry_id);
  if (scope === "all-visible") {
    return visibleCandidates;
  }
  return visibleCandidates.filter((entry) => entry.scenario_name === baselineEntry.scenario_name);
}

function buildWorkspaceCompareRows(baselineEntry, entries, scope) {
  const candidates = buildWorkspaceCandidateSet(baselineEntry, entries, scope)
    .sort((left, right) => left.primary_metric_value - right.primary_metric_value);

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
          const sameMetric = entry.primary_metric_name === baselineEntry.primary_metric_name;
          const delta = entry.primary_metric_value - baselineEntry.primary_metric_value;
          const ratio = baselineEntry.primary_metric_value !== 0 ? entry.primary_metric_value / baselineEntry.primary_metric_value : null;
          const sweepComparison = resolveSweepComparison(baselineEntry, entry);
          return `
            <tr>
              <td>${entry.run_id}</td>
              <td>${entry.schedule_kind}</td>
              <td>${entry.target_profile_name}</td>
              <td>${entry.primary_metric_name}</td>
              <td>${sameMetric ? formatMetricDelta(delta) : "metric mismatch"}</td>
              <td>${sameMetric && ratio !== null ? `${ratio.toFixed(3)}x` : "n/a"}</td>
              <td>${buildMatchedCompareSummaryRows(baselineEntry, entry, sweepComparison)}</td>
              <td>${renderSweepComparisonSummary(sweepComparison)}${buildSweepDrilldownLink(baselineEntry, entry)}${renderSweepLayerDeltaRows(baselineEntry, entry, sweepComparison)}</td>
              <td>${buildComparePanelLinks(entry)}</td>
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
  const baselineEntryId = COMPARE_SELECTION[0];
  const baselineEntry = entries.find((entry) => entry.entry_id === baselineEntryId) || CATALOG_ENTRIES.find((entry) => entry.entry_id === baselineEntryId);
  if (!baselineEntry) {
    container.innerHTML = '<p class="empty">Select a baseline run to open the scenario compare workspace.</p>';
    return;
  }
  const scope = currentCompareScope();
  container.innerHTML = `
    <article class="compare-card">
      <h3>Baseline: ${baselineEntry.run_id}</h3>
      <p>${baselineEntry.scenario_name} · ${baselineEntry.primary_metric_name}: <strong>${baselineEntry.primary_metric_value}</strong></p>
      <p class="muted">${scope === "all-visible" ? "Comparing against all visible runs." : "Comparing against visible runs in the same scenario."}</p>
      ${buildComparePanelLinks(baselineEntry)}
      ${buildWorkspaceCompareRows(baselineEntry, entries, scope)}
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
  const workbenchPanelFilter = document.querySelector("#catalog-workbench-panel-filter");
  const layerDeltaFocusFilter = document.querySelector("#catalog-layer-delta-focus-filter");
  const swapCompareOrderButton = document.querySelector("#swap-compare-order-button");
  if (!searchInput || !modeFilter || !scheduleFilter || !compareScopeFilter || !workbenchPanelFilter || !layerDeltaFocusFilter || !swapCompareOrderButton) {
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
  workbenchPanelFilter.addEventListener("change", refresh);
  layerDeltaFocusFilter.addEventListener("change", refresh);
  swapCompareOrderButton.addEventListener("click", () => {
    swapCompareSelectionOrder();
    refresh();
  });
  refresh();
}

bindCatalogFilters();
""".replace("__CATALOG_ENTRIES__", json.dumps([entry.model_dump(mode="json") for entry in entries]))


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

.compare-summary-group + .compare-summary-group {
  margin-top: 12px;
}

.compare-group-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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
