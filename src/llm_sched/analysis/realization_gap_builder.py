"""Derived realization-gap rows for diagnosis dataset."""

from __future__ import annotations

from collections import defaultdict


def build_realization_gap_rows(
    *,
    structure_demand_rows: list[dict[str, object]],
    structure_support_rows: list[dict[str, object]],
    schedule_block_rows: list[dict[str, object]],
    perf_by_structure_rows: list[dict[str, object]],
    subject_block_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    support_by_structure = {str(row["structure_id"]): row for row in structure_support_rows}
    perf_by_structure = {str(row["structure_id"]): row for row in perf_by_structure_rows}
    block_ids_by_subject: dict[str, list[str]] = defaultdict(list)
    for row in subject_block_rows:
        block_ids_by_subject[str(row["normalized_node_id"])] .append(str(row["block_id"]))
    duration_by_structure: dict[str, float] = defaultdict(float)
    subject_ids_by_structure: dict[str, set[str]] = defaultdict(set)
    for row in schedule_block_rows:
        normalized_node_id = row.get("normalized_node_id")
        if normalized_node_id is not None:
            subject_ids_by_structure[str(normalized_node_id)].add(str(normalized_node_id))
    rows: list[dict[str, object]] = []
    for demand in structure_demand_rows:
        structure_id = str(demand["structure_id"])
        perf = perf_by_structure.get(structure_id, {})
        support = support_by_structure.get(structure_id, {})
        theoretical_compute_ops = float(demand.get("compute_ops", 0.0) or 0.0)
        theoretical_bytes = float(demand.get("read_bytes", 0.0) or 0.0) + float(demand.get("write_bytes", 0.0) or 0.0)
        theoretical_ai = float(demand.get("arithmetic_intensity", 0.0) or 0.0)
        estimated_cycles = float(perf.get("estimated_cycles", 0.0) or 0.0)
        fitted_cycles = float(perf.get("fitted_work_cycles", 0.0) or 0.0)
        effective_ai = theoretical_compute_ops / max(float(perf.get("total_bytes", theoretical_bytes) or theoretical_bytes or 1.0), 1.0)
        worst_support_status = str(support.get("worst_support_status", "native") or "native")
        blocking_gap_count = int(support.get("blocking_gap_count", 0) or 0)
        total_nodes = sum(int(support.get(key, 0) or 0) for key in ("native_count", "constrained_count", "fallback_count", "unsupported_count"))
        fallback_nodes = int(support.get("fallback_count", 0) or 0) + int(support.get("unsupported_count", 0) or 0)
        fallback_ratio = (fallback_nodes / total_nodes) if total_nodes else 0.0
        support_penalty_score = min(1.0, _support_penalty_base(worst_support_status) + (0.1 * blocking_gap_count))
        scheduled_duration_slots = estimated_cycles and max(1, int(round(fitted_cycles or estimated_cycles))) or 0
        sync_penalty_slots = 0.0
        overlap_loss_slots = 0.0
        theoretical_ai_no_penalty = theoretical_compute_ops / max(theoretical_bytes * max(1.0 - fallback_ratio, 0.25), 1.0)
        gap_kind = _classify_gap_kind(worst_support_status, str(perf.get("dominant_bound", "") or ""), support_penalty_score, fallback_ratio)
        gap_score = min(
            1.0,
            (support_penalty_score * 0.45)
            + (fallback_ratio * 0.25)
            + (0.15 if gap_kind == "bandwidth_gap" else 0.0)
            + (0.10 if gap_kind == "support_gap" else 0.0)
            + (0.05 if estimated_cycles > 0 and fitted_cycles == 0 else 0.0),
        )
        gap_confidence = "medium" if perf else "low"
        if worst_support_status == "unsupported":
            gap_confidence = "high"
        rows.append(
            {
                "structure_id": structure_id,
                "structure_kind": demand.get("structure_kind", ""),
                "layer_id": demand.get("layer_id", 0),
                "theoretical_compute_ops": theoretical_compute_ops,
                "theoretical_bytes": theoretical_bytes,
                "theoretical_ai": theoretical_ai,
                "scheduled_duration_slots": scheduled_duration_slots,
                "estimated_cycles": estimated_cycles,
                "fitted_cycles": fitted_cycles,
                "worst_support_status": worst_support_status,
                "support_penalty_score": support_penalty_score,
                "fallback_ratio": fallback_ratio,
                "sync_penalty_slots": sync_penalty_slots,
                "overlap_loss_slots": overlap_loss_slots,
                "effective_ai": effective_ai,
                "theoretical_ai_no_penalty": theoretical_ai_no_penalty,
                "gap_kind": gap_kind,
                "gap_score": gap_score,
                "gap_confidence": gap_confidence,
            }
        )
    return rows


def _support_penalty_base(status: str) -> float:
    return {
        "native": 0.0,
        "constrained": 0.25,
        "fallback": 0.6,
        "unsupported": 1.0,
    }.get(status, 0.3)


def _classify_gap_kind(status: str, dominant_bound: str, support_penalty_score: float, fallback_ratio: float) -> str:
    if status == "unsupported" or support_penalty_score >= 0.8:
        return "support_gap"
    if fallback_ratio >= 0.3 or status == "fallback":
        return "fallback_gap"
    if dominant_bound in {"bandwidth_bound", "bandwidth", "memory_bound", "memory-bound"}:
        return "bandwidth_gap"
    if dominant_bound in {"sync_bound", "sync"}:
        return "sync_gap"
    return "compute_gap"


__all__ = ["build_realization_gap_rows"]
