"""Builder for SPEC-19 static visualization workbench assets."""

from __future__ import annotations

import json
from pathlib import Path

from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.contracts.visualization_workbench import (
    VisualizationWorkbenchArtifact,
    VisualizationWorkbenchAssetFile,
    VisualizationWorkbenchMetadata,
)


def build_visualization_workbench(
    bundle: VisualizationBundle,
    *,
    bundle_relative_path: str,
    workbench_root: str | Path,
) -> tuple[VisualizationWorkbenchArtifact, dict[str, str]]:
    workbench_root_path = Path(workbench_root)
    panels = ["summary", "graph", "timeline", "core-occupancy", "memory", "coverage"]
    if bundle.sweep_view is not None:
        panels.append("sweep")

    title = _build_title(bundle)
    artifact = VisualizationWorkbenchArtifact(
        workbench_id=f"workbench.{bundle.metadata.run_id}",
        metadata=VisualizationWorkbenchMetadata(
            run_id=bundle.metadata.run_id,
            graph_id=bundle.metadata.graph_id,
            scenario_name=bundle.metadata.scenario_name,
            mode=bundle.metadata.mode,
            schedule_kind=bundle.metadata.schedule_kind,
            title=title,
        ),
        entry_html_path=_normalize(workbench_root_path / "index.html"),
        bundle_path=bundle_relative_path,
        default_panel="summary",
        available_panels=panels,
        asset_files=[
            VisualizationWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "index.html"),
                media_type="text/html",
                role="entry_html",
            ),
            VisualizationWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "assets" / "app.js"),
                media_type="application/javascript",
                role="script",
            ),
            VisualizationWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "assets" / "styles.css"),
                media_type="text/css",
                role="style",
            ),
            VisualizationWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "workbench_manifest.json"),
                media_type="application/json",
                role="manifest",
            ),
        ],
    )

    files = {
        _normalize(workbench_root_path / "index.html"): _build_index_html(artifact),
        _normalize(workbench_root_path / "assets" / "app.js"): _build_app_js(bundle_relative_path),
        _normalize(workbench_root_path / "assets" / "styles.css"): _build_styles_css(),
        _normalize(workbench_root_path / "workbench_manifest.json"): json.dumps(
            artifact.model_dump(mode="json"),
            indent=2,
        ),
    }
    return artifact, files


def _build_title(bundle: VisualizationBundle) -> str:
    graph_prefix = bundle.metadata.graph_id.split("-")[0].capitalize()
    mode = bundle.metadata.mode.replace("-", " ").title()
    schedule = bundle.metadata.schedule_kind.replace("-", " ").title()
    return f"{graph_prefix} {mode} / {schedule}"


def _build_index_html(artifact: VisualizationWorkbenchArtifact) -> str:
    nav_buttons = "\n".join(
        f'          <button class="panel-tab" data-panel="{panel}">{_label_for_panel(panel)}</button>'
        for panel in artifact.available_panels
    )
    sections = "\n".join(_build_panel_shell(panel) for panel in artifact.available_panels)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{artifact.metadata.title}</title>
    <link rel="stylesheet" href="./assets/styles.css">
  </head>
  <body>
    <div class="shell">
      <header class="hero">
        <p class="eyebrow">SPEC-19 Workbench</p>
        <h1>{artifact.metadata.title}</h1>
        <p class="hero-meta">
          <span>{artifact.metadata.scenario_name}</span>
          <span>{artifact.metadata.mode}</span>
          <span>{artifact.metadata.schedule_kind}</span>
        </p>
      </header>
      <section class="workbench-actions">
        <a id="back-to-catalog-link" class="action-link" href="#" hidden>Back to Catalog Compare</a>
        <button id="copy-view-link-button" type="button">Copy current view link</button>
        <button id="download-view-json-button" type="button">Export current panel JSON</button>
        <button id="download-panel-svg-button" type="button">Export current panel SVG</button>
        <span id="workbench-action-status" class="muted">No workbench action triggered.</span>
      </section>
      <nav class="panel-tabs">
{nav_buttons}
      </nav>
      <main class="panel-stack">
{sections}
      </main>
    </div>
    <script src="./assets/app.js"></script>
  </body>
</html>
"""


def _build_app_js(bundle_relative_path: str) -> str:
    return """const BUNDLE_PATH = __BUNDLE_PATH__;
const UI_STATE = {
  graphQuery: "",
  timelineQuery: "",
  timelineStage: "all",
  timelineCore: "all",
  memoryQuery: "",
  coverageQuery: "",
  coverageFocus: "",
  sweepCandidate: "",
  sweepLayerFocus: "",
  activeDetailBlockId: null,
  catalogReturnUrl: "",
  requestedPanel: "summary",
};
const MAX_GROUPED_COMPARE_ROWS = 3;

function formatNumber(value) {
  if (typeof value !== "number") {
    return String(value);
  }
  if (Math.abs(value) >= 1000) {
    return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  return value.toFixed(2);
}

function normalizeText(value) {
  return String(value || "").toLowerCase();
}

function buildPanelLink(panelId, extraParams = {}) {
  const params = new URLSearchParams();
  params.set("panel", panelId);
  const catalogReturn = extraParams.catalog_return || UI_STATE.catalogReturnUrl;
  if (catalogReturn) {
    params.set("catalog_return", String(catalogReturn));
  }
  Object.entries(extraParams).forEach(([key, value]) => {
    if (key === "catalog_return") {
      return;
    }
    if (value !== null && value !== undefined && String(value) !== "") {
      params.set(key, String(value));
    }
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

function getActivePanelId() {
  return UI_STATE.requestedPanel || "summary";
}

function serializeUiState() {
  return {
    panel: getActivePanelId(),
    graph_query: UI_STATE.graphQuery,
    timeline_query: UI_STATE.timelineQuery,
    timeline_stage: UI_STATE.timelineStage,
    timeline_core: UI_STATE.timelineCore,
    memory_query: UI_STATE.memoryQuery,
    coverage_query: UI_STATE.coverageQuery,
    coverage_focus: UI_STATE.coverageFocus,
    sweep_candidate: UI_STATE.sweepCandidate,
    sweep_layer_focus: UI_STATE.sweepLayerFocus,
    detail_block: UI_STATE.activeDetailBlockId,
    catalog_return: UI_STATE.catalogReturnUrl,
  };
}

function buildCurrentViewUrl() {
  const state = serializeUiState();
  const panelId = state.panel || "summary";
  const { panel, ...extraParams } = state;
  return `${window.location.pathname}${buildPanelLink(panelId, extraParams)}`;
}

function hydrateStateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  UI_STATE.requestedPanel = params.get("panel") || "summary";
  UI_STATE.graphQuery = params.get("graph_query") || "";
  UI_STATE.timelineQuery = params.get("timeline_query") || "";
  UI_STATE.timelineStage = params.get("timeline_stage") || "all";
  UI_STATE.timelineCore = params.get("timeline_core") || "all";
  UI_STATE.memoryQuery = params.get("memory_query") || "";
  UI_STATE.coverageQuery = params.get("coverage_query") || "";
  UI_STATE.coverageFocus = params.get("coverage_focus") || "";
  UI_STATE.sweepCandidate = params.get("sweep_candidate") || "";
  UI_STATE.sweepLayerFocus = params.get("sweep_layer_focus") || "";
  UI_STATE.activeDetailBlockId = params.get("detail_block");
  UI_STATE.catalogReturnUrl = params.get("catalog_return") || "";
}

function updateCatalogReturnLink() {
  const link = document.querySelector("#back-to-catalog-link");
  if (!link) {
    return;
  }
  if (UI_STATE.catalogReturnUrl) {
    link.hidden = false;
    link.href = UI_STATE.catalogReturnUrl;
    link.textContent = "Back to Catalog Compare";
    return;
  }
  link.hidden = true;
  link.removeAttribute("href");
}

function syncControlsFromState() {
  const graphSearchInput = document.querySelector("#graph-search-input");
  if (graphSearchInput) {
    graphSearchInput.value = UI_STATE.graphQuery;
  }

  const timelineSearchInput = document.querySelector("#timeline-search-input");
  if (timelineSearchInput) {
    timelineSearchInput.value = UI_STATE.timelineQuery;
  }

  const timelineStageFilter = document.querySelector("#timeline-stage-filter");
  if (timelineStageFilter) {
    timelineStageFilter.value = UI_STATE.timelineStage;
  }

  const timelineCoreFilter = document.querySelector("#timeline-core-filter");
  if (timelineCoreFilter) {
    timelineCoreFilter.value = UI_STATE.timelineCore;
  }

  const memorySearchInput = document.querySelector("#memory-search-input");
  if (memorySearchInput) {
    memorySearchInput.value = UI_STATE.memoryQuery;
  }

  const coverageSearchInput = document.querySelector("#coverage-search-input");
  if (coverageSearchInput) {
    coverageSearchInput.value = UI_STATE.coverageQuery;
  }
  updateCatalogReturnLink();
}

function resolveInitialPanel(panelMap) {
  const requested = UI_STATE.requestedPanel;
  if (requested && panelMap[requested]) {
    return requested;
  }
  return "summary";
}

function setActivePanel(panelId) {
  UI_STATE.requestedPanel = panelId;
  document.querySelectorAll(".panel-tab").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.panel === panelId);
  });
  document.querySelectorAll(".panel-view").forEach((section) => {
    section.classList.toggle("is-active", section.dataset.panel === panelId);
  });
}

