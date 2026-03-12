"""Builder for SPEC-14 prefill top-level evaluation reports."""

from __future__ import annotations

from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.prefill_report import (
    PrefillEvaluationReport,
    PrefillISASummary,
    PrefillLayerBreakdownRow,
    PrefillMacroHotspot,
    PrefillMemoryHotspotSummary,
    PrefillMemorySummary,
    PrefillNodeHotspot,
    PrefillThroughputSummary,
)

MXU_HEAVY_MACROS = {"GEMM", "WDQ_GEMM", "RMSNORM_GEMM"}
KV_IO_MACROS = {"KVLOAD", "KVSTORE"}
ATTENTION_MACROS = {"SDPA", "ROPE", "ATTENTION_MASK_PREP"}


def build_prefill_evaluation_report(
    run_id: str,
    scenario: ScenarioProfile,
    perf_summary: PerfSummaryReport,
    coverage_report: ISACoverageReport,
    memory_plan: MemoryPlanArtifact,
) -> PrefillEvaluationReport:
    if scenario.mode != "prefill":
        raise ValueError("prefill evaluation requires scenario.mode='prefill'")

    total_cycles = float(perf_summary.totals.get("estimated_cycles", 0.0))
    critical_path_cycles = float(perf_summary.totals.get("critical_path_cycles", total_cycles))
    total_bytes = float(perf_summary.totals.get("total_bytes", 0.0))
    total_tokens = scenario.batch * scenario.seq_len
    mxu_cycles = _projection_cycles(perf_summary)
    kv_io_cycles = _phase_cycles(perf_summary, "kv_io")
    attention_cycles = _phase_cycles(perf_summary, "attention")
    sync_cycles = _phase_cycles(
        perf_summary,
        "sync",
        fallback=float(perf_summary.totals.get("sync_cycles", 0.0)),
    )
    other_cycles = _phase_cycles(
        perf_summary,
        "other",
        fallback=max(
            0.0,
            total_cycles - mxu_cycles - kv_io_cycles - attention_cycles - sync_cycles,
        ),
    )

    return PrefillEvaluationReport(
        run_id=run_id,
        graph_id=perf_summary.graph_id,
        scenario_name=scenario.scenario_name,
        schedule_kind=perf_summary.schedule_kind,
        batch=scenario.batch,
        seq_len=scenario.seq_len,
        mxu_dominant=mxu_cycles >= (0.5 * total_cycles),
        throughput=PrefillThroughputSummary(
            total_tokens=total_tokens,
            estimated_cycles=total_cycles,
            critical_path_cycles=critical_path_cycles,
            projection_cycles=mxu_cycles,
            kv_io_cycles=kv_io_cycles,
            attention_cycles=attention_cycles,
            sync_cycles=sync_cycles,
            other_cycles=other_cycles,
            tokens_per_cycle=(total_tokens / total_cycles) if total_cycles > 0.0 else 0.0,
            tokens_per_critical_path_cycle=(
                total_tokens / critical_path_cycles
            ) if critical_path_cycles > 0.0 else 0.0,
            cycles_per_token=(total_cycles / total_tokens) if total_tokens > 0 else 0.0,
            bytes_per_cycle=(total_bytes / total_cycles) if total_cycles > 0.0 else 0.0,
        ),
        memory_summary=PrefillMemorySummary(
            max_region_utilization=_max_region_utilization(memory_plan),
            overflow_region_count=_overflow_region_count(memory_plan),
            unresolved_address_count=sum(
                1 for diagnostic in memory_plan.address_diagnostics if diagnostic.status == "unresolved"
            ),
            kv_formula_count=len(memory_plan.kv_formulas),
        ),
        memory_hotspot=_build_memory_hotspot(perf_summary, memory_plan),
        isa_summary=PrefillISASummary(
            unmapped_block_count=coverage_report.unmapped_block_count,
            gap_counts=dict(coverage_report.gap_counts),
        ),
        macro_hotspots=_build_macro_hotspots(perf_summary, total_cycles),
        node_hotspots=_build_node_hotspots(perf_summary, total_cycles),
        layer_breakdown=_build_layer_breakdown(
            perf_summary,
            total_cycles,
            enabled=scenario.reporting.include_layer_breakdown,
        ),
    )


def _projection_cycles(perf_summary: PerfSummaryReport) -> float:
    return _phase_cycles(perf_summary, "projection")


def _phase_cycles(
    perf_summary: PerfSummaryReport,
    phase_name: str,
    *,
    fallback: float | None = None,
) -> float:
    phase_summary = perf_summary.phase_attribution.get(phase_name)
    if phase_summary is not None:
        return float(phase_summary.estimated_cycles)
    if fallback is not None:
        return float(fallback)
    if phase_name == "projection":
        macros = MXU_HEAVY_MACROS
    elif phase_name == "kv_io":
        macros = KV_IO_MACROS
    elif phase_name == "attention":
        macros = ATTENTION_MACROS
    else:
        return 0.0
    return float(
        sum(
            cycles
            for macro_op, cycles in perf_summary.per_macro_cycles.items()
            if macro_op in macros
        )
    )


def _max_region_utilization(memory_plan: MemoryPlanArtifact) -> float:
    utilizations = [
        (summary.peak_bytes / summary.capacity_bytes)
        for summary in memory_plan.region_summaries.values()
        if summary.capacity_bytes > 0
    ]
    return max(utilizations, default=0.0)


