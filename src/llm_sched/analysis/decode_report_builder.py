"""Builder for SPEC-15 decode top-level evaluation reports."""

from __future__ import annotations

from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.contracts.decode_report import (
    DecodeEvaluationReport,
    DecodeISASummary,
    DecodeKVSummary,
    DecodeLatencySummary,
    DecodeMacroHotspot,
    DecodeMemoryHotspotSummary,
)
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.perf_report import PerfSummaryReport

PROJECTION_MACROS = {"GEMM", "WDQ_GEMM", "RMSNORM_GEMM"}
KV_IO_MACROS = {"KVLOAD", "KVSTORE"}
ATTENTION_MACROS = {"SDPA_DECODE", "SDPA", "ROPE", "ATTENTION_MASK_PREP"}


def build_decode_evaluation_report(
    run_id: str,
    scenario: ScenarioProfile,
    perf_summary: PerfSummaryReport,
    coverage_report: ISACoverageReport,
    memory_plan: MemoryPlanArtifact,
) -> DecodeEvaluationReport:
    if scenario.mode != "decode":
        raise ValueError("decode evaluation requires scenario.mode='decode'")

    total_cycles = float(perf_summary.totals.get("estimated_cycles", 0.0))
    total_tokens = scenario.batch * scenario.seq_len
    projection_cycles = _sum_cycles(perf_summary, PROJECTION_MACROS)
    kv_io_cycles = _sum_cycles(perf_summary, KV_IO_MACROS)
    attention_cycles = _sum_cycles(perf_summary, ATTENTION_MACROS)
    sync_cycles = float(perf_summary.totals.get("sync_cycles", 0.0))
    other_cycles = max(
        0.0,
        total_cycles - projection_cycles - kv_io_cycles - attention_cycles - sync_cycles,
    )
    kv_related_bytes = _sum_bytes(perf_summary, KV_IO_MACROS)

    return DecodeEvaluationReport(
        run_id=run_id,
        graph_id=perf_summary.graph_id,
        scenario_name=scenario.scenario_name,
        schedule_kind=perf_summary.schedule_kind,
        batch=scenario.batch,
        kv_len=scenario.kv_len,
        sdpa_decode_present="SDPA_DECODE" in perf_summary.per_macro_cycles,
        token_latency=DecodeLatencySummary(
            total_tokens=total_tokens,
            estimated_cycles=total_cycles,
            cycles_per_token=(total_cycles / total_tokens) if total_tokens > 0 else 0.0,
            projection_cycles=projection_cycles,
            kv_io_cycles=kv_io_cycles,
            attention_cycles=attention_cycles,
            sync_cycles=sync_cycles,
            other_cycles=other_cycles,
        ),
        kv_summary=DecodeKVSummary(
            kv_len=scenario.kv_len,
            kv_formula_count=len(memory_plan.kv_formulas),
            unresolved_address_count=sum(
                1 for diagnostic in memory_plan.address_diagnostics if diagnostic.status == "unresolved"
            ),
            kv_related_cycle_share=(kv_io_cycles / total_cycles) if total_cycles > 0.0 else 0.0,
            kv_related_bytes=kv_related_bytes,
        ),
        memory_hotspot=_build_memory_hotspot(perf_summary, memory_plan),
        isa_summary=DecodeISASummary(
            unmapped_block_count=coverage_report.unmapped_block_count,
            gap_counts=dict(coverage_report.gap_counts),
        ),
        macro_hotspots=_build_macro_hotspots(perf_summary, total_cycles),
    )


def _sum_cycles(perf_summary: PerfSummaryReport, macros: set[str]) -> float:
    return float(sum(perf_summary.per_macro_cycles.get(macro, 0.0) for macro in macros))


def _sum_bytes(perf_summary: PerfSummaryReport, macros: set[str]) -> float:
    return float(sum(perf_summary.per_macro_bytes.get(macro, 0.0) for macro in macros))


def _build_macro_hotspots(
    perf_summary: PerfSummaryReport,
    total_cycles: float,
) -> list[DecodeMacroHotspot]:
    hotspots: list[DecodeMacroHotspot] = []
    for macro_op, estimated_cycles in sorted(
        perf_summary.per_macro_cycles.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        hotspots.append(
            DecodeMacroHotspot(
                macro_op=macro_op,
                estimated_cycles=float(estimated_cycles),
                cycle_share=(float(estimated_cycles) / total_cycles) if total_cycles > 0.0 else 0.0,
                total_bytes=float(perf_summary.per_macro_bytes.get(macro_op, 0.0)),
            )
        )
    return hotspots


def _build_memory_hotspot(
    perf_summary: PerfSummaryReport,
    memory_plan: MemoryPlanArtifact,
) -> DecodeMemoryHotspotSummary:
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
    return DecodeMemoryHotspotSummary(
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
