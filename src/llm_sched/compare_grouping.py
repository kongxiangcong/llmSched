"""Shared compare-group helpers for SPEC-16 and downstream consumers."""

from __future__ import annotations

from typing import Literal, Protocol, TypeVar


CompareGroupId = Literal[
    "headline",
    "throughput_latency",
    "phase_shape",
    "memory_pressure",
    "schedule_shape",
]

COMPARE_GROUP_TITLES: dict[CompareGroupId, str] = {
    "headline": "Headline",
    "throughput_latency": "Throughput / Latency",
    "phase_shape": "Phase Shape",
    "memory_pressure": "Memory Pressure",
    "schedule_shape": "Schedule Shape",
}
PHASE_METRIC_PREFIXES = ("projection", "kv_io", "attention", "sync", "other")
PREFILL_HEADLINE_METRIC_NAMES = (
    "estimated_cycles",
    "critical_path_cycles",
    "tokens_per_critical_path_cycle",
    "tokens_per_cycle",
    "bytes_per_cycle",
    "max_region_utilization",
)
DECODE_HEADLINE_METRIC_NAMES = (
    "estimated_cycles",
    "critical_path_cycles",
    "critical_path_cycles_per_token",
    "cycles_per_token",
    "kv_related_cycle_share",
    "kv_related_bytes",
)
PREFILL_THROUGHPUT_LATENCY_METRIC_NAMES = (
    "estimated_cycles",
    "critical_path_cycles",
    "fitted_work_cycles",
    "tokens_per_cycle",
    "tokens_per_fitted_work_cycle",
    "tokens_per_critical_path_cycle",
    "cycles_per_token",
    "fitted_cycles_per_token",
    "bytes_per_cycle",
)
DECODE_THROUGHPUT_LATENCY_METRIC_NAMES = (
    "estimated_cycles",
    "critical_path_cycles",
    "fitted_work_cycles",
    "cycles_per_token",
    "fitted_work_cycles_per_token",
    "critical_path_cycles_per_token",
    "kv_related_cycle_share",
    "kv_related_fitted_work_cycle_share",
    "kv_related_bytes",
)
PHASE_SHAPE_METRIC_NAMES = (
    "cycles",
    "fitted_work_cycles",
    "bytes",
    "byte_share",
    "bytes_per_cycle",
    "cycle_share",
)
PHASE_ADDRESS_SPACE_METRIC_NAMES = (
    "read_bytes_ddr",
    "write_bytes_ddr",
    "read_bytes_vmem",
    "write_bytes_vmem",
)
PHASE_BACKING_STORE_METRIC_NAMES = (
    "read_bytes_ddr_backed_staged",
    "write_bytes_ddr_backed_staged",
    "read_bytes_ddr_persistent",
    "write_bytes_ddr_persistent",
    "read_bytes_vmem_local",
    "write_bytes_vmem_local",
)
PHASE_MEMORY_CLASS_METRIC_NAMES = (
    "read_bytes_activation",
    "write_bytes_activation",
    "read_bytes_weight",
    "write_bytes_weight",
    "read_bytes_kv_cache",
    "write_bytes_kv_cache",
)
PHASE_CYCLE_COMPONENT_METRIC_NAMES = (
    "compute_cycles",
    "memory_cycles",
    "sync_cycles",
)
PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES = (
    "schedule_compression_cycles",
    "schedule_compression_ratio",
    "schedule_overhang_cycles",
)
PHASE_OCCUPIED_SLOT_METRIC_NAMES = (
    "occupied_slots",
    "occupied_slots_per_token",
)
PHASE_BALANCE_METRIC_NAMES = (
    "occupied_slot_imbalance_slots",
    "occupied_slot_balance_ratio",
    "span_imbalance_slots",
    "span_balance_ratio",
)


class SupportsMetricName(Protocol):
    metric_name: str


MetricRowT = TypeVar("MetricRowT", bound=SupportsMetricName)


def headline_metric_names_for_mode(compare_mode: str) -> tuple[str, ...]:
    if compare_mode == "prefill":
        return PREFILL_HEADLINE_METRIC_NAMES
    return DECODE_HEADLINE_METRIC_NAMES


def select_highlighted_metric_rows(
    metric_rows: list[MetricRowT],
    *,
    headline_metric_names: tuple[str, ...],
) -> list[MetricRowT]:
    metric_by_name = {row.metric_name: row for row in metric_rows}
    highlighted: list[MetricRowT] = []
    seen_metric_names: set[str] = set()

    for metric_name in headline_metric_names:
        metric_row = metric_by_name.get(metric_name)
        if metric_row is None or metric_name in seen_metric_names:
            continue
        highlighted.append(metric_row)
        seen_metric_names.add(metric_name)
        if len(highlighted) == 3:
            break

    for metric_suffix in ("cycle_share", "byte_share", "bytes_per_cycle"):
        metric_row = select_phase_metric_highlight(metric_rows, metric_suffix=metric_suffix)
        if metric_row is None or metric_row.metric_name in seen_metric_names:
            continue
        highlighted.append(metric_row)
        seen_metric_names.add(metric_row.metric_name)

    return highlighted