function renderList(items) {
  if (!items || items.length === 0) {
    return "<p class=\\"empty\\">No data.</p>";
  }
  return `<ul class="metric-list">${items.map((item) => `<li>${item}</li>`).join("")}</ul>`;
}

function renderMetricEntries(entries, emptyMessage = "No data.") {
  if (!entries || entries.length === 0) {
    return `<p class="empty">${emptyMessage}</p>`;
  }
  return `<ul class="metric-list">${entries.map(([label, value]) => `
    <li><span>${label}</span><strong>${formatNumber(value)}</strong></li>
  `).join("")}</ul>`;
}

function renderBackingStoreSummary(entries) {
  const filteredEntries = Object.entries(entries || {})
    .filter(([, value]) => Number(value) > 0)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  if (filteredEntries.length === 0) {
    return "<span class=\\"muted\\">No backing-store attribution.</span>";
  }
  return filteredEntries
    .map(([label, value]) => `${label}: ${formatNumber(value)}`)
    .join(" • ");
}

function renderMemoryClassSummary(entries) {
  const filteredEntries = Object.entries(entries || {})
    .filter(([, value]) => Number(value) > 0)
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  if (filteredEntries.length === 0) {
    return "<span class=\\"muted\\">No memory-class attribution.</span>";
  }
  return filteredEntries
    .map(([label, value]) => `${label}: ${formatNumber(value)}`)
    .join(" | ");
}

function filterGraphNodes(nodes, query) {
  const normalized = normalizeText(query).trim();
  if (!normalized) {
    return nodes;
  }
  return nodes.filter((node) =>
    [node.node_id, node.label, node.op_kind, node.dtype].some((field) => normalizeText(field).includes(normalized))
  );
}

function filterTimelineBlocks(blocks, query, stage, core) {
  const normalized = normalizeText(query).trim();
  return blocks.filter((block) => {
    const matchesQuery = !normalized || [block.block_id, block.node_id, block.macro_op, block.stage]
      .some((field) => normalizeText(field).includes(normalized));
    const matchesStage = stage === "all" || block.stage === stage;
    const matchesCore = core === "all" || String(block.core_id) === core;
    return matchesQuery && matchesStage && matchesCore;
  });
}

function filterCoverageIssues(issues, query) {
  const normalized = normalizeText(query).trim();
  if (!normalized) {
    return issues;
  }
  return issues.filter((issue) =>
    [issue.schedule_block_id, issue.requested_opcode, issue.code, issue.message]
      .some((field) => normalizeText(field).includes(normalized))
  );
}

function filterMemoryRegions(regions, query) {
  const normalized = normalizeText(query).trim();
  if (!normalized) {
    return regions;
  }
  return regions.filter((region) =>
    [
      region.region_name,
      ...Object.keys(region.peak_bytes_by_backing_store || {}),
      ...Object.keys(region.peak_bytes_by_memory_class || {}),
    ].some((field) => normalizeText(field).includes(normalized))
  );
}

function renderSummary(bundle) {
  const metrics = Object.entries(bundle.report_summary.primary_metrics || {})
    .map(([key, value]) => `<li><span>${key}</span><strong>${formatNumber(value)}</strong></li>`)
    .join("");
  return `
    <div class="card-grid">
      <article class="card hero-card">
        <h2>Run Summary</h2>
        <p class="muted">${bundle.metadata.run_id} 路 ${bundle.metadata.target_profile_name}</p>
        <ul class="metric-list">${metrics}</ul>
      </article>
      <article class="card">
        <h2>Hotspots</h2>
        ${renderList(bundle.report_summary.hotspot_macro_ops || [])}
      </article>
    </div>
  `;
}

function renderGraph(bundle) {
  const filteredNodes = filterGraphNodes(bundle.graph_view.nodes || [], UI_STATE.graphQuery);
  const nodeItems = filteredNodes.map((node) => `
    <li>
      <strong>${node.op_kind}</strong>
      <span class="muted">${node.node_id}</span>
      <span class="tag">${node.dtype}</span>
      <a class="inline-link" href="${buildPanelLink("timeline", { timeline_query: node.node_id })}">Open Timeline</a>
    </li>
  `).join("");
  return `
    <div class="card-grid">
      <article class="card">
        <h2>Graph Stats</h2>
        <ul class="metric-list">
          <li><span>Nodes</span><strong>${bundle.graph_view.node_count}</strong></li>
          <li><span>Edges</span><strong>${bundle.graph_view.edge_count}</strong></li>
          <li><span>Matched</span><strong>${filteredNodes.length}</strong></li>
        </ul>
      </article>
      <article class="card">
        <h2>Graph Nodes</h2>
        <ul class="table-list">${nodeItems || "<li class=\\"empty\\">No graph nodes match the current search.</li>"}</ul>
      </article>
    </div>
  `;
}

function renderTimeline(bundle) {
  const filteredBlocks = filterTimelineBlocks(
    bundle.timeline_view.blocks || [],
    UI_STATE.timelineQuery,
    UI_STATE.timelineStage,
    UI_STATE.timelineCore,
  );
  const rows = filteredBlocks.map((block) => `
    <tr data-block-id="${block.block_id}">
      <td>${block.order_key}</td>
      <td>${block.core_id}</td>
      <td>${block.stage || "-"}</td>
      <td>${block.macro_op || "-"}</td>
      <td>${block.node_id || "-"}</td>
    </tr>
  `).join("");
  return `
    <article class="card wide-card">
      <h2>Timeline</h2>
      <table class="data-table">
        <thead>
          <tr><th>Order</th><th>Core</th><th>Stage</th><th>Macro</th><th>Node</th></tr>
        </thead>
        <tbody>${rows || '<tr><td colspan="5" class="empty-cell">No timeline blocks match the current filters.</td></tr>'}</tbody>
      </table>
    </article>
  `;
}

