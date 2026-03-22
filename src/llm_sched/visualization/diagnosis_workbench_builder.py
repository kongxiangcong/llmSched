"""Builder for static diagnosis workbench assets."""

from __future__ import annotations

import json
from pathlib import Path

from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle
from llm_sched.contracts.diagnosis_workbench import (
    DiagnosisWorkbenchArtifact,
    DiagnosisWorkbenchAssetFile,
    DiagnosisWorkbenchMetadata,
    DiagnosisWorkbenchPanelExportFile,
)


def build_diagnosis_workbench(
    bundle: DiagnosisBundle,
    *,
    bundle_relative_path: str,
    workbench_root: str | Path,
) -> tuple[DiagnosisWorkbenchArtifact, dict[str, str]]:
    workbench_root_path = Path(workbench_root)
    panels = list(bundle.available_panels)
    deep_links = {panel: f"#/{panel}" for panel in panels}
    panel_exports = {
        panel: [
            DiagnosisWorkbenchPanelExportFile(
                path=_normalize(workbench_root_path / "exports" / f"{panel}.json"),
                media_type="application/json",
            ),
            DiagnosisWorkbenchPanelExportFile(
                path=_normalize(workbench_root_path / "exports" / f"{panel}.svg"),
                media_type="image/svg+xml",
            ),
        ]
        for panel in panels
    }
    artifact = DiagnosisWorkbenchArtifact(
        workbench_id=f"diagnosis-workbench.{bundle.metadata.run_id}",
        metadata=DiagnosisWorkbenchMetadata(
            run_id=bundle.metadata.run_id,
            graph_id=bundle.metadata.graph_id,
            scenario_name=bundle.metadata.scenario_name,
            report_kind=bundle.metadata.report_kind,
            schedule_kind=bundle.metadata.schedule_kind,
            title=_build_title(bundle),
        ),
        entry_html_path=_normalize(workbench_root_path / "index.html"),
        bundle_path=bundle_relative_path,
        default_panel="summary",
        available_panels=panels,
        deep_links=deep_links,
        panel_exports=panel_exports,
        asset_files=[
            DiagnosisWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "index.html"),
                media_type="text/html",
                role="entry_html",
            ),
            DiagnosisWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "assets" / "app.js"),
                media_type="application/javascript",
                role="script",
            ),
            DiagnosisWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "assets" / "styles.css"),
                media_type="text/css",
                role="style",
            ),
            DiagnosisWorkbenchAssetFile(
                path=_normalize(workbench_root_path / "workbench_manifest.json"),
                media_type="application/json",
                role="manifest",
            ),
        ],
    )

    files = {
        _normalize(workbench_root_path / "index.html"): _build_index_html(artifact, bundle),
        _normalize(workbench_root_path / "assets" / "app.js"): _build_app_js(artifact, bundle_relative_path),
        _normalize(workbench_root_path / "assets" / "styles.css"): _build_styles_css(),
        _normalize(workbench_root_path / "workbench_manifest.json"): json.dumps(
            artifact.model_dump(mode="json"),
            indent=2,
        ),
    }
    return artifact, files


def _build_title(bundle: DiagnosisBundle) -> str:
    graph_name = bundle.metadata.graph_id.split("::")[-1]
    report_kind_slug = bundle.metadata.report_kind.lower()
    if graph_name.endswith(f"-{report_kind_slug}"):
        graph_name = graph_name[: -(len(report_kind_slug) + 1)]
    model_name = graph_name.replace("-", " ").title()
    report_kind = bundle.metadata.report_kind.title()
    schedule = bundle.metadata.schedule_kind.replace("-", " ").title()
    return f"{model_name} {report_kind} Diagnosis / {schedule}"


def _build_index_html(artifact: DiagnosisWorkbenchArtifact, bundle: DiagnosisBundle) -> str:
    nav_buttons = "\n".join(
        f'          <button class="panel-tab" data-panel="{panel}">{panel}</button>'
        for panel in artifact.available_panels
    )
    panel_sections = "\n".join(
        f'          <section class="panel-view" id="panel-{panel}" data-panel="{panel}"><div id="content-{panel}"></div></section>'
        for panel in artifact.available_panels
    )
    embedded_bundle_json = json.dumps(bundle.model_dump(mode="json"), separators=(",", ":")).replace(
        "<", "\\u003c"
    )
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
        <p class="eyebrow">Diagnosis Workbench</p>
        <h1>{artifact.metadata.title}</h1>
        <p class="hero-meta">{artifact.metadata.scenario_name} | {artifact.metadata.report_kind} | {artifact.metadata.schedule_kind}</p>
      </header>
      <section class="workbench-actions">
        <button id="export-panel-json-button" type="button">Export current panel JSON</button>
        <button id="export-panel-svg-button" type="button">Export current panel SVG</button>
      </section>
      <nav class="panel-tabs">
{nav_buttons}
      </nav>
      <main class="panel-stack">
{panel_sections}
      </main>
    </div>
    <script id="diagnosis-bundle-data" type="application/json">{embedded_bundle_json}</script>
    <script src="./assets/app.js"></script>
  </body>
