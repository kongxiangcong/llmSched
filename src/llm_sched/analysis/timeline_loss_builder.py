"""Derived timeline-loss rows for diagnosis dataset."""

from __future__ import annotations


def build_timeline_loss_detail_rows(schedule_diagnostics_report) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in schedule_diagnostics_report.stall_events:
        loss_kind = _classify_loss_kind(reason=row.reason, has_waits=bool(row.wait_for_block_ids), span_slots=row.span_slots)
        recoverability = _recoverability_for(loss_kind)
        rows.append(
            {
                "core_id": row.core_id,
                "start_slot": row.start_slot,
                "end_slot": row.end_slot,
                "span_slots": row.span_slots,
                "loss_kind": loss_kind,
                "recoverability": recoverability,
                "recoverable_slots_estimated": _recoverable_slots(row.span_slots, recoverability),
                "preceding_block_id": row.wait_for_block_ids[0] if row.wait_for_block_ids else None,
                "following_block_id": row.block_id,
            }
        )
    for row in schedule_diagnostics_report.idle_spans:
        loss_kind = _classify_loss_kind(reason=row.reason, has_waits=bool(row.preceding_block_id or row.following_block_id), span_slots=row.span_slots)
        recoverability = _recoverability_for(loss_kind)
        rows.append(
            {
                "core_id": row.core_id,
                "start_slot": row.start_slot,
                "end_slot": row.end_slot,
                "span_slots": row.span_slots,
                "loss_kind": loss_kind,
                "recoverability": recoverability,
                "recoverable_slots_estimated": _recoverable_slots(row.span_slots, recoverability),
                "preceding_block_id": row.preceding_block_id,
                "following_block_id": row.following_block_id,
            }
        )
    return sorted(rows, key=lambda item: (item["core_id"], item["start_slot"], item["end_slot"]))


def build_timeline_loss_summary_rows(detail_rows: list[dict[str, object]], *, makespan_slots: int) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for row in detail_rows:
        bucket = grouped.setdefault(
            str(row["loss_kind"]),
            {
                "loss_kind": row["loss_kind"],
                "total_slots": 0.0,
                "event_count": 0,
                "recoverable_slots_total": 0.0,
                "representative_entities": [],
            },
        )
        bucket["total_slots"] += float(row["span_slots"])
        bucket["event_count"] += 1
        bucket["recoverable_slots_total"] += float(row["recoverable_slots_estimated"])
        entity = row.get("following_block_id") or row.get("preceding_block_id") or f"core.{row['core_id']}"
        if entity not in bucket["representative_entities"]:
            bucket["representative_entities"].append(entity)
    rows: list[dict[str, object]] = []
    if not grouped:
        return [{
            "loss_kind": "no_loss",
            "total_slots": 0.0,
            "event_count": 0,
            "share_of_makespan": 0.0,
            "recoverable_slots_total": 0.0,
            "recoverable_share_of_makespan": 0.0,
            "representative_entities": "",
        }]
    for bucket in grouped.values():
        total_slots = float(bucket["total_slots"])
        recoverable_slots_total = float(bucket["recoverable_slots_total"])
        representative_entities = "|".join(bucket["representative_entities"][:3])
        rows.append(
            {
                "loss_kind": bucket["loss_kind"],
                "total_slots": total_slots,
                "event_count": bucket["event_count"],
                "share_of_makespan": (total_slots / makespan_slots) if makespan_slots else 0.0,
                "recoverable_slots_total": recoverable_slots_total,
                "recoverable_share_of_makespan": (recoverable_slots_total / makespan_slots) if makespan_slots else 0.0,
                "representative_entities": representative_entities,
            }
        )
    return sorted(rows, key=lambda item: (-float(item["total_slots"]), str(item["loss_kind"])))


def _classify_loss_kind(*, reason: str, has_waits: bool, span_slots: int) -> str:
    reason_lower = (reason or "").lower()
    if "barrier" in reason_lower or "sync" in reason_lower:
        return "barrier_wait"
    if "dma" in reason_lower or "transfer" in reason_lower:
        return "dma_underlap"
    if "fallback" in reason_lower or "unsupported" in reason_lower:
        return "unsupported_detour"
    if span_slots <= 2:
        return "granularity_overhead"
    if has_waits:
        return "dependency_serialization"
    return "engine_mismatch"


def _recoverability_for(loss_kind: str) -> str:
    return {
        "dependency_serialization": "none",
        "barrier_wait": "medium",
        "dma_underlap": "high",
        "engine_mismatch": "medium",
        "unsupported_detour": "low",
        "granularity_overhead": "medium",
    }.get(loss_kind, "low")


def _recoverable_slots(span_slots: int | float, recoverability: str) -> float:
    factor = {
        "high": 0.8,
        "medium": 0.4,
        "low": 0.1,
        "none": 0.0,
    }[recoverability]
    return float(span_slots) * factor


__all__ = [
    "build_timeline_loss_detail_rows",
    "build_timeline_loss_summary_rows",
]