function renderTimelineDetail(block) {
  if (!block) {
    return `
      <article class="card detail-card">
        <h2>Block Detail</h2>
        <p class="empty">Select a timeline row to inspect block details.</p>
      </article>
    `;
  }
  return `
    <article class="card detail-card">
      <h2>Block Detail</h2>
      <ul class="metric-list">
        <li><span>Block</span><strong>${block.block_id}</strong></li>
        <li><span>Core</span><strong>${block.core_id}</strong></li>
        <li><span>Stage</span><strong>${block.stage || "-"}</strong></li>
        <li><span>Macro</span><strong>${block.macro_op || "-"}</strong></li>
        <li><span>Node</span><strong>${block.node_id || "-"}</strong></li>
        <li><span>Transfer Bytes</span><strong>${formatNumber(block.transfer_bytes || 0)}</strong></li>
        <li><span>Sync Cycles</span><strong>${formatNumber(block.sync_cost_cycles || 0)}</strong></li>
      </ul>
      <div class="detail-link-row">
        ${block.node_id ? `<a class="inline-link" href="${buildPanelLink("graph", { graph_query: block.node_id })}">Open Graph</a>` : ""}
        ${block.block_id ? `<a class="inline-link" href="${buildPanelLink("coverage", { coverage_query: block.block_id })}">Open Coverage</a>` : ""}
      </div>
    </article>
  `;
}

function renderCoreOccupancy(bundle) {
  const rows = Object.entries(bundle.timeline_view.core_block_counts || {})
    .map(([core, count]) => `<li><span>Core ${core}</span><strong>${count} blocks</strong></li>`)
    .join("");
  return `
    <article class="card">
      <h2>Core Occupancy</h2>
      <ul class="metric-list">${rows}</ul>
    </article>
  `;
}

function renderMemory(bundle) {
  const filteredRegions = filterMemoryRegions(bundle.vmem_view.regions || [], UI_STATE.memoryQuery);
  const regionRows = filteredRegions.map((region) => `
    <tr>
      <td>${region.region_name}</td>
      <td>${formatNumber(region.capacity_bytes)}</td>
      <td>${formatNumber(region.peak_bytes)}</td>
      <td>${formatNumber(region.utilization_ratio * 100)}%</td>
    </tr>
  `).join("");
  const backingStoreRows = filteredRegions.map((region) => `
    <li>
      <strong>${region.region_name}</strong>
      <span class="muted">${renderBackingStoreSummary(region.peak_bytes_by_backing_store)}</span>
    </li>
  `).join("");
  const memoryClassRows = filteredRegions.map((region) => `
    <li>
      <strong>${region.region_name}</strong>
      <span class="muted">${renderMemoryClassSummary(region.peak_bytes_by_memory_class)}</span>
    </li>
  `).join("");
  const kvRows = (bundle.kv_view.formulas || []).map((entry) => `
    <li>
      <strong>${entry.tensor_kind}</strong> 路 ${entry.formula}
      <a class="inline-link" href="${buildPanelLink("timeline", { timeline_query: entry.node_id })}">Open Timeline</a>
    </li>
  `).join("");
  return `
    <div class="card-grid">
      <article class="card">
        <h2>VMEM Regions</h2>
        <table class="data-table">
          <thead><tr><th>Region</th><th>Capacity</th><th>Peak</th><th>Util</th></tr></thead>
          <tbody>${regionRows}</tbody>
        </table>
      </article>
      <article class="card">
        <h2>Region Backing Store Mix</h2>
        <ul class="table-list">${backingStoreRows || "<li>No region backing-store data.</li>"}</ul>
      </article>
      <article class="card">
        <h2>Region Memory Class Mix</h2>
        <ul class="table-list">${memoryClassRows || "<li>No region memory-class data.</li>"}</ul>
      </article>
      <article class="card">
        <h2>KV View</h2>
        <ul class="metric-list">
          <li><span>KV Len</span><strong>${bundle.kv_view.kv_len}</strong></li>
          <li><span>Formulas</span><strong>${bundle.kv_view.kv_formula_count}</strong></li>
          <li><span>Unresolved</span><strong>${bundle.kv_view.unresolved_address_count}</strong></li>
        </ul>
        <ul class="table-list">${kvRows}</ul>
      </article>
    </div>
  `;
}

function renderCoverage(bundle) {
  const issues = (bundle.coverage_view.issues || []).map((issue) => `<li><strong>${issue.code}</strong> 路 ${issue.message}</li>`).join("");
  return `
    <div class="card-grid">
      <article class="card">
        <h2>Coverage</h2>
        <ul class="metric-list">
          <li><span>Mapped</span><strong>${bundle.coverage_view.mapped_descriptor_count}</strong></li>
          <li><span>Unmapped</span><strong>${bundle.coverage_view.unmapped_block_count}</strong></li>
        </ul>
      </article>
      <article class="card">
        <h2>Coverage Issues</h2>
        <ul class="table-list">${issues || "<li>No issues.</li>"}</ul>
      </article>
    </div>
  `;
}

function renderCoverageEnhanced(bundle) {
  const filteredIssues = filterCoverageIssues(bundle.coverage_view.issues || [], UI_STATE.coverageQuery);
  const packedLayoutEntries = Object.entries(bundle.coverage_view.packed_layout_template_counts || {});
  const packedFieldEntries = Object.entries(bundle.coverage_view.packed_field_name_counts || {});
  const packedFieldPlacementCount = packedFieldEntries.reduce((total, [, count]) => total + count, 0);
  const issues = filteredIssues.map((issue) => `
    <li>
      <strong>${issue.code}</strong> 璺?${issue.message}
      <a class="inline-link" href="${buildPanelLink("timeline", { detail_block: issue.schedule_block_id })}">Open Timeline</a>
    </li>
  `).join("");
  return `
    <div class="card-grid">
      <article class="${coverageCardClass("overview")}">
        <h2>Coverage</h2>
        <ul class="metric-list">
          <li><span>Mapped</span><strong>${bundle.coverage_view.mapped_descriptor_count}</strong></li>
          <li><span>Unmapped</span><strong>${bundle.coverage_view.unmapped_block_count}</strong></li>
          <li><span>Matched Issues</span><strong>${filteredIssues.length}</strong></li>
        </ul>
      </article>
      <article class="${coverageCardClass("packed-descriptor")}" data-coverage-focus-target="packed-descriptor">
        <h2>Packed Descriptor Summary</h2>
        ${renderMetricEntries([
          ["Packed Records", bundle.coverage_view.packed_record_count || 0],
          ["Packed Stream Bytes", bundle.coverage_view.packed_stream_total_bytes || 0],
          ["Layout Templates", packedLayoutEntries.length],
          ["Field Placements", packedFieldPlacementCount],
        ])}
      </article>
      <article class="${coverageCardClass("packed-descriptor")}" data-coverage-focus-target="packed-descriptor">
        <h2>Packed Layout Templates</h2>
        ${renderMetricEntries(packedLayoutEntries, "No packed layout templates.")}
      </article>
      <article class="${coverageCardClass("packed-descriptor")}" data-coverage-focus-target="packed-descriptor">
        <h2>Packed Field Placements</h2>
        ${renderMetricEntries(packedFieldEntries, "No packed field placements.")}
      </article>
      <article class="${coverageCardClass("issues")}" data-coverage-focus-target="issues">
        <h2>Coverage Issues</h2>
        <ul class="table-list">${issues || "<li>No issues.</li>"}</ul>
      </article>
    </div>
  `;
}

function coverageCardClass(focusTarget) {
  if (!focusTarget || !UI_STATE.coverageFocus) {
    return "card";
  }
  return UI_STATE.coverageFocus === focusTarget ? "card is-focused" : "card";
}