</html>
"""


def _build_app_js(artifact: DiagnosisWorkbenchArtifact, bundle_relative_path: str) -> str:
    panel_deep_links = json.dumps(artifact.deep_links, separators=(",", ":"))
    panel_exports = json.dumps(
        {
            panel: [entry.model_dump(mode="json") for entry in exports]
            for panel, exports in artifact.panel_exports.items()
        },
        separators=(",", ":"),
    )
    return f"""const BUNDLE_PATH = {json.dumps(bundle_relative_path)};
const PANEL_DEEP_LINKS = {panel_deep_links};
const PANEL_EXPORTS = {panel_exports};

function readEmbeddedBundle() {{
  const bundleScript = document.querySelector("#diagnosis-bundle-data");
  if (!bundleScript) {{
    return null;
  }}
  return JSON.parse(bundleScript.textContent || "null");
}}

async function loadBundle() {{
  const embeddedBundle = readEmbeddedBundle();
  if (embeddedBundle) {{
    return embeddedBundle;
  }}
  const response = await fetch(BUNDLE_PATH);
  if (!response.ok) {{
    throw new Error(`Failed to load bundle: ${{response.status}}`);
  }}
  return response.json();
}}

function setActivePanel(panelId) {{
  document.querySelectorAll(".panel-tab").forEach((button) => {{
    button.classList.toggle("is-active", button.dataset.panel === panelId);
  }});
  document.querySelectorAll(".panel-view").forEach((section) => {{
    section.classList.toggle("is-active", section.dataset.panel === panelId);
  }});
  window.location.hash = PANEL_DEEP_LINKS[panelId] || "#/summary";
}}

function syncPanelFromHash() {{
  const rawHash = window.location.hash || "#/summary";
  const requestedPanel = rawHash.replace(/^#\\//, "") || "summary";
  return Object.prototype.hasOwnProperty.call(PANEL_DEEP_LINKS, requestedPanel)
    ? requestedPanel
    : "summary";
}}

function renderPanel(bundle, panelId) {{
  const container = document.querySelector(`#content-${{panelId}}`);
  if (!container) {{
    return;
  }}
  const reportKey = panelId === "assessment" ? "architecture_assessment_report" : null;
  const lines = [
    `<h2>${{panelId}}</h2>`,
    `<p>Run: ${{bundle.metadata.run_id}}</p>`,
    reportKey && bundle.report_references[reportKey]
      ? `<p>Source: ${{bundle.report_references[reportKey]}}</p>`
      : "",
  ].filter(Boolean);
  container.innerHTML = lines.join("");
}}

function exportCurrentPanelJson(panelId) {{
  return PANEL_EXPORTS[panelId][0].path;
}}

function exportCurrentPanelSvg(panelId) {{
  return PANEL_EXPORTS[panelId][1].path;
}}

async function main() {{
  const bundle = await loadBundle();
  document.querySelectorAll(".panel-tab").forEach((button) => {{
    button.addEventListener("click", () => setActivePanel(button.dataset.panel));
  }});
  window.addEventListener("hashchange", () => setActivePanel(syncPanelFromHash()));
  document.querySelector("#export-panel-json-button")?.addEventListener("click", () => {{
    exportCurrentPanelJson(syncPanelFromHash());
  }});
  document.querySelector("#export-panel-svg-button")?.addEventListener("click", () => {{
    exportCurrentPanelSvg(syncPanelFromHash());
  }});
  Object.keys(PANEL_DEEP_LINKS).forEach((panelId) => renderPanel(bundle, panelId));
  setActivePanel(syncPanelFromHash());
}}

main().catch((error) => {{
  document.querySelector(".panel-stack").innerHTML = `<article class="error-card"><h2>Workbench Error</h2><p>${{error.message}}</p></article>`;
}});
"""


def _build_styles_css() -> str:
    return """html, body {
  margin: 0;
  min-height: 100%;
  background: linear-gradient(180deg, #07111d 0%, #f3efe4 55%, #f3efe4 100%);
  color: #102033;
  font-family: "Trebuchet MS", "Segoe UI", sans-serif;
}

.shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 18px 40px;
}

.hero {
  color: #f5f1e6;
  padding: 22px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(10, 21, 39, 0.94), rgba(23, 46, 74, 0.94));
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 12px;
  color: #ffd60a;
}

.panel-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 20px 0 16px;
}

.panel-tab,
.workbench-actions button {
  border: 1px solid rgba(16, 32, 51, 0.14);
  border-radius: 999px;
  padding: 10px 14px;
  background: rgba(255, 251, 244, 0.94);
  color: #102033;
}

.panel-tab.is-active {
  background: #102033;
  color: #f5f1e6;
}

.panel-view {
  display: none;
  background: rgba(255, 251, 244, 0.94);
  border: 1px solid rgba(16, 32, 51, 0.08);
  border-radius: 18px;
  padding: 18px;
}

.panel-view.is-active {
  display: block;
}

.error-card {
  background: rgba(255, 245, 245, 0.92);
  border: 1px solid rgba(163, 0, 0, 0.18);
  border-radius: 18px;
  padding: 18px;
}
"""


def _normalize(path: Path) -> str:
    return str(path).replace("\\", "/")