def _overflow_region_count(memory_plan: MemoryPlanArtifact) -> int:
    overflow_regions = {summary.region_name for summary in memory_plan.region_summaries.values() if not summary.fits}
    overflow_regions.update(
        diagnostic.region_name for diagnostic in memory_plan.diagnostics if diagnostic.status == "overflow"
    )
    return len(overflow_regions)


def _build_macro_hotspots(
    perf_summary: PerfSummaryReport,
    total_cycles: float,
) -> list[PrefillMacroHotspot]:
    hotspots: list[PrefillMacroHotspot] = []
    for macro_op, estimated_cycles in sorted(
        perf_summary.per_macro_cycles.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        hotspots.append(
            PrefillMacroHotspot(
                macro_op=macro_op,
                estimated_cycles=float(estimated_cycles),
                cycle_share=(float(estimated_cycles) / total_cycles) if total_cycles > 0.0 else 0.0,
                total_bytes=float(perf_summary.per_macro_bytes.get(macro_op, 0.0)),
            )
        )
    return hotspots


def _build_node_hotspots(
    perf_summary: PerfSummaryReport,
    total_cycles: float,
) -> list[PrefillNodeHotspot]:
    hotspots: list[PrefillNodeHotspot] = []
    for node_id, estimated_cycles in sorted(
        perf_summary.per_node_cycles.items(),
        key=lambda item: (-float(item[1]), item[0]),
    ):
        hotspots.append(
            PrefillNodeHotspot(
                node_id=node_id,
                estimated_cycles=float(estimated_cycles),
                cycle_share=(float(estimated_cycles) / total_cycles) if total_cycles > 0.0 else 0.0,
                total_bytes=float(perf_summary.per_node_bytes.get(node_id, 0.0)),
            )
        )
    return hotspots


def _build_layer_breakdown(
    perf_summary: PerfSummaryReport,
    total_cycles: float,
    *,
    enabled: bool,
) -> list[PrefillLayerBreakdownRow]:
    if not enabled:
        return []
    rows: list[PrefillLayerBreakdownRow] = []
    for layer_key, estimated_cycles in sorted(
        perf_summary.per_layer_cycles.items(),
        key=lambda item: (-float(item[1]), int(item[0])),
    ):
        rows.append(
            PrefillLayerBreakdownRow(
                layer_id=int(layer_key),
                estimated_cycles=float(estimated_cycles),
                cycle_share=(float(estimated_cycles) / total_cycles) if total_cycles > 0.0 else 0.0,
                total_bytes=float(perf_summary.per_layer_bytes.get(layer_key, 0.0)),
            )
        )
    return rows


def _build_memory_hotspot(
    perf_summary: PerfSummaryReport,
    memory_plan: MemoryPlanArtifact,
) -> PrefillMemoryHotspotSummary:
    read_bytes = dict(perf_summary.data_movement_read_bytes_by_address_space)
    write_bytes = dict(perf_summary.data_movement_write_bytes_by_address_space)
    dominant_address_space = _dominant_address_space(read_bytes, write_bytes)
    (
        hottest_region,
        hottest_region_peak_bytes,
        hottest_region_capacity_bytes,
        hottest_region_utilization,
        hottest_region_peak_bytes_by_backing_store,
        hottest_region_peak_bytes_by_memory_class,
    ) = _hottest_region(memory_plan)
    return PrefillMemoryHotspotSummary(
        dominant_address_space=dominant_address_space,
        read_bytes_by_address_space=read_bytes,
        write_bytes_by_address_space=write_bytes,
        hottest_region=hottest_region,
        hottest_region_peak_bytes=hottest_region_peak_bytes,
        hottest_region_capacity_bytes=hottest_region_capacity_bytes,
        hottest_region_utilization=hottest_region_utilization,
        hottest_region_peak_bytes_by_backing_store=hottest_region_peak_bytes_by_backing_store,
        hottest_region_peak_bytes_by_memory_class=hottest_region_peak_bytes_by_memory_class,
    )


def _dominant_address_space(
    read_bytes: dict[str, float],
    write_bytes: dict[str, float],
) -> str | None:
    totals: dict[str, float] = {}
    for address_space, value in read_bytes.items():
        totals[address_space] = totals.get(address_space, 0.0) + float(value)
    for address_space, value in write_bytes.items():
        totals[address_space] = totals.get(address_space, 0.0) + float(value)
    if not totals:
        return None
    return max(sorted(totals), key=lambda address_space: totals[address_space])


def _hottest_region(
    memory_plan: MemoryPlanArtifact,
) -> tuple[str | None, int, int, float, dict[str, int], dict[str, int]]:
    if not memory_plan.region_summaries:
        return None, 0, 0, 0.0, {}, {}
    region_name, summary = max(
        memory_plan.region_summaries.items(),
        key=lambda item: (
            (item[1].peak_bytes / item[1].capacity_bytes) if item[1].capacity_bytes > 0 else 0.0,
            item[1].peak_bytes,
            item[0],
        ),
    )
    utilization = (summary.peak_bytes / summary.capacity_bytes) if summary.capacity_bytes > 0 else 0.0
    return (
        region_name,
        summary.peak_bytes,
        summary.capacity_bytes,
        utilization,
        dict(sorted(summary.peak_bytes_by_backing_store.items())),
        dict(sorted(summary.peak_bytes_by_memory_class.items())),
    )