function scrollCoverageFocusIntoView() {
  if (!UI_STATE.coverageFocus) {
    return;
  }
  const target = document.querySelector(
    `#content-coverage [data-coverage-focus-target="${UI_STATE.coverageFocus}"]`
  );
  if (target && typeof target.scrollIntoView === "function") {
    target.scrollIntoView({ block: "start" });
  }
}

function selectedSweepComparisons(comparisons) {
  if (!UI_STATE.sweepCandidate) {
    return comparisons || [];
  }
  return (comparisons || []).filter(
    (comparison) => comparison.candidate_target_profile_name === UI_STATE.sweepCandidate
  );
}

function selectedSweepLayerDeltas(comparison) {
  if (!UI_STATE.sweepLayerFocus) {
    return comparison.layer_deltas || [];
  }
  return (comparison.layer_deltas || []).filter(
    (layerDelta) => String(layerDelta.layer_id) === String(UI_STATE.sweepLayerFocus)
  );
}

function renderScalarDeltaRows(scalarDeltas) {
  return (scalarDeltas || []).map((scalarDelta) => `
      <li>
        <span>${scalarDelta.metric_name}</span>
        <div class="metric-detail-values">
          <strong>${formatMetricDelta(scalarDelta.delta_value)}</strong>
          <em>${formatNumber(scalarDelta.baseline_value)} -> ${formatNumber(scalarDelta.candidate_value)}</em>
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

function renderGroupedScalarDeltaSection(group) {
  const scalarDeltas = orderedGroupedScalarDeltas(group.scalar_deltas || []);
  if (!scalarDeltas.length) {
    return "";
  }
  const visibleRows = scalarDeltas.slice(0, MAX_GROUPED_COMPARE_ROWS);
  const hiddenRows = scalarDeltas.slice(MAX_GROUPED_COMPARE_ROWS);
  const overflowDetails = hiddenRows.length
    ? `
      <details class="compare-summary-details">
        <summary>Show all ${scalarDeltas.length} metrics</summary>
        <ul class="metric-detail-list">${renderScalarDeltaRows(hiddenRows)}</ul>
      </details>
    `
    : "";
  return `
      <section class="compare-summary-group">
        <p class="muted">${group.title || group.group_id}</p>
        <ul class="metric-detail-list">${renderScalarDeltaRows(visibleRows)}</ul>
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

function renderSweepCompareSummary(compareSummary, metricDeltas) {
  if (
    compareSummary
    && (
      hasScalarDeltaGroups(compareSummary)
      || (
      (compareSummary.highlighted_scalar_deltas || []).length
      || (compareSummary.scalar_deltas || []).length
      )
    )
  ) {
    const scheduleSummary = `${compareSummary.baseline_schedule_kind} -> ${compareSummary.candidate_schedule_kind}`;
    const diffFields = (compareSummary.profile_diff_fields || []).join(", ");
    const highlightedRows = compareSummary.highlighted_scalar_deltas || [];
    const scalarRows = compareSummary.scalar_deltas || [];
    const groupedRows = hasScalarDeltaGroups(compareSummary)
      ? renderScalarDeltaGroups(compareSummary)
      : "";
    const visibleRows = highlightedRows.length ? highlightedRows : scalarRows;
    const fullScalarDetails = scalarRows.length && (
      groupedRows || (highlightedRows.length && scalarRows.length > highlightedRows.length)
    )
      ? `
        <details class="compare-summary-details">
          <summary>All Scalar Deltas</summary>
          <ul class="metric-detail-list">${renderScalarDeltaRows(scalarRows)}</ul>
        </details>
      `
      : "";
    return `
      <div class="compare-summary-block">
        <p class="muted">Schedule: ${scheduleSummary}</p>
        ${diffFields ? `<p class="muted">Profile Diff Fields: ${diffFields}</p>` : ""}
        ${groupedRows || `
          ${highlightedRows.length ? `<p class="muted">Highlighted Metric Shifts</p>` : ""}
          <ul class="metric-detail-list">${renderScalarDeltaRows(visibleRows)}</ul>
        `}
        ${fullScalarDetails}
      </div>
    `;
  }
  const metricRows = Object.entries(metricDeltas || {});
  if (!metricRows.length) {
    return '<span class="muted">No matched sweep metric deltas.</span>';
  }
  return metricRows.map(([key, value]) => `${key}: ${formatNumber(value)}`).join("<br>");
}

function buildSweepSnapshotMetadata(sweepData) {
  const headerRows = [
    sweepData.baseline_target_profile_name
      ? `Baseline Sweep Target: ${sweepData.baseline_target_profile_name}`
      : "",
    sweepData.focused_sweep_candidate
      ? `Focused Sweep Candidate: ${sweepData.focused_sweep_candidate}`
      : "",
    sweepData.focused_sweep_layer
      ? `Focused Sweep Layer: ${sweepData.focused_sweep_layer}`
      : "",
    sweepData.focused_layer_delta_summary
      ? `Focused Layer Summary: ${sweepData.focused_layer_delta_summary.candidate_target_profile_name} / Layer ${sweepData.focused_layer_delta_summary.layer_id} / delta_cycles ${formatNumber(sweepData.focused_layer_delta_summary.delta_cycles)} / delta_bytes ${formatNumber(sweepData.focused_layer_delta_summary.delta_bytes)}`
      : "",
  ].filter(Boolean);
  const titleParts = ["sweep snapshot"];
  if (sweepData.focused_sweep_candidate) {
    titleParts.push(sweepData.focused_sweep_candidate);
  }
  if (sweepData.focused_sweep_layer) {
    titleParts.push(`layer ${sweepData.focused_sweep_layer}`);
  }
  return {
    title: titleParts.join(" / "),
    header_label: "Snapshot Focus",
    header_rows: headerRows,
  };
}

function buildSweepExportData(bundle) {
  const emptySweepData = {
    baseline_target_profile_name: null,
    focused_sweep_candidate: UI_STATE.sweepCandidate || null,
    focused_sweep_layer: UI_STATE.sweepLayerFocus || null,
    focused_comparison_count: 0,
    focused_layer_delta_count: 0,
    focused_layer_delta_summary: null,
    comparisons: [],
  };
  if (!bundle.sweep_view) {
    return {
      ...emptySweepData,
      snapshot_metadata: buildSweepSnapshotMetadata(emptySweepData),
    };
  }
  const comparisons = selectedSweepComparisons(bundle.sweep_view.comparisons || []).map((comparison) => ({
    ...comparison,
    layer_deltas: selectedSweepLayerDeltas(comparison),
  }));
  const focusedLayerDeltaSummary = UI_STATE.sweepLayerFocus
    ? (() => {
        for (const comparison of comparisons) {
          for (const layerDelta of comparison.layer_deltas || []) {
            return {
              candidate_target_profile_name: comparison.candidate_target_profile_name,
              scenario_name: comparison.scenario_name,
              mode: comparison.mode,
              layer_id: layerDelta.layer_id,
              baseline_cycles: layerDelta.baseline_cycles,
              candidate_cycles: layerDelta.candidate_cycles,
              delta_cycles: layerDelta.delta_cycles,
              baseline_bytes: layerDelta.baseline_bytes,
              candidate_bytes: layerDelta.candidate_bytes,
              delta_bytes: layerDelta.delta_bytes,
            };
          }
        }
        return null;
      })()
    : null;
  const sweepData = {
    baseline_target_profile_name: bundle.sweep_view.baseline_target_profile_name || null,
    focused_sweep_candidate: UI_STATE.sweepCandidate || null,
    focused_sweep_layer: UI_STATE.sweepLayerFocus || null,
    focused_comparison_count: comparisons.length,
    focused_layer_delta_count: comparisons.reduce(
      (total, comparison) => total + ((comparison.layer_deltas || []).length),
      0,
    ),
    focused_layer_delta_summary: focusedLayerDeltaSummary,
    comparisons,
  };
  return {
    ...sweepData,
    snapshot_metadata: buildSweepSnapshotMetadata(sweepData),
  };
}

function renderSweep(bundle) {
  if (!bundle.sweep_view) {
    return `<article class="card"><h2>Sweep</h2><p class="empty">No sweep context.</p></article>`;
  }
  const sweepData = buildSweepExportData(bundle);
  const comparisons = sweepData.comparisons || [];
  const focusSummary = [
    sweepData.baseline_target_profile_name
      ? `Baseline Sweep Target: ${sweepData.baseline_target_profile_name}`
      : "",
    sweepData.focused_sweep_candidate
      ? `Focused Sweep Candidate: ${sweepData.focused_sweep_candidate}`
      : "",
    sweepData.focused_sweep_layer ? `Focused Sweep Layer: ${sweepData.focused_sweep_layer}` : "",
    `Focused Comparisons: ${sweepData.focused_comparison_count}`,
    `Focused Layer Deltas: ${sweepData.focused_layer_delta_count}`,
    sweepData.focused_layer_delta_summary
      ? `Focused Layer Summary: ${sweepData.focused_layer_delta_summary.candidate_target_profile_name} / Layer ${sweepData.focused_layer_delta_summary.layer_id} / delta_cycles ${formatNumber(sweepData.focused_layer_delta_summary.delta_cycles)} / delta_bytes ${formatNumber(sweepData.focused_layer_delta_summary.delta_bytes)}`
      : "",
  ].filter(Boolean).map((line) => `<p class="muted">${line}</p>`).join("");
  const rows = comparisons.map((comparison) => `
    <tr>
      <td>${comparison.candidate_target_profile_name}</td>
      <td>${comparison.scenario_name}</td>
      <td>${comparison.mode}</td>
      <td>${renderSweepCompareSummary(comparison.compare_summary, comparison.metric_deltas)}</td>
      <td>${(comparison.layer_deltas || []).length > 0
        ? (comparison.layer_deltas || []).map((layerDelta) =>
            `<span class="${sweepData.focused_sweep_layer && String(layerDelta.layer_id) === String(sweepData.focused_sweep_layer) ? "focused-sweep-row" : ""}">Layer ${layerDelta.layer_id}: delta_cycles ${formatNumber(layerDelta.delta_cycles)}, delta_bytes ${formatNumber(layerDelta.delta_bytes)}</span>`
          ).join("<br>")
        : `<span class="muted">${sweepData.focused_sweep_layer ? "Focused sweep layer not found." : "No layer deltas."}</span>`}</td>
    </tr>
  `).join("");
  return `
    <article class="card wide-card">
      <h2>Sweep Comparison</h2>
      ${focusSummary}
      <table class="data-table">
        <thead><tr><th>Candidate</th><th>Scenario</th><th>Mode</th><th>Metric Deltas</th><th>Layer Deltas</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="5" class="empty-cell">No sweep comparisons match the current focus.</td></tr>'}</tbody>
      </table>
    </article>
  `;
}

function buildPanelExportData(bundle, panelId) {
  const state = serializeUiState();
  switch (panelId) {
    case "summary":
      return {
        panel: panelId,
        ui_state: state,
        data: {
          primary_metrics: bundle.report_summary.primary_metrics || {},
          hotspot_macro_ops: bundle.report_summary.hotspot_macro_ops || [],
        },
      };
    case "graph":
      return {
        panel: panelId,
        ui_state: state,
        data: {
          matched_nodes: filterGraphNodes(bundle.graph_view.nodes || [], UI_STATE.graphQuery),
          op_counts: bundle.graph_view.op_counts || {},
        },
      };
    case "timeline":
      return {
        panel: panelId,
        ui_state: state,
        data: {
          matched_blocks: filterTimelineBlocks(
            bundle.timeline_view.blocks || [],
            UI_STATE.timelineQuery,
            UI_STATE.timelineStage,
            UI_STATE.timelineCore,
          ),
          active_detail_block: UI_STATE.activeDetailBlockId,
        },
      };
    case "core-occupancy":
      return {
        panel: panelId,
        ui_state: state,
        data: {
          core_block_counts: bundle.timeline_view.core_block_counts || {},
        },
      };
    case "memory":
      return {
        panel: panelId,
        ui_state: state,
        data: {
          regions: filterMemoryRegions(bundle.vmem_view.regions || [], UI_STATE.memoryQuery),
          kv_formulas: bundle.kv_view.formulas || [],
        },
      };
    case "coverage":
      return {
        panel: panelId,
        ui_state: state,
        data: {
          matched_issues: filterCoverageIssues(bundle.coverage_view.issues || [], UI_STATE.coverageQuery),
          gap_counts: bundle.coverage_view.gap_counts || {},
          packed_record_count: bundle.coverage_view.packed_record_count || 0,
          packed_stream_total_bytes: bundle.coverage_view.packed_stream_total_bytes || 0,
          packed_layout_template_counts: bundle.coverage_view.packed_layout_template_counts || {},
          packed_field_name_counts: bundle.coverage_view.packed_field_name_counts || {},
        },
      };
    case "sweep":
      return {
        panel: panelId,
        ui_state: state,
        data: buildSweepExportData(bundle),
      };
    default:
      return {
        panel: panelId,
        ui_state: state,
        data: {},
      };
  }
}

function buildPanelSnapshotLines(bundle, panelId) {
  const payload = buildPanelExportData(bundle, panelId);
  const lines = [
    `Run: ${bundle.metadata.run_id}`,
    `Panel: ${panelId}`,
    `Mode: ${bundle.metadata.mode}`,
    `Schedule: ${bundle.metadata.schedule_kind}`,
  ];

  switch (panelId) {
    case "summary":
      Object.entries(payload.data.primary_metrics || {}).slice(0, 6).forEach(([key, value]) => {
        lines.push(`${key}: ${formatNumber(value)}`);
      });
      break;
    case "graph":
      lines.push(`Matched Nodes: ${(payload.data.matched_nodes || []).length}`);
      (payload.data.matched_nodes || []).slice(0, 5).forEach((node) => {
        lines.push(`${node.node_id}: ${node.op_kind}`);
      });
      break;
    case "timeline":
      lines.push(`Matched Blocks: ${(payload.data.matched_blocks || []).length}`);
      if (payload.data.active_detail_block) {
        lines.push(`Detail Block: ${payload.data.active_detail_block}`);
      }
      (payload.data.matched_blocks || []).slice(0, 5).forEach((block) => {
        lines.push(`${block.block_id}: ${block.stage || "-"} / ${block.macro_op || "-"}`);
      });
      break;
    case "core-occupancy":
      Object.entries(payload.data.core_block_counts || {}).forEach(([core, count]) => {
        lines.push(`Core ${core}: ${count} blocks`);
      });
      break;
    case "memory":
      lines.push(`Regions: ${(payload.data.regions || []).length}`);
      lines.push(`KV Formulas: ${(payload.data.kv_formulas || []).length}`);
      if ((payload.data.regions || []).length > 0) {
        const topRegion = payload.data.regions[0];
        lines.push(`Top Region: ${topRegion.region_name}`);
        Object.entries(topRegion.peak_bytes_by_backing_store || {})
          .filter(([, value]) => Number(value) > 0)
          .slice(0, 3)
          .forEach(([name, value]) => {
            lines.push(`Top Region Backing Stores ${name}: ${formatNumber(value)}`);
          });
        Object.entries(topRegion.peak_bytes_by_memory_class || {})
          .filter(([, value]) => Number(value) > 0)
          .slice(0, 3)
          .forEach(([name, value]) => {
            lines.push(`Top Region Memory Classes ${name}: ${formatNumber(value)}`);
          });
      }
      break;
    case "coverage":
      lines.push(`Matched Issues: ${(payload.data.matched_issues || []).length}`);
      lines.push(`Packed Records: ${formatNumber(payload.data.packed_record_count || 0)}`);
      lines.push(`Packed Stream Bytes: ${formatNumber(payload.data.packed_stream_total_bytes || 0)}`);
      Object.entries(payload.data.packed_layout_template_counts || {}).slice(0, 3).forEach(([name, count]) => {
        lines.push(`Layout ${name}: ${formatNumber(count)}`);
      });
      Object.entries(payload.data.packed_field_name_counts || {}).slice(0, 3).forEach(([name, count]) => {
        lines.push(`Field ${name}: ${formatNumber(count)}`);
      });
      (payload.data.matched_issues || []).slice(0, 5).forEach((issue) => {
        lines.push(`${issue.schedule_block_id}: ${issue.code}`);
      });
      break;
    case "sweep":
      const snapshotHeaderRows =
        payload.data.snapshot_metadata && Array.isArray(payload.data.snapshot_metadata.header_rows)
          ? payload.data.snapshot_metadata.header_rows.filter(Boolean)
          : [];
      if (snapshotHeaderRows.length === 0 && payload.data.baseline_target_profile_name) {
        lines.push(`Baseline Sweep Target: ${payload.data.baseline_target_profile_name}`);
      }
      lines.push(`Comparisons: ${(payload.data.comparisons || []).length}`);
      lines.push(`Focused Comparisons: ${payload.data.focused_comparison_count || 0}`);
      lines.push(`Focused Layer Deltas: ${payload.data.focused_layer_delta_count || 0}`);
      if (snapshotHeaderRows.length === 0 && payload.data.focused_sweep_candidate) {
        lines.push(`Focused Sweep Candidate: ${payload.data.focused_sweep_candidate}`);
      }
      if (snapshotHeaderRows.length === 0 && payload.data.focused_sweep_layer) {
        lines.push(`Focused Sweep Layer: ${payload.data.focused_sweep_layer}`);
      }
      if (snapshotHeaderRows.length === 0 && payload.data.focused_layer_delta_summary) {
        lines.push(
          `Focused Layer Summary: ${payload.data.focused_layer_delta_summary.candidate_target_profile_name} / Layer ${payload.data.focused_layer_delta_summary.layer_id} / delta_cycles ${formatNumber(payload.data.focused_layer_delta_summary.delta_cycles)} / delta_bytes ${formatNumber(payload.data.focused_layer_delta_summary.delta_bytes)}`
        );
      }
      (payload.data.comparisons || []).slice(0, 3).forEach((comparison) => {
        lines.push(`${comparison.candidate_target_profile_name}: ${(comparison.layer_deltas || []).length} layer deltas`);
        (comparison.layer_deltas || []).slice(0, 2).forEach((layerDelta) => {
          lines.push(`Layer ${layerDelta.layer_id}: delta_cycles ${formatNumber(layerDelta.delta_cycles)}`);
        });
      });
      break;
    default:
      lines.push("No panel-specific snapshot lines.");
      break;
  }

  return lines;
}

function escapeSvgText(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;");
}

function buildPanelSnapshotTitle(bundle, panelId, payload) {
  if (payload.data.snapshot_metadata && payload.data.snapshot_metadata.title) {
    return payload.data.snapshot_metadata.title;
  }
  if (panelId !== "sweep") {
    return `${panelId} snapshot`;
  }
  const parts = ["sweep snapshot"];
  if (payload.data.focused_sweep_candidate) {
    parts.push(payload.data.focused_sweep_candidate);
  }
  if (payload.data.focused_sweep_layer) {
    parts.push(`layer ${payload.data.focused_sweep_layer}`);
  }
  return parts.join(" / ");
}

function renderPanelSnapshotHeader(payload, topY) {
  const metadata = payload.data.snapshot_metadata || null;
  const headerRows = metadata && Array.isArray(metadata.header_rows) ? metadata.header_rows.filter(Boolean) : [];
  if (headerRows.length === 0) {
    return { svg: "", height: 0 };
  }
  const rowGap = 20;
  const blockHeight = 44 + (headerRows.length * rowGap);
  const blockWidth = 1136;
  const textRows = headerRows.map((line, index) => {
    const y = topY + 46 + (index * rowGap);
    return `<text x="52" y="${y}" font-size="15" fill="#102033">${escapeSvgText(line)}</text>`;
  }).join("");
  return {
    svg: `
  <rect x="32" y="${topY}" width="${blockWidth}" height="${blockHeight}" rx="18" fill="#edf7fb" stroke="#9ac7d8" />
  <text x="52" y="${topY + 24}" font-size="13" fill="#0b4f6c">${escapeSvgText(metadata.header_label || "Snapshot Focus")}</text>
  ${textRows}`.trim(),
    height: blockHeight + 20,
  };
}

function buildPanelSnapshotSvg(bundle, panelId) {
  const payload = buildPanelExportData(bundle, panelId);
  const lines = buildPanelSnapshotLines(bundle, panelId);
  const snapshotTitle = buildPanelSnapshotTitle(bundle, panelId, payload);
  const snapshotHeader = renderPanelSnapshotHeader(payload, 92);
  const lineHeight = 24;
  const bodyStartY = 84 + snapshotHeader.height;
  const height = 120 + snapshotHeader.height + (lines.length * lineHeight);
  const textRows = lines.map((line, index) => {
    const y = bodyStartY + (index * lineHeight);
    return `<text x="32" y="${y}" font-size="16" fill="#102033">${escapeSvgText(line)}</text>`;
  }).join("");

  return `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="${height}" viewBox="0 0 1200 ${height}">
  <rect width="1200" height="${height}" fill="#f3efe4" />
  <rect x="24" y="24" width="1152" height="${height - 48}" rx="24" fill="#fffaf1" stroke="#d9d1c4" />
  <text x="32" y="52" font-size="28" font-family="Georgia, Times New Roman, serif" fill="#102033">${escapeSvgText(bundle.metadata.run_id)}</text>
  <text x="32" y="76" font-size="18" fill="#5b6980">${escapeSvgText(snapshotTitle)}</text>
  ${snapshotHeader.svg}
  ${textRows}
</svg>`.trim();
}

function slugifyFileSegment(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "focus";
}

function buildPanelExportFilename(bundle, panelId, payload, suffix) {
  const segments = [bundle.metadata.run_id, panelId];
  if (panelId === "sweep") {
    if (payload.data.focused_sweep_candidate) {
      segments.push(slugifyFileSegment(payload.data.focused_sweep_candidate));
    }
    if (payload.data.focused_sweep_layer) {
      segments.push(`layer-${slugifyFileSegment(payload.data.focused_sweep_layer)}`);
    }
  }
  return `${segments.join("-")}-${suffix}`;
}

function renderPanel(bundle, panelId) {
  switch (panelId) {
    case "summary": return renderSummary(bundle);
    case "graph": return renderGraph(bundle);
    case "timeline": return renderTimeline(bundle);
    case "core-occupancy": return renderCoreOccupancy(bundle);
    case "memory": return renderMemory(bundle);
    case "coverage": return renderCoverageEnhanced(bundle);
    case "sweep": return renderSweep(bundle);
    default: return `<article class="card"><p class="empty">Unknown panel.</p></article>`;
  }
}

function renderIntoShell(bundle, panelId) {
  const content = document.querySelector(`#content-${panelId}`);
  if (content) {
    content.innerHTML = renderPanel(bundle, panelId);
  }
  if (panelId === "coverage") {
    scrollCoverageFocusIntoView();
  }
  if (panelId === "timeline") {
    bindTimelineRows(bundle);
    refreshTimelineDetail(bundle);
  }
}

function setWorkbenchActionStatus(message) {
  const status = document.querySelector("#workbench-action-status");
  if (status) {
    status.textContent = message;
  }
}

function bindTimelineRows(bundle) {
  const filteredBlocks = filterTimelineBlocks(
    bundle.timeline_view.blocks || [],
    UI_STATE.timelineQuery,
    UI_STATE.timelineStage,
    UI_STATE.timelineCore,
  );
  if (filteredBlocks.length > 0 && !filteredBlocks.some((block) => block.block_id === UI_STATE.activeDetailBlockId)) {
    UI_STATE.activeDetailBlockId = filteredBlocks[0].block_id;
  }
  document.querySelectorAll("#content-timeline tbody tr[data-block-id]").forEach((row) => {
    row.addEventListener("click", () => {
      UI_STATE.activeDetailBlockId = row.dataset.blockId;
      refreshTimelineDetail(bundle);
    });
  });
}

function refreshTimelineDetail(bundle) {
  const detailPanel = document.querySelector("#timeline-detail-panel");
  if (!detailPanel) {
    return;
  }
  const block = (bundle.timeline_view.blocks || []).find((item) => item.block_id === UI_STATE.activeDetailBlockId) || null;
  detailPanel.innerHTML = renderTimelineDetail(block);
  document.querySelectorAll("#content-timeline tbody tr[data-block-id]").forEach((row) => {
    row.classList.toggle("is-active", row.dataset.blockId === UI_STATE.activeDetailBlockId);
  });
}

function updateGraph(bundle) {
  renderIntoShell(bundle, "graph");
}

function updateTimeline(bundle) {
  renderIntoShell(bundle, "timeline");
}

async function copyCurrentViewLink() {
  const url = buildCurrentViewUrl();
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(url);
    setWorkbenchActionStatus("Saved view link copied.");
    return;
  }
  setWorkbenchActionStatus(`Saved view link ready: ${url}`);
}

function downloadCurrentViewJson(bundle) {
  const panelId = getActivePanelId();
  const payload = buildPanelExportData(bundle, panelId);
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = buildPanelExportFilename(bundle, panelId, payload, "view.json");
  anchor.click();
  URL.revokeObjectURL(downloadUrl);
  setWorkbenchActionStatus(`Exported ${panelId} panel JSON.`);
}

function downloadCurrentPanelSvg(bundle) {
  const panelId = getActivePanelId();
  const payload = buildPanelExportData(bundle, panelId);
  const svg = buildPanelSnapshotSvg(bundle, panelId);
  const blob = new Blob([svg], { type: "image/svg+xml" });
  const downloadUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = buildPanelExportFilename(bundle, panelId, payload, "snapshot.svg");
  anchor.click();
  URL.revokeObjectURL(downloadUrl);
  setWorkbenchActionStatus(`Exported ${panelId} panel SVG.`);
}

function bindControls(bundle) {
  const graphSearchInput = document.querySelector("#graph-search-input");
  if (graphSearchInput) {
    graphSearchInput.addEventListener("input", (event) => {
      UI_STATE.graphQuery = event.target.value;
      updateGraph(bundle);
    });
  }

  const timelineSearchInput = document.querySelector("#timeline-search-input");
  if (timelineSearchInput) {
    timelineSearchInput.addEventListener("input", (event) => {
      UI_STATE.timelineQuery = event.target.value;
      updateTimeline(bundle);
    });
  }

  const timelineStageFilter = document.querySelector("#timeline-stage-filter");
  if (timelineStageFilter) {
    timelineStageFilter.addEventListener("change", (event) => {
      UI_STATE.timelineStage = event.target.value;
      updateTimeline(bundle);
    });
  }

  const timelineCoreFilter = document.querySelector("#timeline-core-filter");
  if (timelineCoreFilter) {
    timelineCoreFilter.addEventListener("change", (event) => {
      UI_STATE.timelineCore = event.target.value;
      updateTimeline(bundle);
    });
  }

  const memorySearchInput = document.querySelector("#memory-search-input");
  if (memorySearchInput) {
    memorySearchInput.addEventListener("input", (event) => {
      UI_STATE.memoryQuery = event.target.value;
      renderIntoShell(bundle, "memory");
    });
  }

  const coverageSearchInput = document.querySelector("#coverage-search-input");
  if (coverageSearchInput) {
    coverageSearchInput.addEventListener("input", (event) => {
      UI_STATE.coverageQuery = event.target.value;
      renderIntoShell(bundle, "coverage");
    });
  }
}

function bindWorkbenchActions(bundle) {
  const copyButton = document.querySelector("#copy-view-link-button");
  if (copyButton) {
    copyButton.addEventListener("click", () => {
      copyCurrentViewLink().catch((error) => {
        setWorkbenchActionStatus(`Saved view copy failed: ${error.message}`);
      });
    });
  }

  const downloadButton = document.querySelector("#download-view-json-button");
  if (downloadButton) {
    downloadButton.addEventListener("click", () => {
      downloadCurrentViewJson(bundle);
    });
  }

  const svgButton = document.querySelector("#download-panel-svg-button");
  if (svgButton) {
    svgButton.addEventListener("click", () => {
      downloadCurrentPanelSvg(bundle);
    });
  }
}

async function main() {
  const response = await fetch(BUNDLE_PATH);
  if (!response.ok) {
    throw new Error(`Failed to load bundle: ${response.status}`);
  }
  const bundle = await response.json();
  const available = new Set(bundle.view_index.available_views || []);
  const panelMap = {
    summary: true,
    graph: available.has("graph"),
    timeline: available.has("timeline"),
    "core-occupancy": available.has("timeline"),
    memory: available.has("vmem") || available.has("kv"),
    coverage: available.has("coverage"),
    sweep: available.has("sweep"),
  };

  hydrateStateFromUrl();
  document.querySelectorAll(".panel-tab").forEach((button) => {
    const panelId = button.dataset.panel;
    if (!panelMap[panelId]) {
      button.remove();
      const section = document.querySelector(`#panel-${panelId}`);
      if (section) {
        section.remove();
      }
      return;
    }
    button.addEventListener("click", () => setActivePanel(panelId));
  });

  bindControls(bundle);
  bindWorkbenchActions(bundle);
  syncControlsFromState();
  document.querySelectorAll(".panel-view").forEach((section) => {
    renderIntoShell(bundle, section.dataset.panel);
  });
  const initialPanel = resolveInitialPanel(panelMap);
  setActivePanel(initialPanel);
}

main().catch((error) => {
  document.querySelector(".panel-stack").innerHTML = `<article class="card error-card"><h2>Workbench Error</h2><p>${error.message}</p></article>`;
});
""".replace("__BUNDLE_PATH__", json.dumps(bundle_relative_path))


def _build_styles_css() -> str:
    return """html, body {
  margin: 0;
  min-height: 100%;
  background:
    radial-gradient(circle at top left, rgba(255, 214, 10, 0.18), transparent 28%),
    radial-gradient(circle at top right, rgba(28, 181, 224, 0.18), transparent 24%),
    linear-gradient(180deg, #08111f 0%, #10192d 48%, #f3efe4 48%, #f3efe4 100%);
  color: #102033;
  font-family: "Trebuchet MS", "Segoe UI", sans-serif;
}

.shell {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}

.hero {
  color: #f5f1e6;
  padding: 24px 28px 28px;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(10, 21, 39, 0.92), rgba(23, 46, 74, 0.92));
  box-shadow: 0 24px 60px rgba(8, 17, 31, 0.22);
}

.eyebrow {
  margin: 0 0 8px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 12px;
  color: #ffd60a;
}

.hero h1 {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(2rem, 4vw, 3.4rem);
}

.hero-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 14px 0 0;
}