def select_phase_metric_highlight(
    metric_rows: list[MetricRowT],
    *,
    metric_suffix: str,
) -> MetricRowT | None:
    candidate_metric_names = {
        f"{metric_prefix}_{metric_suffix}" for metric_prefix in PHASE_METRIC_PREFIXES
    }
    ranked_candidates = sorted(
        (
            metric_row
            for metric_row in metric_rows
            if metric_row.metric_name in candidate_metric_names
            and (
                abs(getattr(metric_row, "delta_ratio", 0.0)) > 0.0
                or abs(getattr(metric_row, "delta_value", 0.0)) > 0.0
            )
        ),
        key=lambda metric_row: (
            -abs(getattr(metric_row, "delta_ratio", 0.0)),
            -abs(getattr(metric_row, "delta_value", 0.0)),
            metric_row.metric_name,
        ),
    )
    if not ranked_candidates:
        return None
    return ranked_candidates[0]


def build_grouped_metric_rows(
    metric_rows: list[MetricRowT],
    *,
    compare_mode: str,
    headline_metric_names: tuple[str, ...] | None = None,
) -> list[tuple[CompareGroupId, str, list[MetricRowT]]]:
    resolved_headline_metric_names = headline_metric_names or headline_metric_names_for_mode(
        compare_mode
    )
    throughput_latency_metric_names = (
        PREFILL_THROUGHPUT_LATENCY_METRIC_NAMES
        if compare_mode == "prefill"
        else DECODE_THROUGHPUT_LATENCY_METRIC_NAMES
    )
    memory_pressure_metric_names = {"max_region_utilization"}
    if compare_mode == "decode":
        memory_pressure_metric_names.add("kv_related_bytes")

    grouped_metric_rows: list[tuple[CompareGroupId, list[MetricRowT]]] = [
        (
            "headline",
            _select_metric_rows_by_ordered_names(metric_rows, resolved_headline_metric_names),
        ),
        (
            "throughput_latency",
            _select_metric_rows_by_ordered_names(metric_rows, throughput_latency_metric_names),
        ),
        (
            "phase_shape",
            _select_metric_rows_by_name(
                metric_rows,
                _build_phase_metric_name_set(PHASE_SHAPE_METRIC_NAMES),
            ),
        ),
        (
            "memory_pressure",
            _select_metric_rows_by_name(
                metric_rows,
                memory_pressure_metric_names
                | _build_phase_metric_name_set(PHASE_ADDRESS_SPACE_METRIC_NAMES)
                | _build_phase_metric_name_set(PHASE_BACKING_STORE_METRIC_NAMES)
                | _build_phase_metric_name_set(PHASE_MEMORY_CLASS_METRIC_NAMES),
            ),
        ),
        (
            "schedule_shape",
            _select_metric_rows_by_name(
                metric_rows,
                _build_phase_metric_name_set(PHASE_CYCLE_COMPONENT_METRIC_NAMES)
                | _build_phase_metric_name_set(PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES)
                | _build_phase_metric_name_set(PHASE_OCCUPIED_SLOT_METRIC_NAMES)
                | _build_phase_metric_name_set(PHASE_BALANCE_METRIC_NAMES),
            ),
        ),
    ]
    return [
        (group_id, COMPARE_GROUP_TITLES[group_id], group_rows)
        for group_id, group_rows in grouped_metric_rows
        if group_rows
    ]


def _build_phase_metric_name_set(metric_names: tuple[str, ...]) -> set[str]:
    return {
        f"{phase_name}_{metric_name}"
        for phase_name in PHASE_METRIC_PREFIXES
        for metric_name in metric_names
    }


def _select_metric_rows_by_ordered_names(
    metric_rows: list[MetricRowT],
    metric_names: tuple[str, ...],
) -> list[MetricRowT]:
    metric_by_name = {row.metric_name: row for row in metric_rows}
    return [metric_by_name[metric_name] for metric_name in metric_names if metric_name in metric_by_name]


def _select_metric_rows_by_name(
    metric_rows: list[MetricRowT],
    metric_names: set[str],
) -> list[MetricRowT]:
    return [metric_row for metric_row in metric_rows if metric_row.metric_name in metric_names]
