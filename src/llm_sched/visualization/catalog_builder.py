"""Builder for SPEC-19 static cross-run visualization catalogs."""

from __future__ import annotations

import json
import re
from pathlib import Path

from llm_sched.contracts.visualization_catalog import (
    VisualizationCatalogArtifact,
    VisualizationCatalogEntry,
    VisualizationCatalogMetadata,
)


def build_visualization_catalog(
    *,
    catalog_id: str,
    title: str,
    entries: list[VisualizationCatalogEntry],
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
          <h2>Compare Selected Runs</h2>
          <p class="muted">Pick up to two runs from the table or grouped cards.</p>
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
    return `
      <li>
        <span>${name}</span>
        <div class="metric-detail-values">
          <strong>${formatMetricDelta(delta)}</strong>
          <em>${ratio !== null ? `${ratio.toFixed(3)}x` : "n/a"}</em>
        </div>
      </li>
    `;
  }).join("")}</ul>`;
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
      <td><a href="${entry.workbench_entry_path}">${entry.run_id}</a></td>
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
        <a class="panel-link" href="${panelLink(entry, "summary")}">Open Summary</a>
      </article>
    `;
  }

  const [baseline, candidate] = selectedEntries;
  const sameMetric = baseline.primary_metric_name === candidate.primary_metric_name;
  const delta = candidate.primary_metric_value - baseline.primary_metric_value;
  const ratio = baseline.primary_metric_value !== 0 ? candidate.primary_metric_value / baseline.primary_metric_value : null;
  return `
    <article class="compare-card compare-grid">
      <div>
        <h3>Baseline</h3>
        <p>${baseline.run_id}</p>
        <p>${baseline.primary_metric_name}: <strong>${baseline.primary_metric_value}</strong></p>
        ${renderMetricValueList(baseline)}
        <a class="panel-link" href="${panelLink(baseline, "summary")}">Open Summary</a>
      </div>
      <div>
        <h3>Candidate</h3>
        <p>${candidate.run_id}</p>
        <p>${candidate.primary_metric_name}: <strong>${candidate.primary_metric_value}</strong></p>
        ${renderMetricValueList(candidate)}
        <a class="panel-link" href="${panelLink(candidate, "summary")}">Open Summary</a>
      </div>
      <div>
        <h3>Shared Metric Deltas</h3>
        <p>${sameMetric ? `${candidate.primary_metric_name} delta: ${formatMetricDelta(delta)}` : "Metric mismatch"}</p>
        <p>${sameMetric && ratio !== null ? `ratio: ${ratio.toFixed(3)}x` : "ratio unavailable"}</p>
        ${buildSharedMetricDeltaRows(baseline, candidate)}
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
          <th>Link</th>
        </tr>
      </thead>
      <tbody>
        ${candidates.map((entry) => {
          const sameMetric = entry.primary_metric_name === baselineEntry.primary_metric_name;
          const delta = entry.primary_metric_value - baselineEntry.primary_metric_value;
          const ratio = baselineEntry.primary_metric_value !== 0 ? entry.primary_metric_value / baselineEntry.primary_metric_value : null;
          return `
            <tr>
              <td>${entry.run_id}</td>
              <td>${entry.schedule_kind}</td>
              <td>${entry.target_profile_name}</td>
              <td>${entry.primary_metric_name}</td>
              <td>${sameMetric ? formatMetricDelta(delta) : "metric mismatch"}</td>
              <td>${sameMetric && ratio !== null ? `${ratio.toFixed(3)}x` : "n/a"}</td>
              <td>${buildSharedMetricDeltaRows(baselineEntry, entry)}</td>
              <td><a href="${panelLink(entry, "summary")}">Open Summary</a></td>
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
              <a href="${entry.workbench_entry_path}">${entry.run_id}</a>
              <span>${entry.mode}</span>
              <span>${entry.schedule_kind}</span>
              <span>${entry.primary_metric_name}: ${entry.primary_metric_value}</span>
            </div>
            <div class="group-link-row">
              <button class="compare-toggle" data-entry-id="${entry.entry_id}" type="button">Compare</button>
              <a class="panel-link" href="${panelLink(entry, "summary")}">Summary</a>
              <a class="panel-link" href="${panelLink(entry, "timeline")}">Timeline</a>
              <a class="panel-link" href="${panelLink(entry, "memory")}">Memory</a>
              <a class="panel-link" href="${panelLink(entry, "coverage")}">Coverage</a>
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
  const swapCompareOrderButton = document.querySelector("#swap-compare-order-button");
  if (!searchInput || !modeFilter || !scheduleFilter || !compareScopeFilter || !swapCompareOrderButton) {
    return;
  }
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
  };
  searchInput.addEventListener("input", refresh);
  modeFilter.addEventListener("change", refresh);
  scheduleFilter.addEventListener("change", refresh);
  compareScopeFilter.addEventListener("change", refresh);
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

.metric-detail-values em {
  color: #5b6980;
  font-style: normal;
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