.hero-meta span,
.panel-tab {
  border: 1px solid rgba(245, 241, 230, 0.16);
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
}

.panel-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 22px 0 18px;
}

.workbench-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 18px 0 12px;
}

.workbench-actions button {
  border: 1px solid rgba(16, 32, 51, 0.12);
  border-radius: 999px;
  padding: 10px 14px;
  background: rgba(255, 251, 244, 0.92);
  color: #102033;
  cursor: pointer;
  font-weight: 700;
}

.action-link {
  text-decoration: none;
  border: 1px solid rgba(16, 32, 51, 0.12);
  border-radius: 999px;
  padding: 10px 14px;
  background: rgba(255, 251, 244, 0.92);
  color: #102033;
  font-weight: 700;
}

.panel-tab {
  background: rgba(255, 255, 255, 0.68);
  color: #102033;
  cursor: pointer;
}

.panel-tab.is-active {
  background: #102033;
  color: #f5f1e6;
  border-color: #102033;
}

.panel-view {
  display: none;
}

.panel-view.is-active {
  display: block;
}

.panel-shell {
  display: grid;
  gap: 18px;
}

.panel-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.panel-tool {
  min-width: 180px;
  display: grid;
  gap: 6px;
}

.panel-tool span {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5b6980;
}

.panel-tool input,
.panel-tool select {
  border: 1px solid rgba(16, 32, 51, 0.16);
  border-radius: 14px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.9);
  color: #102033;
}

