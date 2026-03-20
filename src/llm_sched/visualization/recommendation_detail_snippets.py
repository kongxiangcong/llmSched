"""Shared JS snippets for recommendation detail continuity surfaces."""

from __future__ import annotations


def build_recommendation_detail_helpers_js() -> str:
    return """
function buildRecommendationDetailLayerSummary(estimatedLayer, fittedLayer, formatDetailValue) {
  return {
    estimated_layer_summary: estimatedLayer
      ? `Layer ${estimatedLayer.layer_id}: ${formatDetailValue(estimatedLayer.delta_cycles)} cycles, ${formatDetailValue(estimatedLayer.delta_bytes)} bytes`
      : "No estimated layer deltas.",
    fitted_layer_summary: fittedLayer
      ? `Layer ${fittedLayer.layer_id}: ${formatDetailValue(fittedLayer.delta_fitted_work_cycles)} fitted work cycles, ${formatDetailValue(fittedLayer.delta_bytes)} bytes`
      : "No fitted layer deltas.",
  };
}

function buildRecommendationDetailSnapshotLines(detailEntries) {
  return (detailEntries || []).flatMap((detail) => ([
    `Top Recommendation Detail Candidates: ${detail.run_id || detail.candidate_target_profile_name || "unknown"}`,
    `Estimated Detail: ${detail.estimated_layer_summary || "No estimated layer deltas."}`,
    `Fitted Detail: ${detail.fitted_layer_summary || "No fitted layer deltas."}`,
  ]));
}

function renderRecommendationDetailEntryMarkup(detail, options = {}) {
  const title = options.title || detail.run_id || detail.candidate_target_profile_name || "unknown";
  const focusedBadge = detail.is_focused ? '<span class="tag">Focused Candidate</span>' : "";
  const headingTag = options.heading_tag || "span";
  const meta = options.meta || (detail.recommendation_reason || detail.target_profile_name || "");
  const tier = detail.recommendation_tier || "ranked";
  const leadLabel = options.lead_label || "Estimated Layer";
  const trailLabel = options.trail_label || "Fitted Layer";
  return `
    <li>
      <${headingTag}>${title}${detail.queue_position ? ` (#${detail.queue_position})` : ""}</${headingTag}>
      <div class="metric-detail-values">
        ${focusedBadge}
        <strong>${tier}</strong>
        <em>${meta}</em>
      </div>
      <div class="metric-detail-values">
        <strong>${leadLabel}: ${detail.estimated_layer_summary || "No estimated layer deltas."}</strong>
        <em>${trailLabel}: ${detail.fitted_layer_summary || "No fitted layer deltas."}</em>
      </div>
    </li>
  `;
}
""".strip()