.panel-tool input:focus,
.panel-tool select:focus {
  outline: 2px solid rgba(28, 181, 224, 0.28);
  border-color: rgba(28, 181, 224, 0.72);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
}

.card,
.wide-card {
  background: rgba(255, 251, 244, 0.92);
  border: 1px solid rgba(16, 32, 51, 0.08);
  border-radius: 22px;
  padding: 20px;
  box-shadow: 0 16px 40px rgba(16, 32, 51, 0.08);
}

.card.is-focused {
  border-color: rgba(28, 181, 224, 0.72);
  box-shadow: 0 18px 44px rgba(28, 181, 224, 0.18);
}

.focused-sweep-row {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 8px;
  background: rgba(28, 181, 224, 0.14);
  color: #0b4f6c;
}

.wide-card {
  overflow-x: auto;
}

.card h2,
.wide-card h2 {
  margin-top: 0;
  font-family: Georgia, "Times New Roman", serif;
}

.metric-list,
.table-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.metric-list li,
.table-list li {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(16, 32, 51, 0.08);
}

.table-list li {
  display: block;
}

.table-list li strong {
  display: inline-block;
  margin-right: 8px;
}

.tag {
  display: inline-block;
  margin-top: 8px;
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  background: rgba(255, 214, 10, 0.16);
  color: #7a5700;
}

.metric-list li:last-child,
.table-list li:last-child {
  border-bottom: 0;
}

.compare-summary-group + .compare-summary-group {
  margin-top: 12px;
}

.compare-summary-group .compare-summary-details {
  margin-top: 8px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table th,
.data-table td {
  text-align: left;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(16, 32, 51, 0.08);
}

.data-table th {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #5b6980;
}

.data-table tbody tr {
  cursor: pointer;
  transition: background 120ms ease;
}

.data-table tbody tr:hover {
  background: rgba(16, 32, 51, 0.04);
}

.data-table tbody tr.is-active {
  background: rgba(28, 181, 224, 0.12);
}

.empty-cell {
  color: #5b6980;
  text-align: center;
}

.muted,
.empty {
  color: #5b6980;
}

.detail-card {
  min-height: 220px;
}

.inline-link {
  display: inline-flex;
  align-items: center;
  margin-top: 8px;
  color: #0d4f8b;
  text-decoration: none;
  font-weight: 700;
}

.detail-link-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.error-card {
  border-color: rgba(163, 0, 0, 0.18);
  background: rgba(255, 245, 245, 0.92);
}

@media (max-width: 720px) {
  .shell {
    padding: 18px 14px 40px;
  }

  .hero {
    padding: 20px;
  }
}
"""


def _label_for_panel(panel: str) -> str:
    labels = {
        "summary": "Summary",
        "graph": "Graph",
        "timeline": "Timeline",
        "core-occupancy": "Core Occupancy",
        "memory": "VMEM + KV",
        "coverage": "ISA Coverage",
        "sweep": "Sweep",
    }
    return labels[panel]


def _build_panel_shell(panel: str) -> str:
    if panel == "graph":
        return """          <section class="panel-view" id="panel-graph" data-panel="graph">
            <div class="panel-shell">
              <div class="panel-tools">
                <label class="panel-tool" for="graph-search-input">
                  <span>Graph Search</span>
                  <input id="graph-search-input" type="search" placeholder="Search node id, op, dtype">
                </label>
              </div>
              <div id="content-graph"></div>
            </div>
          </section>"""

    if panel == "timeline":
        return """          <section class="panel-view" id="panel-timeline" data-panel="timeline">
            <div class="panel-shell">
              <div class="panel-tools">
                <label class="panel-tool" for="timeline-search-input">
                  <span>Timeline Search</span>
                  <input id="timeline-search-input" type="search" placeholder="Search block, node, macro">
                </label>
                <label class="panel-tool" for="timeline-stage-filter">
                  <span>Stage Filter</span>
                  <select id="timeline-stage-filter">
                    <option value="all">All stages</option>
                    <option value="dma_in">dma_in</option>
                    <option value="prepare">prepare</option>
                    <option value="compute">compute</option>
                    <option value="store">store</option>
                    <option value="transfer">transfer</option>
                  </select>
                </label>
                <label class="panel-tool" for="timeline-core-filter">
                  <span>Core Filter</span>
                  <select id="timeline-core-filter">
                    <option value="all">All cores</option>
                    <option value="0">Core 0</option>
                    <option value="1">Core 1</option>
                    <option value="both">Both</option>
                  </select>
                </label>
              </div>
              <div id="content-timeline"></div>
              <div id="timeline-detail-panel"></div>
            </div>
          </section>"""

    if panel == "coverage":
        return """          <section class="panel-view" id="panel-coverage" data-panel="coverage">
            <div class="panel-shell">
              <div class="panel-tools">
                <label class="panel-tool" for="coverage-search-input">
                  <span>Coverage Search</span>
                  <input id="coverage-search-input" type="search" placeholder="Search block, opcode, issue">
                </label>
              </div>
              <div id="content-coverage"></div>
            </div>
          </section>"""

    if panel == "memory":
        return """          <section class="panel-view" id="panel-memory" data-panel="memory">
            <div class="panel-shell">
              <div class="panel-tools">
                <label class="panel-tool" for="memory-search-input">
                  <span>Memory Search</span>
                  <input id="memory-search-input" type="search" placeholder="Search region, backing store, memory class">
                </label>
              </div>
              <div id="content-memory"></div>
            </div>
          </section>"""

    return f"""          <section class="panel-view" id="panel-{panel}" data-panel="{panel}">
            <div id="content-{panel}"></div>
          </section>"""


def _normalize(path: Path) -> str:
    return str(path).replace("\\", "/")
